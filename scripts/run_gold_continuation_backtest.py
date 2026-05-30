#!/usr/bin/env python3
"""Run latest continuation backtest for the gold direct model.

Unlike the older ad-hoc report script, this includes partial latest targets:
for example, if the newest SHFE bar is only one trading day after an origin,
that T+1 sample is still evaluated. This is important during volatile weeks
where the newest one or two sessions are the main diagnostic target.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ML_DIR = ROOT / "ml-service"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from run_gold_analysis import fetch_comex_daily, fetch_cross_market, fetch_shfe_au_daily, fetch_usdcny_daily
from models.multi_day_direct_predictor import run_direct_multi_day_prediction


def _build_records(
    shfe: pd.DataFrame,
    comex: pd.DataFrame,
    usdcny: pd.DataFrame,
    cross: pd.DataFrame,
    cutoff: pd.Timestamp,
    lookback: int,
    max_horizon: int,
) -> pd.DataFrame:
    if cutoff not in set(pd.to_datetime(shfe["date"])):
        raise SystemExit(f"cutoff {cutoff.date()} not found in SHFE daily data")

    cutoff_idx = int(shfe.index[shfe["date"] == cutoff][0])
    start_idx = max(lookback, cutoff_idx - max_horizon + 1)
    end_idx = len(shfe) - 2
    records: List[Dict[str, Any]] = []

    for origin_idx in range(start_idx, end_idx + 1):
        history = shfe.iloc[: origin_idx + 1].copy()
        origin_date = pd.Timestamp(history.iloc[-1]["date"])
        origin_close = float(history.iloc[-1]["close"])
        available_horizon = min(max_horizon, len(shfe) - origin_idx - 1)
        future_dates = [
            pd.Timestamp(shfe.iloc[origin_idx + horizon]["date"])
            for horizon in range(1, available_horizon + 1)
        ]
        if not any(date > cutoff for date in future_dates):
            continue

        predictions = run_direct_multi_day_prediction(
            daily_df=history,
            comex_daily=comex[comex["date"] <= origin_date],
            usdcny_daily=usdcny[usdcny["date"] <= origin_date],
            cross_market=cross[cross["date"] <= origin_date],
            target_dates=future_dates,
            lookback_days=lookback,
            verbose=False,
            cot_daily=None,
        )

        for horizon, pred in enumerate(predictions, start=1):
            target_idx = origin_idx + horizon
            target_date = pd.Timestamp(shfe.iloc[target_idx]["date"])
            if target_date <= cutoff:
                continue

            actual_close = float(shfe.iloc[target_idx]["close"])
            pred_close = float(pred["close"])
            abs_error = abs(pred_close - actual_close)
            ape_pct = abs_error / max(abs(actual_close), 1e-8) * 100
            pred_delta = pred_close - origin_close
            actual_delta = actual_close - origin_close
            model_details = pred.get("model_details", {}) or {}

            records.append(
                {
                    "origin_date": origin_date.strftime("%Y-%m-%d"),
                    "target_date": target_date.strftime("%Y-%m-%d"),
                    "horizon": horizon,
                    "origin_close": round(origin_close, 2),
                    "pred_close": round(pred_close, 2),
                    "actual_close": round(actual_close, 2),
                    "pred_delta": round(pred_delta, 4),
                    "actual_delta": round(actual_delta, 4),
                    "confidence": float(pred.get("confidence", 0.0)),
                    "abs_error": round(abs_error, 4),
                    "ape_pct": round(ape_pct, 6),
                    "dir_match": bool(np.sign(pred_delta) == np.sign(actual_delta)),
                    "direction": pred.get("direction"),
                    "regime": pred.get("regime"),
                    "pre_guard_return_pct": model_details.get("pre_guard_return_pct"),
                    "pred_return_pct": model_details.get("pred_return_pct"),
                    "direction_guard": model_details.get("direction_guard"),
                    "confidence_guard": model_details.get("confidence_guard"),
                    "up_probability": model_details.get("up_probability"),
                    "trend_regime_code": model_details.get("trend_regime_code"),
                    "trend_signal": model_details.get("trend_signal"),
                    "jump_regime_code": model_details.get("jump_regime_code"),
                    "jump_signal": model_details.get("jump_signal"),
                    "branch_name": model_details.get("branch_name"),
                    "branch_used": model_details.get("branch_used"),
                }
            )

    result = pd.DataFrame(records)
    if result.empty:
        raise SystemExit("no continuation records generated")
    return result


def _summarize(bt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    for horizon in sorted(bt["horizon"].unique()):
        sub = bt[bt["horizon"] == horizon]
        summary_rows.append(
            {
                "周期": f"T+{horizon}",
                "样本数": int(len(sub)),
                "MAE(元/克)": round(float(sub["abs_error"].mean()), 2),
                "MAPE%": round(float(sub["ape_pct"].mean()), 2),
                "方向准确率%": round(float(sub["dir_match"].mean() * 100), 1),
                "平均信心度": round(float(sub["confidence"].mean()), 1),
            }
        )
    summary = pd.DataFrame(summary_rows)

    bucket_rows = []
    for label, mask in [
        ("T+1~T+3", bt["horizon"].between(1, 3)),
        ("T+4~T+5", bt["horizon"].between(4, 5)),
        ("T+5~T+10", bt["horizon"].between(5, 10)),
    ]:
        sub = bt[mask]
        if sub.empty:
            continue
        bucket_rows.append(
            {
                "区间": label,
                "样本数": int(len(sub)),
                "MAPE%": round(float(sub["ape_pct"].mean()), 2),
                "方向准确率%": round(float(sub["dir_match"].mean() * 100), 1),
                "平均信心度": round(float(sub["confidence"].mean()), 1),
            }
        )
    buckets = pd.DataFrame(bucket_rows)

    by_target = (
        bt.groupby("target_date", as_index=False)
        .agg(
            样本数=("pred_close", "size"),
            平均预测价=("pred_close", "mean"),
            实际收盘=("actual_close", "first"),
            平均偏差率=("ape_pct", "mean"),
            方向准确率=("dir_match", lambda values: float(values.mean() * 100)),
            平均信心度=("confidence", "mean"),
        )
    )
    for col in ["平均预测价", "实际收盘", "平均偏差率", "方向准确率", "平均信心度"]:
        by_target[col] = by_target[col].round(3)
    return summary, buckets, by_target


def _write_outputs(
    bt: pd.DataFrame,
    summary: pd.DataFrame,
    buckets: pd.DataFrame,
    by_target: pd.DataFrame,
    output_dirs: list[Path],
    report_name: str,
    cutoff: pd.Timestamp,
    latest_trade_date: pd.Timestamp,
    latest_close: float,
) -> None:
    recent_targets = sorted(bt["target_date"].unique())[-2:]
    recent = bt[bt["target_date"].isin(recent_targets)].copy()
    recent_display = recent[
        [
            "origin_date",
            "target_date",
            "horizon",
            "origin_close",
            "pred_close",
            "actual_close",
            "pred_delta",
            "actual_delta",
            "confidence",
            "ape_pct",
            "dir_match",
            "direction_guard",
            "confidence_guard",
            "branch_name",
        ]
    ].sort_values(["target_date", "horizon", "origin_date"])

    overall_dir_acc = round(float(bt["dir_match"].mean() * 100), 2)
    overall_conf = round(float(bt["confidence"].mean()), 2)
    lines = [
        f"# Gold Continuation Backtest ({cutoff.date()} to {latest_trade_date.date()})",
        "",
        f"- cutoff_date: {cutoff.date()}",
        f"- latest_trade_date: {latest_trade_date.date()}",
        f"- latest_close: {latest_close:.2f}",
        f"- records: {len(bt)}",
        f"- overall_direction_accuracy: {overall_dir_acc}%",
        f"- overall_confidence: {overall_conf}",
        "- note: variable-horizon evaluation includes partial latest targets, including T+1 into the latest trading day.",
        "",
        "## Horizon Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Bucket Summary",
        "",
        buckets.to_markdown(index=False),
        "",
        "## By Target Date",
        "",
        by_target.to_markdown(index=False),
        "",
        "## Recent Volatile Targets",
        "",
        recent_display.to_markdown(index=False),
        "",
    ]

    for out_dir in output_dirs:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{report_name}.md").write_text("\n".join(lines), encoding="utf-8")
        bt.to_csv(out_dir / f"{report_name}.csv", index=False)
        summary.to_csv(out_dir / f"{report_name}_summary.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gold continuation backtest with latest partial horizons.")
    parser.add_argument("--cutoff", default="2026-05-22", help="Only targets after this SHFE date are evaluated.")
    parser.add_argument("--lookback", type=int, default=240)
    parser.add_argument("--max-horizon", type=int, default=10)
    parser.add_argument("--report-dir", default="/Users/rootliu/code/report")
    parser.add_argument("--repo-report-dir", default=str(ROOT / "report"))
    args = parser.parse_args()

    cutoff = pd.Timestamp(args.cutoff)
    shfe = fetch_shfe_au_daily().sort_values("date").reset_index(drop=True)
    comex = fetch_comex_daily().sort_values("date").reset_index(drop=True)
    usdcny = fetch_usdcny_daily().sort_values("date").reset_index(drop=True)
    cross = fetch_cross_market().sort_values("date").reset_index(drop=True)

    bt = _build_records(
        shfe=shfe,
        comex=comex,
        usdcny=usdcny,
        cross=cross,
        cutoff=cutoff,
        lookback=args.lookback,
        max_horizon=args.max_horizon,
    )
    summary, buckets, by_target = _summarize(bt)

    latest_trade_date = pd.Timestamp(shfe.iloc[-1]["date"])
    latest_close = float(shfe.iloc[-1]["close"])
    report_name = f"gold_continuation_backtest_{cutoff.strftime('%Y-%m-%d')}_to_{latest_trade_date.strftime('%Y-%m-%d')}"
    _write_outputs(
        bt=bt,
        summary=summary,
        buckets=buckets,
        by_target=by_target,
        output_dirs=[Path(args.report_dir), Path(args.repo_report_dir)],
        report_name=report_name,
        cutoff=cutoff,
        latest_trade_date=latest_trade_date,
        latest_close=latest_close,
    )

    print("REPORT_NAME", report_name)
    print("overall_direction_accuracy", round(float(bt["dir_match"].mean() * 100), 2))
    print("overall_confidence", round(float(bt["confidence"].mean()), 2))
    print("\nHORIZON SUMMARY")
    print(summary.to_string(index=False))
    print("\nBUCKET SUMMARY")
    print(buckets.to_string(index=False))
    print("\nBY TARGET")
    print(by_target.to_string(index=False))


if __name__ == "__main__":
    main()
