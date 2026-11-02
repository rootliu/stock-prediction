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

from models.versions import FALLBACK, predict_close  # noqa: E402

DEFAULT_CALIBRATION = ROOT / "config/gold_versions/calibration.json"
DEFAULT_VERSION = "v7"
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
    entry = cal.get(str(int(horizon)))
    if not entry:
        return (None, None)
    return (round(pred + entry["q_low"], 2), round(pred + entry["q_high"], 2))


def rolling_skill(history: pd.DataFrame, version: str, window: int = ROLLING_SKILL_WINDOW) -> Optional[float]:
    """Skill over the most recent matured rows (history only, never the forecast)."""
    matured = history.dropna(subset=["actual_close"]).copy()
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


def build_predictions_live(horizons: int) -> pd.DataFrame:
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

    daily = fetch_shfe_au_daily()
    if daily.empty:
        raise RuntimeError("empty SHFE daily series")
    last_date = pd.Timestamp(daily["date"].iloc[-1]).normalize()
    target_end = last_date + pd.Timedelta(days=horizons * 2 + 4)
    future, _meta = build_future_trade_dates(last_date, target_end)
    if len(future) == 0:
        raise RuntimeError("no future trading day resolved")

    predictions = run_direct_multi_day_prediction(
        daily_df=daily,
        comex_daily=fetch_comex_daily(),
        usdcny_daily=fetch_usdcny_daily(),
        cross_market=fetch_cross_market(),
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
    return pd.DataFrame(rows)


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
    parser.add_argument("--dry-run", action="store_true", help="write to a temp dir, do not push")
    args = parser.parse_args()

    try:
        if args.live and args.predictions_csv:
            raise SystemExit("use either --live or --predictions-csv, not both")
        history = pd.DataFrame(columns=["origin_date", "target_date", "horizon", "origin_close", "pred_close", "actual_close"])
        if args.predictions_csv:
            pred = pd.read_csv(args.predictions_csv, parse_dates=["origin_date", "target_date"])
            if "actual_close" not in pred:
                pred["actual_close"] = np.nan
        elif args.live:
            pred = build_predictions_live(args.horizons)
        else:
            raise SystemExit("one of --live / --predictions-csv is required")

        if pred.empty:
            _log("ERROR no predictions; upstream produced nothing")
            return 2

        origin = pd.Timestamp(args.origin) if args.origin else pd.Timestamp(pred["origin_date"].max())
        forecast = pred[pred["origin_date"] == origin].copy()
        history = pred[(pred["origin_date"] < origin) & pred["actual_close"].notna()].copy()
        if forecast.empty:
            _log(f"ERROR no forecast rows for origin {origin.date()}")
            return 2
        if forecast["origin_close"].isna().any() or (forecast["origin_close"] <= 0).any():
            _log("ERROR invalid origin_close in forecast rows")
            return 2

        version = args.version
        gate_note = ""
        skill = rolling_skill(history, version)
        if skill is not None and skill < SKILL_FLOOR:
            gate_note = f"{version} rolling skill {skill:+.3f} < {SKILL_FLOOR:+.2f} -> fell back to {FALLBACK}"
            _log(gate_note)
            version = FALLBACK

        cal = load_calibration(args.calibration, version)
        manifest = build_outputs(forecast, version, cal, gate_note)
        manifest["generated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        manifest["calibration_source"] = str(args.calibration)

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
            fh.write(json.dumps({k: v for k, v in manifest.items() if k != "rows"}, ensure_ascii=False) + "\n")

        _log(f"wrote {out}/report.md (version={version}, skill={skill})")

        if args.feishu_webhook and not args.dry_run:
            try:
                push_feishu(args.feishu_webhook, manifest, skill, out / "report.md")
                _log("feishu push ok")
            except Exception as exc:  # noqa: BLE001
                _log(f"WARN feishu push failed: {exc}")
                return 4
        return 0

    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        _log("ERROR unexpected failure\n" + traceback.format_exc())
        return 4


if __name__ == "__main__":
    raise SystemExit(main())