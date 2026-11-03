#!/usr/bin/env python3
"""Daily gold forecast job for the server.

Pipeline:
  1. obtain predictions (live model run, or an upstream predictions CSV)
  2. apply the champion version from models/versions.py
  3. attach calibrated intervals
  4. apply the rolling skill gate (falls back to v0 when it degrades)
  5. write outputs atomically + append-only log
  6. optionally push a compact card to Feishu

Exit codes: 0 ok, 2 data problem, 3 gate/quality problem, 4 unexpected error.
A non-zero exit must page someone; do not let cron swallow it.

Examples:
  # offline dry run against the frozen snapshot rows
  python scripts/gold_daily.py --predictions-csv /tmp/pred.csv --out /tmp/goldout --dry-run

  # live, default champion
  python scripts/gold_daily.py --live --out /srv/gold/out
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-service"))

from models.versions import CHAMPION_DEFAULT, FALLBACK, predict_close  # noqa: E402

DEFAULT_CALIBRATION = ROOT / "config/gold_versions/calibration.json"
DEFAULT_VERSION = CHAMPION_DEFAULT
ROLLING_SKILL_WINDOW = 30
SKILL_FLOOR = -0.05


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
    print(f"[{ts}] {msg}", flush=True)


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_calibration(path: Path, version: str) -> Dict[str, Dict[str, float]]:
    if not path.exists():
        _log(f"WARN calibration missing at {path}; intervals will be omitted")
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("versions", {}).get(version, {})


def interval_for(cal: Dict[str, Dict[str, float]], horizon: int, pred: float) -> tuple[Optional[float], Optional[float]]:
    """Nearest calibrated horizon, widened/narrowed by sqrt(h) for the gap.

    Calibration only carries T+1/3/5/10; T+2 and T+4 must still get an interval,
    otherwise the report silently ships a point forecast with no uncertainty.
    """
    if not cal:
        return (None, None)
    key = str(int(horizon))
    if key in cal:
        entry, scale = cal[key], 1.0
    else:
        nearest = min(cal, key=lambda k: abs(int(k) - int(horizon)))
        entry = cal[nearest]
        scale = (float(horizon) / float(nearest)) ** 0.5
    return (round(pred + entry["q_low"] * scale, 2), round(pred + entry["q_high"] * scale, 2))


def rolling_skill(history: pd.DataFrame, version: str, window: int = ROLLING_SKILL_WINDOW,
                  as_of: Optional[pd.Timestamp] = None) -> Optional[float]:
    """Skill over the most recent matured rows (history only, never the forecast)."""
    matured = history.dropna(subset=["actual_close"]).copy()
    if as_of is not None:
        matured = matured[(matured["origin_date"] < as_of) & (matured["target_date"] <= as_of)]
    matured = matured.drop_duplicates(subset=["origin_date", "horizon"])
    if matured.empty:
        return None
    matured["model_return"] = matured["pred_close"] / matured["origin_close"] - 1.0
    matured["pred_v"] = [
        predict_close(version, r.origin_close, r.model_return, r.horizon) for r in matured.itertuples()
    ]
    matured = matured.sort_values("target_date").tail(window)
    base = (matured["actual_close"] - matured["origin_close"]).abs().mean()
    model = (matured["actual_close"] - matured["pred_v"]).abs().mean()
    if not base:
        return None
    return float(1 - model / base)


class DataError(RuntimeError):
    """Upstream data unavailable and no usable cache; maps to exit code 2."""


def validate_predictions(pred: pd.DataFrame) -> pd.DataFrame:
    """Reject ambiguous or non-finite inputs before evaluating or publishing."""
    required = {"origin_date", "target_date", "horizon", "origin_close", "pred_close"}
    missing = required - set(pred.columns)
    if missing:
        raise DataError(f"missing prediction columns: {sorted(missing)}")
    out = pred.copy()
    for col in ("origin_date", "target_date"):
        out[col] = pd.to_datetime(out[col], errors="coerce")
        if out[col].isna().any():
            raise DataError(f"invalid {col}")
    for col in ("origin_close", "pred_close", "horizon", "actual_close"):
        if col not in out:
            out[col] = np.nan
        values = pd.to_numeric(out[col], errors="coerce")
        present = out[col].notna() if col == "actual_close" else pd.Series(True, index=out.index)
        if ((~np.isfinite(values) | (values <= 0)) & present).any():
            raise DataError(f"{col} must contain finite positive numbers")
        out[col] = values
    if (out["horizon"] % 1 != 0).any():
        raise DataError("horizon must be an integer")
    if (out["target_date"] <= out["origin_date"]).any():
        raise DataError("target_date must follow origin_date")
    if out.duplicated(["origin_date", "horizon"]).any():
        raise DataError("duplicate origin_date/horizon")
    if (out.groupby("origin_date")["origin_close"].nunique() > 1).any():
        raise DataError("inconsistent origin_close for the same origin")
    return out.sort_values(["origin_date", "horizon"]).reset_index(drop=True)


def _cached_fetch(name: str, fn, cache_dir: Path) -> tuple[pd.DataFrame, str | None]:
    """Fetch a series, persist it, and fall back to the last good copy.

    Yahoo rate-limits aggressively, so a cron job that dies on the first 429
    would be useless. A cache hit is real historical data and is disclosed in
    the manifest; a miss is a hard failure rather than a silent guess.
    """
    cache = cache_dir / f"{name}.csv"
    try:
        df = fn()
        if df is None or df.empty:
            raise DataError(f"{name} returned no rows")
        cache_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache, index=False)
        return df, None
    except Exception as exc:  # noqa: BLE001
        if cache.exists():
            df = pd.read_csv(cache, parse_dates=["date"])
            note = (
                f"{name}: 抓取失败({type(exc).__name__})，使用缓存 {cache.name}"
                f"（数据截至 {pd.Timestamp(df['date'].max()).date()}）"
            )
            _log("WARN " + note)
            return df, note
        raise DataError(f"{name} 抓取失败且无缓存，请先成功运行一次: {exc}") from exc


def build_predictions_live(horizons: int) -> tuple[pd.DataFrame, list[str]]:
    """Fetch the daily bars and run the direct model. Network + akshare required."""
    import akshare as ak  # noqa: F401  (fail fast with a clear message)

    from models.multi_day_direct_predictor import run_direct_multi_day_prediction

    sys.path.insert(0, str(ROOT))
    from run_gold_analysis import (  # type: ignore[import-not-found]
        build_future_trade_dates,
        fetch_comex_daily,
        fetch_cross_market,
        fetch_shfe_au_daily,
        fetch_usdcny_daily,
    )

    cache = ROOT / ".cache/gold"
    warnings: list[str] = []

    def grab(name: str, fn):
        df, note = _cached_fetch(name, fn, cache)
        if note:
            warnings.append(note)
        return df

    daily = grab("shfe", fetch_shfe_au_daily)
    if daily.empty:
        raise DataError("empty SHFE daily series")
    if len(daily) < 300:
        raise DataError(f"SHFE history too short: {len(daily)} rows")

    last_date = pd.Timestamp(daily["date"].iloc[-1]).normalize()
    target_end = last_date + pd.Timedelta(days=horizons * 2 + 4)
    future, _meta = build_future_trade_dates(last_date, target_end)
    if len(future) == 0:
        raise DataError("no future trading day resolved")

    predictions = run_direct_multi_day_prediction(
        daily_df=daily,
        comex_daily=grab("comex", fetch_comex_daily),
        usdcny_daily=grab("usdcny", fetch_usdcny_daily),
        cross_market=grab("cross", fetch_cross_market),
        target_dates=list(future[:horizons]),
        lookback_days=240,
        verbose=False,
    )
    origin_close = float(daily["close"].iloc[-1])
    rows = []
    for h, p in enumerate(predictions, start=1):
        rows.append(
            {
                "origin_date": last_date,
                "target_date": pd.Timestamp(p["date"]),
                "horizon": int(h),
                "origin_close": origin_close,
                "pred_close": float(p["close"]),
                "actual_close": np.nan,
            }
        )
    return pd.DataFrame(rows), warnings


def load_history(ledger: Path, daily: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Reconstruct matured forecast rows from the append-only ledger.

    Without this the rolling-skill gate can never fire in live mode: every run
    would report skill=None and the fallback would be dead code.
    """
    empty = pd.DataFrame(columns=["origin_date", "target_date", "horizon", "origin_close", "pred_close", "actual_close"])
    if not ledger.exists() or daily is None or daily.empty:
        return empty
    close_by_date = {
        pd.Timestamp(d).normalize(): float(c) for d, c in zip(daily["date"], daily["close"])
    }
    rows = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        for row in entry.get("rows", []):
            target = pd.Timestamp(row["date"]).normalize()
            actual = close_by_date.get(target)
            if actual is None:
                continue
            rows.append(
                {
                    "origin_date": pd.Timestamp(entry["origin_date"]),
                    "target_date": target,
                    "horizon": int(row["horizon"]),
                    "origin_close": float(entry["origin_close"]),
                    "pred_close": float(row.get("raw_model_close", row["model_close"])),
                    "actual_close": actual,
                }
            )
    if not rows:
        return empty
    return pd.DataFrame(rows).drop_duplicates(subset=["origin_date", "horizon"]).sort_values("target_date")


def build_outputs(pred: pd.DataFrame, version: str, cal: Dict[str, Dict[str, float]], gate_note: str) -> Dict[str, Any]:
    origin_close = float(pred["origin_close"].iloc[0])
    origin_date = pd.Timestamp(pred["origin_date"].iloc[0]).strftime("%Y-%m-%d")
    rows = []
    for r in pred.itertuples():
        model_return = r.pred_close / r.origin_close - 1.0
        price = predict_close(version, r.origin_close, model_return, r.horizon)
        lo, hi = interval_for(cal, r.horizon, price)
        rows.append(
            {
                "date": pd.Timestamp(r.target_date).strftime("%Y-%m-%d"),
                "horizon": int(r.horizon),
                "baseline_close": round(float(origin_close), 2),
                "model_close": round(float(price), 2),
                "raw_model_close": round(float(r.pred_close), 2),
                "range_low": lo,
                "range_high": hi,
            }
        )
    return {
        "origin_date": origin_date,
        "origin_close": round(origin_close, 2),
        "version": version,
        "gate_note": gate_note,
        "rows": rows,
    }


def render_markdown(manifest: Dict[str, Any], skill: Optional[float]) -> str:
    lines = [
        f"# 黄金预测 {manifest['origin_date']}（{manifest['version']}）",
        "",
        f"- 基准收盘：**{manifest['origin_close']:.2f}** 元/克",
        f"- 版本：`{manifest['version']}`",
    ]
    if skill is None:
        lines.append("- 滚动 skill：暂无成熟样本")
    else:
        lines.append(f"- 滚动 skill（近 {ROLLING_SKILL_WINDOW} 条）：**{skill:+.3f}**")
        if skill < 0:
            lines.append("- ⚠️ skill < 0：本模型不优于“价格不变”，预测仅作参考")
    if manifest.get("gate_note"):
        lines.append(f"- 闸门：{manifest['gate_note']}")
    if manifest.get("skill_version"):
        lines.append(f"- skill 评估对象：`{manifest['skill_version']}`，截至 {manifest['skill_as_of']}，成熟样本 {manifest['skill_sample_count']} 条（样本可能重叠，不代表独立样本数）")
    for warn in manifest.get("data_warnings") or []:
        lines.append(f"- ⚠️ 数据：{warn}")
    lines += ["", "| 日期 | T+n | 基准 | 模型 | 80% 区间 |", "|---|---:|---:|---:|---|"]
    for row in manifest["rows"]:
        rng = (
            f"{row['range_low']:.2f} ~ {row['range_high']:.2f}"
            if row["range_low"] is not None
            else "—"
        )
        lines.append(
            f"| {row['date']} | T+{row['horizon']} | {row['baseline_close']:.2f} | "
            f"{row['model_close']:.2f} | {rng} |"
        )
    lines += [
        "",
        "> 区间来自历史残差分位数，标称 80%；实际覆盖率见 leaderboard。",
        "> 价格区间覆盖率不是涨跌概率；收益收缩也不代表方向准确率提高。",
        "> 本报告不构成投资建议。",
    ]
    return "\n".join(lines)


def push_feishu(webhook: str, manifest: Dict[str, Any], skill: Optional[float], report_path: Path) -> None:
    import urllib.request

    head = f"黄金预测 {manifest['origin_date']} · {manifest['version']}"
    first = manifest["rows"][0]
    rng = (
        f"{first['range_low']:.2f}~{first['range_high']:.2f}" if first["range_low"] is not None else "—"
    )
    body = [
        f"{row['date']} T+{row['horizon']}: {row['model_close']:.2f}"
        for row in manifest["rows"][:3]
    ]
    text = "\n".join(
        [
            head,
            f"基准 {manifest['origin_close']:.2f} 元/克",
            f"T+1 {first['model_close']:.2f}（{rng}）",
            *body[1:],
            f"滚动 skill：{skill:+.3f}" if skill is not None else "滚动 skill：暂无",
            f"详情：{report_path}",
        ]
    )
    payload = json.dumps({"msg_type": "text", "content": {"text": text}}).encode()
    req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"feishu push failed: HTTP {resp.status}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="champion version (v0/v1/v3/v4/v7)")
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--predictions-csv", type=Path, help="offline mode: precomputed predictions")
    parser.add_argument("--live", action="store_true", help="fetch data and run the model")
    parser.add_argument("--horizons", type=int, default=5)
    parser.add_argument("--origin", help="forecast origin date (default: latest in input)")
    parser.add_argument("--feishu-webhook", default=os.environ.get("FEISHU_WEBHOOK_URL", ""))
    parser.add_argument("--publish-dir", type=Path, help="also copy report.md into this dir as YYYY-MM-DD.md")
    parser.add_argument("--dry-run", action="store_true", help="write to a temp dir, do not push")
    args = parser.parse_args()

    try:
        if args.live and args.predictions_csv:
            raise SystemExit("use either --live or --predictions-csv, not both")
        data_warnings: list[str] = []
        history = pd.DataFrame(columns=["origin_date", "target_date", "horizon", "origin_close", "pred_close", "actual_close"])
        if args.predictions_csv:
            pred = pd.read_csv(args.predictions_csv)
            if "actual_close" not in pred:
                pred["actual_close"] = np.nan
        elif args.live:
            pred, data_warnings = build_predictions_live(args.horizons)
        else:
            raise SystemExit("one of --live / --predictions-csv is required")

        if pred.empty:
            _log("ERROR no predictions; upstream produced nothing")
            return 2

        pred = validate_predictions(pred)

        live_daily: Optional[pd.DataFrame] = None
        if args.live:
            live_daily = pd.read_csv(ROOT / ".cache/gold/shfe.csv", parse_dates=["date"]) if (ROOT / ".cache/gold/shfe.csv").exists() else None

        origin = pd.Timestamp(args.origin) if args.origin else pd.Timestamp(pred["origin_date"].max())
        forecast = pred[pred["origin_date"] == origin].copy()
        history = pred[(pred["origin_date"] < origin) & pred["actual_close"].notna()].copy()
        if args.live:
            ledger_path = args.out / "forecasts.jsonl"
            reconciled = load_history(ledger_path, live_daily)
            if not reconciled.empty:
                history = pd.concat([history, reconciled], ignore_index=True)
                _log(f"reconciled {len(reconciled)} matured rows from ledger")
        if forecast.empty:
            _log(f"ERROR no forecast rows for origin {origin.date()}")
            return 2
        if forecast["origin_close"].isna().any() or (forecast["origin_close"] <= 0).any():
            _log("ERROR invalid origin_close in forecast rows")
            return 2

        version = args.version
        gate_note = ""
        history = history[(history["origin_date"] < origin) & (history["target_date"] <= origin)].copy()
        skill = rolling_skill(history, version, as_of=origin)
        if skill is not None and skill < SKILL_FLOOR:
            gate_note = f"{version} rolling skill {skill:+.3f} < {SKILL_FLOOR:+.2f} -> fell back to {FALLBACK}"
            _log(gate_note)
            version = FALLBACK

        cal = load_calibration(args.calibration, version)
        manifest = build_outputs(forecast, version, cal, gate_note)
        manifest["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        manifest["calibration_source"] = str(args.calibration)
        manifest["data_warnings"] = data_warnings
        manifest["skill_version"] = args.version
        manifest["skill_as_of"] = origin.isoformat()
        manifest["skill_sample_count"] = min(len(history.drop_duplicates(["origin_date", "horizon"])), ROLLING_SKILL_WINDOW)
        manifest["rolling_skill"] = skill
        manifest["direction_probability_status"] = "not_estimated"

        out = args.out
        if args.dry_run:
            out = Path("/tmp/gold_daily_dryrun")
            shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True, exist_ok=True)

        report = render_markdown(manifest, skill)
        atomic_write(out / "report.md", report)
        atomic_write(out / "gold_prediction.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        atomic_write(
            out / "gold_forecast.csv",
            pd.DataFrame(manifest["rows"]).to_csv(index=False),
        )

        # Append-only ledger; never rewrite history.
        ledger = out / "forecasts.jsonl"
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest, ensure_ascii=False) + "\n")

        _log(f"wrote {out}/report.md (version={version}, skill={skill})")

        if args.publish_dir and not args.dry_run:
            pub = args.publish_dir
            pub.mkdir(parents=True, exist_ok=True)
            atomic_write(pub / f"{manifest['origin_date']}.md", report)
            index = pub / "index.md"
            line = (
                f"- {manifest['origin_date']} · {version} · 基准 {manifest['origin_close']:.2f} · "
                f"skill {'n/a' if skill is None else f'{skill:+.3f}'} · [报告]({manifest['origin_date']}.md)\n"
            )
            with index.open("a", encoding="utf-8") as fh:
                fh.write(line)
            _log(f"published {pub}/{manifest['origin_date']}.md")

        if args.feishu_webhook and not args.dry_run:
            try:
                push_feishu(args.feishu_webhook, manifest, skill, out / "report.md")
                _log("feishu push ok")
            except Exception as exc:  # noqa: BLE001
                _log(f"WARN feishu push failed: {exc}")
                return 4
        return 0

    except DataError as exc:
        _log(f"ERROR data unavailable: {exc}")
        return 2
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        _log("ERROR unexpected failure\n" + traceback.format_exc())
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
