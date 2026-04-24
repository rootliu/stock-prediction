"""Stable-signature adapter for gold direct-horizon GBM predictor.

Exposes a flat-dict interface to external integrations (e.g. gold-kronos)
so they don't need to dig into `model_details` nested structures.

This module must NOT fetch data itself — callers are responsible for
providing the required DataFrames. Keeps the adapter pure and testable.
"""

from typing import Any, Dict, List, Optional, Sequence

import pandas as pd


def predict_direct_gbm(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    target_dates: Sequence[pd.Timestamp],
    lookback_days: int = 240,
    verbose: bool = False,
    cot_daily: pd.DataFrame = None,
) -> List[Dict[str, Any]]:
    """Predict GBM direct multi-horizon closes and return flat dicts.

    Args:
        daily_df: SHFE AU daily OHLCV (date, open, high, low, close, volume, amount)
        comex_daily: COMEX gold daily (date, close)
        usdcny_daily: USDCNY daily (date, usdcny)
        cross_market: DXY/VIX/US10Y merged (date, dxy, vix, us10y)
        target_dates: future dates to predict (horizon = index + 1)
        lookback_days: training window size
        verbose: print progress

    Returns:
        List of dicts, one per target_date, with keys:
            date, close, direction, confidence, range_low, range_high,
            regime, horizon_days, pred_return_pct, up_probability,
            test_mape_pct, test_direction_accuracy, jump_regime_code,
            jump_signal, branch_name, effective_base
    """
    from models.multi_day_direct_predictor import run_direct_multi_day_prediction

    if not target_dates:
        return []

    raw = run_direct_multi_day_prediction(
        daily_df=daily_df,
        comex_daily=comex_daily,
        usdcny_daily=usdcny_daily,
        cross_market=cross_market,
        target_dates=list(target_dates),
        lookback_days=lookback_days,
        verbose=verbose,
        cot_daily=cot_daily,
    )

    flat: List[Dict[str, Any]] = []
    for r in raw:
        md = r.get("model_details", {}) or {}
        flat.append({
            "date": r["date"],
            "close": r["close"],
            "direction": r["direction"],
            "confidence": r["confidence"],
            "range_low": r["range_low"],
            "range_high": r["range_high"],
            "regime": r["regime"],
            "horizon_days": md.get("horizon_days"),
            "pred_return_pct": md.get("pred_return_pct"),
            "up_probability": md.get("up_probability"),
            "test_mape_pct": md.get("test_mape_pct"),
            "test_direction_accuracy": md.get("test_direction_accuracy"),
            "jump_regime_code": md.get("jump_regime_code"),
            "jump_signal": md.get("jump_signal"),
            "branch_name": md.get("branch_name"),
            "effective_base": md.get("effective_base"),
        })
    return flat


def rolling_backtest_gbm(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    lookback: int = 240,
    max_horizon: int = 5,
    stride: int = 10,
    cot_daily: pd.DataFrame = None,
) -> pd.DataFrame:
    """Thin passthrough to rolling_backtest_direct."""
    from models.multi_day_direct_predictor import rolling_backtest_direct
    return rolling_backtest_direct(
        daily_df=daily_df,
        comex_daily=comex_daily,
        usdcny_daily=usdcny_daily,
        cross_market=cross_market,
        lookback=lookback,
        max_horizon=max_horizon,
        stride=stride,
        cot_daily=cot_daily,
    )
