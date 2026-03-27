from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd

# Keep imports stable regardless of launch cwd.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_collector import get_gold_market_collector
from models.external_direction import DEFAULT_EXTERNAL_DIRECTION_CSV
from models.predictor import run_price_prediction


def _format_ts(ts: pd.Timestamp) -> str:
    stamp = pd.Timestamp(ts)
    if stamp.hour == 0 and stamp.minute == 0 and stamp.second == 0:
        return stamp.strftime("%Y-%m-%d")
    return stamp.strftime("%Y-%m-%d %H:%M")


def _safe_mape(actual: pd.Series, predicted: pd.Series) -> float | None:
    safe_actual = actual.replace(0, np.nan)
    arr = (predicted - actual).abs() / safe_actual
    value = float(np.nanmean(arr) * 100)
    if np.isnan(value):
        return None
    return value


def _compute_metrics(frame: pd.DataFrame) -> Dict[str, Any]:
    if frame.empty:
        return {
            "samples": 0,
            "mae": None,
            "rmse": None,
            "mape": None,
            "bias_pct": None,
            "directional_accuracy": None,
            "aggressive_ratio_2pct": None,
            "aggressive_ratio_5pct": None,
        }

    error = frame["pred_close"] - frame["actual_close"]
    abs_pct_error = (error.abs() / frame["actual_close"].replace(0, np.nan)) * 100
    pct_error = (error / frame["actual_close"].replace(0, np.nan)) * 100

    directional_match = (
        np.sign(frame["pred_close"] - frame["origin_close"])
        == np.sign(frame["actual_close"] - frame["origin_close"])
    )

    return {
        "samples": int(len(frame)),
        "mae": float(error.abs().mean()),
        "rmse": float(np.sqrt(np.mean(np.square(error)))),
        "mape": _safe_mape(frame["actual_close"], frame["pred_close"]),
        "bias_pct": float(np.nanmean(pct_error)),
        "directional_accuracy": float(directional_match.mean() * 100),
        "aggressive_ratio_2pct": float((abs_pct_error > 2).mean() * 100),
        "aggressive_ratio_5pct": float((abs_pct_error > 5).mean() * 100),
    }


def _build_regime_summary(frame: pd.DataFrame) -> Dict[str, Any]:
    if frame.empty:
        return {"volatility_cutoff": None, "regimes": {}}

    vol_cutoff = float(frame["origin_vol_20"].quantile(0.75))
    tagged = frame.copy()
    tagged["regime"] = np.where(tagged["origin_vol_20"] >= vol_cutoff, "high_vol", "normal_vol")

    result: Dict[str, Any] = {"volatility_cutoff": vol_cutoff, "regimes": {}}
    for regime in ["normal_vol", "high_vol"]:
        result["regimes"][regime] = _compute_metrics(tagged[tagged["regime"] == regime])
    return result


def _iter_origins(
    data: pd.DataFrame,
    lookback: int,
    max_horizon: int,
    stride: int,
) -> Iterable[int]:
    start_index = max(lookback, 80)
    end_index = len(data) - max_horizon
    for origin_idx in range(start_index, end_index, max(stride, 1)):
        yield origin_idx


def _run_single_model(
    data: pd.DataFrame,
    lookback: int,
    max_horizon: int,
    stride: int,
    model_label: str,
    model_type: str,
    use_external_direction: bool,
    external_direction_csv: str | None,
    enable_direction_head: bool,
    enable_bias_correction: bool,
    calibration_origin_cap: int,
) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    skipped = 0

    for origin_idx in _iter_origins(data, lookback=lookback, max_horizon=max_horizon, stride=stride):
        history = data.loc[:origin_idx, ["date", "close"]].copy()
        origin_row = data.iloc[origin_idx]
        origin_close = float(origin_row["close"])
        origin_date = pd.Timestamp(origin_row["date"])
        origin_vol_20 = float(origin_row["vol_20"])

        try:
            pred_result = run_price_prediction(
                history,
                horizon=max_horizon,
                lookback=lookback,
                model_type=model_type,
                use_external_direction=use_external_direction,
                external_direction_csv=external_direction_csv,
                enable_direction_head=enable_direction_head,
                enable_bias_correction=enable_bias_correction,
                calibration_origin_cap=calibration_origin_cap,
            )
        except Exception:
            skipped += 1
            continue

        pred_series = pred_result["prediction"]
        for horizon in range(1, max_horizon + 1):
            target_idx = origin_idx + horizon
            if target_idx >= len(data):
                continue
            target_row = data.iloc[target_idx]
            records.append(
                {
                    "model_label": model_label,
                    "origin_date": _format_ts(origin_date),
                    "target_date": _format_ts(pd.Timestamp(target_row["date"])),
                    "horizon": horizon,
                    "origin_close": origin_close,
                    "pred_close": float(pred_series[horizon - 1]["close"]),
                    "actual_close": float(target_row["close"]),
                    "origin_vol_20": origin_vol_20,
                    "model_internal_mape": pred_result["metrics"].get("mape"),
                }
            )

    return {"records": records, "skipped": skipped}


def run_gold_rolling_backtest(
    source: str = "SHFE_AU_MAIN",
    period: str = "daily",
    session: str = "ALL",
    lookback: int = 240,
    max_horizon: int = 5,
    stride: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
    external_direction_csv: str | None = None,
    calibration_origin_cap: int = 8,
) -> Dict[str, Any]:
    collector = get_gold_market_collector()
    start = start_date or "2021-01-01"
    end = end_date or datetime.now().strftime("%Y-%m-%d")

    raw = collector.get_kline(
        source=source,
        period=period,
        start_date=start,
        end_date=end,
        session=session,
    )
    if raw.empty or len(raw) < lookback + max_horizon + 30:
        raise RuntimeError(
            f"历史数据不足，无法完成滚动回测: period={period}, rows={len(raw)}, "
            f"need>={lookback + max_horizon + 30}"
        )

    data = raw[["date", "close"]].copy().sort_values("date").reset_index(drop=True)
    data["ret_1"] = data["close"].pct_change()
    data["vol_20"] = data["ret_1"].rolling(20).std().bfill().fillna(0.0)

    model_configs = [
        {
            "model_label": "linear_baseline",
            "model_type": "linear",
            "use_external_direction": False,
            "enable_direction_head": False,
            "enable_bias_correction": False,
        },
        {
            "model_label": "boosting_external",
            "model_type": "boosting",
            "use_external_direction": True,
            "enable_direction_head": True,
            "enable_bias_correction": True,
        },
        {
            "model_label": "ensemble_fusion",
            "model_type": "ensemble",
            "use_external_direction": False,
            "enable_direction_head": False,
            "enable_bias_correction": False,
        },
    ]

    records: List[Dict[str, Any]] = []
    skipped_by_model: Dict[str, int] = {}
    for cfg in model_configs:
        model_result = _run_single_model(
            data=data,
            lookback=lookback,
            max_horizon=max_horizon,
            stride=stride,
            model_label=cfg["model_label"],
            model_type=cfg["model_type"],
            use_external_direction=cfg["use_external_direction"],
            external_direction_csv=external_direction_csv,
            enable_direction_head=cfg["enable_direction_head"],
            enable_bias_correction=cfg["enable_bias_correction"],
            calibration_origin_cap=calibration_origin_cap,
        )
        records.extend(model_result["records"])
        skipped_by_model[cfg["model_label"]] = model_result["skipped"]

    if not records:
        raise RuntimeError("回测没有产生有效样本")

    detail = pd.DataFrame(records)
    detail["error"] = detail["pred_close"] - detail["actual_close"]
    detail["abs_pct_error"] = (
        (detail["error"].abs() / detail["actual_close"].replace(0, np.nan)) * 100
    )

    horizon_summary: Dict[str, Any] = {}
    for model_label in detail["model_label"].unique():
        model_frame = detail[detail["model_label"] == model_label]
        horizon_summary[model_label] = {}
        for horizon in range(1, max_horizon + 1):
            horizon_frame = model_frame[model_frame["horizon"] == horizon]
            horizon_summary[model_label][f"T+{horizon}"] = {
                "overall": _compute_metrics(horizon_frame),
                "regime": _build_regime_summary(horizon_frame),
            }

    model_comparison: Dict[str, Any] = {}
    baseline = horizon_summary.get("linear_baseline", {})
    boosted = horizon_summary.get("boosting_external", {})
    for horizon in range(1, max_horizon + 1):
        key = f"T+{horizon}"
        base_overall = baseline.get(key, {}).get("overall", {})
        boost_overall = boosted.get(key, {}).get("overall", {})
        if not base_overall or not boost_overall:
            continue
        base_mape = base_overall.get("mape")
        boost_mape = boost_overall.get("mape")
        base_mae = base_overall.get("mae")
        boost_mae = boost_overall.get("mae")
        model_comparison[key] = {
            "mape_delta": (boost_mape - base_mape) if base_mape is not None and boost_mape is not None else None,
            "mae_delta": (boost_mae - base_mae) if base_mae is not None and boost_mae is not None else None,
            "directional_accuracy_delta": (
                boost_overall.get("directional_accuracy", 0) - base_overall.get("directional_accuracy", 0)
            ),
        }

    global_summary = {
        "source": source,
        "period": period,
        "session": session,
        "start_date": start,
        "end_date": end,
        "lookback": lookback,
        "max_horizon": max_horizon,
        "stride": stride,
        "external_direction_csv": external_direction_csv,
        "calibration_origin_cap": calibration_origin_cap,
        "raw_rows": int(len(data)),
        "origin_count": int(detail["origin_date"].nunique()),
        "sample_count": int(len(detail)),
        "skipped_origin_count": skipped_by_model,
    }

    return {
        "summary": global_summary,
        "horizon_summary": horizon_summary,
        "model_comparison": model_comparison,
        "detail": detail,
    }


def _write_report(output_dir: Path, result: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "backtest_summary.json"
    detail_path = output_dir / "backtest_detail.csv"
    report_path = output_dir / "backtest_report.md"

    summary_path.write_text(
        json.dumps(
            {
                "summary": result["summary"],
                "horizon_summary": result["horizon_summary"],
                "model_comparison": result["model_comparison"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    result["detail"].to_csv(detail_path, index=False)

    lines: List[str] = [
        "# Gold Rolling Backtest",
        "",
        f"- source: {result['summary']['source']}",
        f"- period: {result['summary'].get('period', 'daily')}",
        f"- session: {result['summary'].get('session', 'ALL')}",
        f"- window: {result['summary']['start_date']} ~ {result['summary']['end_date']}",
        f"- lookback: {result['summary']['lookback']}",
        f"- max_horizon: {result['summary']['max_horizon']}",
        f"- origin_count: {result['summary']['origin_count']}",
        f"- sample_count: {result['summary']['sample_count']}",
        "",
    ]

    for model_label, model_metrics in result["horizon_summary"].items():
        lines.extend([f"## Model: {model_label}", ""])
        for horizon_name, metrics in model_metrics.items():
            overall = metrics["overall"]
            lines.extend(
                [
                    f"### {horizon_name}",
                    "",
                    f"- MAE: {overall['mae']}",
                    f"- RMSE: {overall['rmse']}",
                    f"- MAPE: {overall['mape']}",
                    f"- Bias%: {overall['bias_pct']}",
                    f"- Directional Accuracy%: {overall['directional_accuracy']}",
                    f"- Aggressive >2%%: {overall['aggressive_ratio_2pct']}",
                    f"- Aggressive >5%%: {overall['aggressive_ratio_5pct']}",
                    "",
                ]
            )

    lines.extend(["## Model Delta (boosting_external - linear_baseline)", ""])
    for horizon_name, delta in result["model_comparison"].items():
        lines.extend(
            [
                f"- {horizon_name}: MAPE delta={delta['mape_delta']}, MAE delta={delta['mae_delta']}, Direction delta={delta['directional_accuracy_delta']}",
            ]
        )
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gold rolling backtest for current predictor")
    parser.add_argument("--source", default="SHFE_AU_MAIN")
    parser.add_argument(
        "--period",
        default="daily",
        choices=["daily", "weekly", "monthly", "4h", "5min", "15min", "30min", "60min"],
    )
    parser.add_argument("--session", default="ALL", choices=["ALL", "DAY", "NIGHT"])
    parser.add_argument("--lookback", type=int, default=240)
    parser.add_argument("--max-horizon", type=int, default=5)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--start-date", default="2021-01-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--external-direction-csv", default=str(DEFAULT_EXTERNAL_DIRECTION_CSV))
    parser.add_argument("--calibration-origin-cap", type=int, default=8)
    parser.add_argument("--output-dir", default="/tmp/gold-backtest")
    args = parser.parse_args()

    result = run_gold_rolling_backtest(
        source=args.source,
        period=args.period,
        session=args.session,
        lookback=args.lookback,
        max_horizon=args.max_horizon,
        stride=args.stride,
        start_date=args.start_date,
        end_date=args.end_date,
        external_direction_csv=args.external_direction_csv,
        calibration_origin_cap=args.calibration_origin_cap,
    )
    output_dir = Path(args.output_dir).expanduser().resolve()
    _write_report(output_dir, result)
    print(f"Backtest report generated at: {output_dir}")
    print(f"Summary file: {output_dir / 'backtest_summary.json'}")
    print(f"Detail file: {output_dir / 'backtest_detail.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
