from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

REPO = Path(__file__).resolve().parents[1]
ML_DIR = REPO / "ml-service"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from data_collector import get_gold_market_collector
from models.external_direction import DEFAULT_EXTERNAL_DIRECTION_CSV
from models.predictor import run_price_prediction


ANALYSIS_DATE = pd.Timestamp("2026-03-25")
TARGET_END = pd.Timestamp("2026-04-05")
LOOKBACK = 120
RECENT_ORIGINS = 20
OUTPUT_DIR = REPO / "analysis_outputs" / "gold_4h_dailyclose_20260325"


def flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [str(col[0]).lower() for col in frame.columns]
    else:
        frame.columns = [str(col).lower() for col in frame.columns]
    return frame


def confidence_pct(up_probability: float | None) -> float | None:
    if up_probability is None or pd.isna(up_probability):
        return None
    return round(abs(float(up_probability) - 0.5) * 200, 2)


def direction_label(up_probability: float | None) -> str:
    if up_probability is None or pd.isna(up_probability):
        return "n/a"
    return "up" if float(up_probability) >= 0.5 else "down"


def compute_metrics(frame: pd.DataFrame) -> Dict[str, Any]:
    if frame.empty:
        return {
            "samples": 0,
            "mae": None,
            "rmse": None,
            "mape_pct": None,
            "bias_pct": None,
            "directional_accuracy_pct": None,
        }

    error = frame["pred_close"] - frame["actual_close"]
    safe_actual = frame["actual_close"].replace(0, np.nan)
    pct_error = (error / safe_actual) * 100
    abs_pct_error = (error.abs() / safe_actual) * 100
    directional_match = (
        np.sign(frame["pred_close"] - frame["origin_close"])
        == np.sign(frame["actual_close"] - frame["origin_close"])
    )

    return {
        "samples": int(len(frame)),
        "mae": round(float(error.abs().mean()), 4),
        "rmse": round(float(np.sqrt(np.mean(np.square(error)))), 4),
        "mape_pct": round(float(np.nanmean(abs_pct_error)), 4),
        "bias_pct": round(float(np.nanmean(pct_error)), 4),
        "directional_accuracy_pct": round(float(directional_match.mean() * 100), 2),
    }


def generate_future_schedule(source_id: str, last_close_date: pd.Timestamp, target_end: pd.Timestamp) -> pd.DatetimeIndex:
    trade_days = pd.bdate_range(last_close_date + pd.Timedelta(days=1), target_end)
    stamps: List[pd.Timestamp] = []
    if source_id == "SHFE_AU_MAIN":
        bar_hours = [0, 4, 12, 16]
    elif source_id == "COMEX_GC":
        bar_hours = [0, 4, 8, 12, 16, 20]
    else:
        raise ValueError(source_id)

    for day in trade_days:
        for hour in bar_hours:
            stamps.append(pd.Timestamp(day).replace(hour=hour))
    return pd.DatetimeIndex(stamps)


def predict_with_segments(
    df: pd.DataFrame,
    future_dates: pd.DatetimeIndex,
    lookback: int,
    kwargs: Dict[str, Any],
) -> Dict[str, Any]:
    history = df[["date", "close"]].copy().reset_index(drop=True)
    pending = list(pd.to_datetime(future_dates))
    collected: List[Dict[str, Any]] = []
    first_metrics: Dict[str, Any] | None = None

    while pending:
        chunk = pending[:30]
        pending = pending[30:]
        chunk_lookback = min(lookback, max(len(history) - len(chunk) - 1, 80))
        chunk_lookback = max(chunk_lookback, 80)
        result = run_price_prediction(
            df=history,
            horizon=len(chunk),
            lookback=chunk_lookback,
            future_dates=chunk,
            external_direction_csv=str(DEFAULT_EXTERNAL_DIRECTION_CSV),
            **kwargs,
        )
        if first_metrics is None:
            first_metrics = result["metrics"]

        pred_df = pd.DataFrame(result["prediction"])
        pred_df["date"] = pd.to_datetime(pred_df["date"], format="mixed")
        collected.extend(pred_df.to_dict(orient="records"))
        history = pd.concat([history, pred_df[["date", "close"]]], ignore_index=True)

    return {
        "prediction": collected,
        "metrics": first_metrics or {},
    }


def fetch_shfe_4h(collector) -> pd.DataFrame:
    df = collector.get_kline(
        "SHFE_AU_MAIN",
        period="4h",
        start_date="2025-11-01",
        end_date="2026-03-25",
        session="ALL",
    )
    frame = (
        df[["date", "close"]]
        .copy()
        .sort_values("date")
        .drop_duplicates(subset=["date"])
        .reset_index(drop=True)
    )
    frame["source_id"] = "SHFE_AU_MAIN"
    frame["source_name"] = "SHFE Gold Main Futures"
    frame["exchange"] = "SHFE"
    frame["market_type"] = "futures"
    return frame


def fetch_comex_4h() -> pd.DataFrame:
    cache_root = REPO / ".cache_yf"
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ["XDG_CACHE_HOME"] = str(cache_root)
    os.environ["HOME"] = str(cache_root)
    os.environ["USERPROFILE"] = str(cache_root)

    raw = yf.download(
        "GC=F",
        interval="60m",
        start="2025-11-01",
        end="2026-03-26",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        raise RuntimeError("COMEX 60m data unavailable")

    frame = flatten_yf_columns(raw).reset_index()
    frame.columns = [str(col).lower() for col in frame.columns]
    date_col = "datetime" if "datetime" in frame.columns else "date"
    frame["date"] = pd.to_datetime(frame[date_col]).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
    frame = frame[["date", "open", "high", "low", "close", "volume"]].copy()
    frame = (
        frame.sort_values("date")
        .set_index("date")
        .resample("4h", label="right", closed="right")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )
    frame = frame[frame["date"].dt.dayofweek < 5].reset_index(drop=True)
    frame = frame[["date", "close"]].copy()
    frame["source_id"] = "COMEX_GC"
    frame["source_name"] = "COMEX Gold Futures (4h, Asia/Shanghai bins)"
    frame["exchange"] = "COMEX"
    frame["market_type"] = "futures"
    return frame


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collector = get_gold_market_collector()

    issues: List[Dict[str, Any]] = [
        {
            "source_id": "SGE_AU9999_SPOT",
            "issue": "Current accessible feed only provides daily historical spot bars, not reproducible 4h history. Excluded from strict 4h rerun rather than approximated.",
        }
    ]
    latest_rows: List[Dict[str, Any]] = []
    forecast_rows: List[Dict[str, Any]] = []
    backtest_rows: List[Dict[str, Any]] = []

    sources = [fetch_shfe_4h(collector), fetch_comex_4h()]
    model_configs = [
        (
            "linear",
            {
                "model_type": "linear",
                "use_external_direction": False,
                "enable_direction_head": True,
                "enable_bias_correction": False,
            },
        ),
        (
            "boosting",
            {
                "model_type": "boosting",
                "use_external_direction": True,
                "enable_direction_head": True,
                "enable_bias_correction": True,
            },
        ),
        (
            "ensemble",
            {
                "model_type": "ensemble",
                "use_external_direction": False,
                "enable_direction_head": False,
                "enable_bias_correction": False,
            },
        ),
    ]

    for source_df in sources:
        source_df = source_df.sort_values("date").reset_index(drop=True)
        source_id = source_df.loc[0, "source_id"]
        source_name = source_df.loc[0, "source_name"]
        exchange = source_df.loc[0, "exchange"]
        market_type = source_df.loc[0, "market_type"]

        day_close_mask = source_df["date"].dt.hour == 16
        if not day_close_mask.any():
            issues.append({"source_id": source_id, "issue": "No 16:00 bars found after 4h resampling."})
            continue

        last_close_ts = pd.Timestamp(source_df.loc[day_close_mask, "date"].iloc[-1])
        latest_close = float(source_df.loc[source_df["date"] == last_close_ts, "close"].iloc[0])
        future_schedule = generate_future_schedule(source_id, last_close_ts.normalize(), TARGET_END)
        future_day_close_count = int((future_schedule.hour == 16).sum())
        resolved_lookback = min(LOOKBACK, max(len(source_df) - len(future_schedule) - 1, 80))
        resolved_lookback = max(resolved_lookback, 80)

        latest_rows.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "exchange": exchange,
                "market_type": market_type,
                "latest_bar_timestamp": source_df["date"].max().strftime("%Y-%m-%d %H:%M"),
                "latest_day_close_timestamp": last_close_ts.strftime("%Y-%m-%d %H:%M"),
                "latest_day_close_value": round(latest_close, 4),
                "row_count": int(len(source_df)),
                "forecast_day_close_count": future_day_close_count,
                "last_forecast_close_date": future_schedule[future_schedule.hour == 16][-1].strftime("%Y-%m-%d %H:%M"),
            }
        )

        for model_name, kwargs in model_configs:
            result = predict_with_segments(
                df=source_df[["date", "close"]],
                lookback=resolved_lookback,
                future_dates=future_schedule,
                kwargs=kwargs,
            )
            predicted = pd.DataFrame(result["prediction"])
            predicted["date"] = pd.to_datetime(predicted["date"], format="mixed")
            predicted = predicted[predicted["date"].dt.hour == 16].reset_index(drop=True)

            for _, row in predicted.iterrows():
                up_prob = row.get("up_probability")
                forecast_rows.append(
                    {
                        "source_id": source_id,
                        "source_name": source_name,
                        "exchange": exchange,
                        "market_type": market_type,
                        "forecast_date": row["date"].strftime("%Y-%m-%d"),
                        "forecast_close_time": row["date"].strftime("%H:%M"),
                        "model": model_name,
                        "predicted_close": round(float(row["close"]), 4),
                        "predicted_return_pct_vs_latest_close": round((float(row["close"]) / latest_close - 1) * 100, 4),
                        "up_probability": None if pd.isna(up_prob) else round(float(up_prob), 4),
                        "confidence_pct": confidence_pct(up_prob),
                        "direction": direction_label(up_prob),
                        "internal_mape_pct": None
                        if result["metrics"].get("mape") is None
                        else round(float(result["metrics"]["mape"]), 4),
                        "internal_direction_accuracy_pct": None
                        if result["metrics"].get("direction_accuracy") is None
                        else round(float(result["metrics"]["direction_accuracy"]), 2),
                        "lookback_used": resolved_lookback,
                    }
                )

        close_indices = source_df.index[source_df["date"].dt.hour == 16].tolist()
        eligible_origins: List[tuple[int, List[int]]] = []
        for origin_idx in close_indices:
            future_idx: List[int] = []
            future_close_seen = 0
            cursor = origin_idx + 1
            while cursor < len(source_df) and future_close_seen < future_day_close_count:
                future_idx.append(cursor)
                if source_df.loc[cursor, "date"].hour == 16:
                    future_close_seen += 1
                cursor += 1
            if future_close_seen == future_day_close_count:
                eligible_origins.append((origin_idx, future_idx))
        eligible_origins = eligible_origins[-RECENT_ORIGINS:]

        for model_name, kwargs in model_configs:
            eval_rows: List[Dict[str, Any]] = []
            for origin_idx, future_idx in eligible_origins:
                history = source_df.loc[:origin_idx, ["date", "close"]].copy()
                future_dates = source_df.loc[future_idx, "date"].tolist()
                bt_lookback = min(LOOKBACK, max(len(history) - min(len(future_dates), 30) - 1, 80))
                bt_lookback = max(bt_lookback, 80)
                result = predict_with_segments(
                    df=history,
                    lookback=bt_lookback,
                    future_dates=future_dates,
                    kwargs=kwargs,
                )
                origin_close = float(source_df.loc[origin_idx, "close"])
                pred_df = pd.DataFrame(result["prediction"])
                pred_df["date"] = pd.to_datetime(pred_df["date"], format="mixed")
                actual_df = source_df.loc[future_idx, ["date", "close"]].rename(columns={"close": "actual_close"}).copy()
                merged = pred_df.merge(actual_df, on="date", how="left")
                merged = merged[merged["date"].dt.hour == 16].reset_index(drop=True)
                for _, item in merged.iterrows():
                    eval_rows.append(
                        {
                            "origin_close": origin_close,
                            "pred_close": float(item["close"]),
                            "actual_close": float(item["actual_close"]),
                        }
                    )

            metrics = compute_metrics(pd.DataFrame(eval_rows))
            backtest_rows.append(
                {
                    "source_id": source_id,
                    "source_name": source_name,
                    "exchange": exchange,
                    "market_type": market_type,
                    "model": model_name,
                    "recent_origin_count": len(eligible_origins),
                    "forecast_day_close_count": future_day_close_count,
                    **metrics,
                }
            )

    latest_df = pd.DataFrame(latest_rows)
    forecast_df = (
        pd.DataFrame(forecast_rows)
        .sort_values(["source_id", "forecast_date", "model"])
        .reset_index(drop=True)
    )
    backtest_df = (
        pd.DataFrame(backtest_rows)
        .sort_values(["source_id", "model"])
        .reset_index(drop=True)
    )
    issues_df = pd.DataFrame(issues)

    forecast_wide = forecast_df.pivot_table(
        index=[
            "source_id",
            "source_name",
            "exchange",
            "market_type",
            "forecast_date",
            "forecast_close_time",
        ],
        columns="model",
        values=[
            "predicted_close",
            "confidence_pct",
            "direction",
            "predicted_return_pct_vs_latest_close",
        ],
        aggfunc="first",
    )
    forecast_wide.columns = [f"{a}_{b}" for a, b in forecast_wide.columns]
    forecast_wide = (
        forecast_wide.reset_index()
        .sort_values(["source_id", "forecast_date"])
        .reset_index(drop=True)
    )

    best_df = (
        backtest_df.sort_values(["source_id", "mape_pct", "mae"])
        .groupby("source_id", as_index=False)
        .first()
    )

    latest_df.to_csv(OUTPUT_DIR / "latest_sources.csv", index=False, encoding="utf-8-sig")
    forecast_df.to_csv(OUTPUT_DIR / "forecast_dailyclose_long.csv", index=False, encoding="utf-8-sig")
    forecast_wide.to_csv(OUTPUT_DIR / "forecast_dailyclose_wide.csv", index=False, encoding="utf-8-sig")
    backtest_df.to_csv(OUTPUT_DIR / "backtest_dailyclose_summary.csv", index=False, encoding="utf-8-sig")
    best_df.to_csv(OUTPUT_DIR / "best_model_summary.csv", index=False, encoding="utf-8-sig")
    issues_df.to_csv(OUTPUT_DIR / "issues.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# Gold 4h Model with Daily Close Output",
        "",
        f"- analysis_date: {ANALYSIS_DATE.strftime('%Y-%m-%d')}",
        f"- target_calendar_end: {TARGET_END.strftime('%Y-%m-%d')}",
        "- output rule: model uses 4h bars, but only the 16:00 close bar is exposed as the daily pre-close value.",
        "- note: SGE spot was excluded from the strict 4h rerun because current accessible feeds do not provide reproducible 4h history.",
        "",
        "## Source Coverage",
        "",
        latest_df.to_markdown(index=False) if not latest_df.empty else "No sources.",
        "",
        "## Recent Backtest Summary",
        "",
        backtest_df.to_markdown(index=False) if not backtest_df.empty else "No backtest results.",
        "",
        "## Daily Close Forecast Table",
        "",
        forecast_wide.to_markdown(index=False) if not forecast_wide.empty else "No forecast results.",
        "",
        "## Issues",
        "",
        issues_df.to_markdown(index=False) if not issues_df.empty else "No issues.",
        "",
    ]
    (OUTPUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "output_dir": str(OUTPUT_DIR),
        "sources": latest_df["source_id"].tolist(),
        "forecast_rows": int(len(forecast_df)),
        "backtest_rows": int(len(backtest_df)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n=== latest_sources ===")
    print(latest_df.to_string(index=False))
    print("\n=== backtest ===")
    print(backtest_df.to_string(index=False))
    print("\n=== forecast_wide ===")
    print(forecast_wide.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
