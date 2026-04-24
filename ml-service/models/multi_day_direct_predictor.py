"""
Direct multi-horizon daily predictor for gold close extrapolation.

This module preserves the existing Multi-Bar path and adds a separate
non-recursive predictor for T+1...T+N daily close forecasting.

Recent upgrades:
- stronger emphasis on the latest 5-10 trading days for near horizons
- extra high-volatility day features from OHLC history
- event overlays remain outside this module and should be interpreted as
  explanation layers, not core accuracy drivers
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

from models.multi_bar_features import (
    FEATURE_COLUMNS_COT,
    FEATURE_COLUMNS_CROSS,
    FEATURE_COLUMNS_DAILY,
    build_cot_features,
    build_cross_market_features,
    build_daily_features,
)
from models.volatility_regime import (
    classify_regime,
    compute_regime_info,
    dampen_prediction,
    realized_volatility,
)


REGIME_TO_CODE = {
    "low": 0.0,
    "normal": 1.0,
    "high": 2.0,
    "extreme": 3.0,
}

DIRECT_META_COLUMNS = [
    "horizon_days",
    "day_of_week",
    "month",
    "regime_code",
    "jump_regime_code",
    "jump_signal",
    "trend_regime_code",
    "trend_signal",
]

DIRECT_FEATURE_COLUMNS = (
    FEATURE_COLUMNS_DAILY
    + FEATURE_COLUMNS_CROSS
    + FEATURE_COLUMNS_COT
    + DIRECT_META_COLUMNS
)


def _safe_quantile(values: pd.Series, q: float, fallback: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float(fallback)
    return float(max(clean.quantile(q), fallback))


def _build_gbm_pair() -> Tuple[GradientBoostingRegressor, GradientBoostingClassifier]:
    reg = GradientBoostingRegressor(
        n_estimators=220,
        learning_rate=0.03,
        max_depth=3,
        min_samples_leaf=8,
        subsample=0.85,
        random_state=42,
    )
    cls = GradientBoostingClassifier(
        n_estimators=160,
        learning_rate=0.04,
        max_depth=2,
        subsample=0.85,
        random_state=42,
    )
    return reg, cls


def _fit_branch_pair(
    x_train: pd.DataFrame,
    y_ret_train: pd.Series,
    y_dir_train: pd.Series,
    weights: pd.Series,
) -> Tuple[GradientBoostingRegressor, Optional[GradientBoostingClassifier]]:
    reg, cls = _build_gbm_pair()
    reg.fit(x_train, y_ret_train, sample_weight=weights.values)

    if y_dir_train.nunique() > 1:
        cls.fit(x_train, y_dir_train, sample_weight=weights.values)
    else:
        cls = None
    return reg, cls


def _compute_jump_signal(
    overnight_gap_pct: float,
    intraday_range_pct: float,
    comex_shfe_premium: float,
    vol_5: float,
    gap_threshold: float,
    gap_extreme_threshold: float,
    range_threshold: float,
    range_extreme_threshold: float,
    premium_threshold: float,
) -> Tuple[float, float]:
    """Detect jump-like conditions from recent bar structure and cross-market dislocation."""
    base_vol = max(abs(float(vol_5 or 0.0)), 0.005)
    gap_floor = max(0.004, base_vol * 0.90)
    range_floor = max(0.010, base_vol * 1.80)
    premium_floor = max(0.006, base_vol * 0.80)

    gap_norm = max(gap_threshold, gap_floor)
    range_norm = max(range_threshold, range_floor)
    premium_norm = max(premium_threshold, premium_floor)

    gap_score = abs(float(overnight_gap_pct or 0.0)) / gap_norm
    range_score = abs(float(intraday_range_pct or 0.0)) / range_norm
    premium_score = abs(float(comex_shfe_premium or 0.0)) / premium_norm

    if abs(float(overnight_gap_pct or 0.0)) >= max(gap_extreme_threshold, gap_norm * 1.18):
        gap_score += 0.30
    if abs(float(intraday_range_pct or 0.0)) >= max(range_extreme_threshold, range_norm * 1.20):
        range_score += 0.30

    jump_signal = min(
        3.0,
        0.45 * min(gap_score, 3.0)
        + 0.40 * min(range_score, 3.0)
        + 0.15 * min(premium_score, 3.0),
    )
    if jump_signal >= 1.55:
        jump_regime_code = 2.0
    elif jump_signal >= 0.95:
        jump_regime_code = 1.0
    else:
        jump_regime_code = 0.0
    return float(jump_regime_code), float(jump_signal)


def _recent_jump_thresholds(daily_history: pd.Series | pd.DataFrame, vol_5: float) -> Dict[str, float]:
    if isinstance(daily_history, pd.DataFrame):
        history_df = daily_history.copy()
    else:
        close_series = pd.to_numeric(daily_history, errors="coerce").astype(float)
        history_df = pd.DataFrame({"close": close_series})

    base_vol = max(abs(float(vol_5 or 0.0)), 0.005)
    fallback_gap = max(0.005, base_vol * 1.00)
    fallback_gap_extreme = max(0.008, base_vol * 1.45)
    fallback_range = max(0.012, base_vol * 2.00)
    fallback_range_extreme = max(0.018, base_vol * 2.90)
    fallback_premium = max(0.007, base_vol * 0.90)

    if history_df.empty or "close" not in history_df.columns:
        return {
            "gap_threshold": fallback_gap,
            "gap_extreme_threshold": fallback_gap_extreme,
            "range_threshold": fallback_range,
            "range_extreme_threshold": fallback_range_extreme,
            "premium_threshold": fallback_premium,
        }

    close_hist = pd.to_numeric(history_df.get("close"), errors="coerce").astype(float)
    ret_1 = close_hist.pct_change().abs()
    if {"open", "high", "low", "close"}.issubset(history_df.columns):
        open_hist = pd.to_numeric(history_df.get("open"), errors="coerce").astype(float)
        high_hist = pd.to_numeric(history_df.get("high"), errors="coerce").astype(float)
        low_hist = pd.to_numeric(history_df.get("low"), errors="coerce").astype(float)
        prev_close = close_hist.shift(1)
        gap_hist = ((open_hist - prev_close) / prev_close.replace(0, np.nan)).abs()
        range_hist = ((high_hist - low_hist) / close_hist.replace(0, np.nan)).abs()
    else:
        gap_hist = ret_1
        range_hist = ret_1.rolling(2).max()

    recent_slice = slice(-16, None)
    gap_recent = gap_hist.iloc[recent_slice]
    range_recent = range_hist.iloc[recent_slice]
    premium_proxy = ret_1.iloc[recent_slice] * 0.7

    return {
        "gap_threshold": _safe_quantile(gap_recent, 0.70, fallback_gap),
        "gap_extreme_threshold": _safe_quantile(gap_recent, 0.88, fallback_gap_extreme),
        "range_threshold": _safe_quantile(range_recent, 0.70, fallback_range),
        "range_extreme_threshold": _safe_quantile(range_recent, 0.88, fallback_range_extreme),
        "premium_threshold": _safe_quantile(premium_proxy, 0.72, fallback_premium),
    }


def _compute_trend_reversal_signal(
    daily_history: pd.Series | pd.DataFrame,
    daily_features: Dict[str, float],
) -> Tuple[float, float]:
    if isinstance(daily_history, pd.DataFrame):
        close_hist = pd.to_numeric(daily_history.get("close"), errors="coerce").astype(float)
    else:
        close_hist = pd.to_numeric(daily_history, errors="coerce").astype(float)

    close_hist = close_hist.dropna()
    if len(close_hist) < 8:
        return 0.0, 0.0

    ret_hist = close_hist.pct_change().dropna()
    down_streak = 0
    for value in reversed(ret_hist.tail(4).tolist()):
        if value < 0:
            down_streak += 1
        else:
            break

    up_streak = 0
    for value in reversed(ret_hist.tail(4).tolist()):
        if value > 0:
            up_streak += 1
        else:
            break

    ma_gap_5 = float(daily_features.get("ma_gap_5", 0.0))
    ma_gap_10 = float(daily_features.get("ma_gap_10", 0.0))
    ret_3 = float(daily_features.get("ret_3", 0.0))
    ret_5 = float(daily_features.get("ret_5", 0.0))
    close_vs_vwap = float(daily_features.get("close_vs_vwap", 0.0))
    close_vs_high = float(daily_features.get("close_vs_high", 0.0))

    slope_input = close_hist.tail(5).values.astype(float)
    if len(slope_input) >= 3 and slope_input[-1] != 0:
        x_axis = np.arange(len(slope_input), dtype=float)
        slope = float(np.polyfit(x_axis, slope_input, 1)[0] / slope_input[-1])
    else:
        slope = 0.0

    bearish_score = (
        1.6 * max(0.0, -ret_3)
        + 1.2 * max(0.0, -ret_5)
        + 1.3 * max(0.0, -ma_gap_5)
        + 1.0 * max(0.0, -ma_gap_10)
        + 0.8 * max(0.0, -close_vs_vwap)
        + 0.5 * max(0.0, -close_vs_high)
        + 4.0 * max(0.0, -slope)
        + 0.18 * down_streak
    )
    bullish_score = (
        1.6 * max(0.0, ret_3)
        + 1.2 * max(0.0, ret_5)
        + 1.3 * max(0.0, ma_gap_5)
        + 1.0 * max(0.0, ma_gap_10)
        + 0.8 * max(0.0, close_vs_vwap)
        + 0.5 * max(0.0, close_vs_high)
        + 4.0 * max(0.0, slope)
        + 0.18 * up_streak
    )

    if bearish_score >= 0.20 and bearish_score > bullish_score * 1.08:
        return -1.0, float(min(3.0, bearish_score))
    if bullish_score >= 0.20 and bullish_score > bearish_score * 1.08:
        return 1.0, float(min(3.0, bullish_score))
    return 0.0, float(max(bearish_score, bullish_score))


def _build_direct_feature_row(
    daily_history: pd.Series | pd.DataFrame,
    current_close: float,
    current_date: pd.Timestamp,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    horizon_days: int,
    cot_daily: Optional[pd.DataFrame] = None,
) -> Dict[str, float]:
    daily = build_daily_features(daily_history)
    if isinstance(daily_history, pd.DataFrame):
        daily_closes = pd.to_numeric(daily_history["close"], errors="coerce").astype(float)
    else:
        daily_closes = pd.to_numeric(daily_history, errors="coerce").astype(float)
    cross = build_cross_market_features(
        comex_daily=comex_daily,
        usdcny_daily=usdcny_daily,
        cross_market=cross_market,
        shfe_close=current_close,
        target_date=current_date,
    )
    ann_vol = realized_volatility(daily_closes.astype(float), window=20)
    regime = classify_regime(ann_vol)
    jump_thresholds = _recent_jump_thresholds(daily_history, float(daily.get("vol_5", 0.0)))
    jump_regime_code, jump_signal = _compute_jump_signal(
        overnight_gap_pct=float(daily.get("overnight_gap_pct", 0.0)),
        intraday_range_pct=float(daily.get("intraday_range_pct", 0.0)),
        comex_shfe_premium=float(cross.get("comex_shfe_premium", 0.0)),
        vol_5=float(daily.get("vol_5", 0.0)),
        gap_threshold=jump_thresholds["gap_threshold"],
        gap_extreme_threshold=jump_thresholds["gap_extreme_threshold"],
        range_threshold=jump_thresholds["range_threshold"],
        range_extreme_threshold=jump_thresholds["range_extreme_threshold"],
        premium_threshold=jump_thresholds["premium_threshold"],
    )
    trend_regime_code, trend_signal = _compute_trend_reversal_signal(daily_history, daily)
    meta = {
        "horizon_days": float(horizon_days),
        "day_of_week": float(current_date.dayofweek),
        "month": float(current_date.month),
        "regime_code": REGIME_TO_CODE.get(regime, 1.0),
        "jump_regime_code": jump_regime_code,
        "jump_signal": jump_signal,
        "trend_regime_code": trend_regime_code,
        "trend_signal": trend_signal,
    }

    cot = build_cot_features(cot_daily, current_date)

    row: Dict[str, float] = {}
    row.update(daily)
    row.update(cross)
    row.update(cot)
    row.update(meta)
    return row


def _build_recency_weights(sample_dates: pd.Series, horizon_days: int) -> pd.Series:
    if sample_dates.empty:
        return pd.Series(dtype=float)

    dates = pd.to_datetime(sample_dates).reset_index(drop=True)
    max_date = dates.iloc[-1]
    age_days = (max_date - dates).dt.days.clip(lower=0)

    half_life = 7 if horizon_days <= 2 else 12
    decay_component = np.exp(-age_days / max(half_life, 1))
    weights = 0.8 + 0.35 * decay_component

    tail_window = min(len(dates), 10 if horizon_days <= 2 else 5)
    if tail_window > 0:
        tail_boost = 0.55 if horizon_days <= 2 else 0.20
        weights.iloc[-tail_window:] *= np.linspace(1.0, 1.0 + tail_boost, tail_window)

    return weights.astype(float)


def _build_training_dataset(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    horizon_days: int,
    lookback_days: int = 240,
    cot_daily: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series, pd.Series]:
    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    usable_end = len(daily_sorted) - horizon_days
    if usable_end <= 20:
        empty_x = pd.DataFrame(columns=DIRECT_FEATURE_COLUMNS)
        empty_dates = pd.Series(dtype="datetime64[ns]")
        return empty_x, pd.Series(dtype=float), pd.Series(dtype=int), pd.Series(dtype=float), empty_dates

    start_idx = max(20, usable_end - lookback_days)

    rows: List[Dict[str, float]] = []
    y_return: List[float] = []
    y_direction: List[int] = []
    bases: List[float] = []
    sample_dates: List[pd.Timestamp] = []

    for idx in range(start_idx, usable_end):
        current_date = pd.Timestamp(daily_sorted.iloc[idx]["date"])
        current_close = float(daily_sorted.iloc[idx]["close"])
        target_close = float(daily_sorted.iloc[idx + horizon_days]["close"])
        if current_close <= 0 or target_close <= 0:
            continue

        daily_history = daily_sorted.iloc[max(0, idx - 20): idx + 1].copy()
        feature_row = _build_direct_feature_row(
            daily_history=daily_history,
            current_close=current_close,
            current_date=current_date,
            comex_daily=comex_daily,
            usdcny_daily=usdcny_daily,
            cross_market=cross_market,
            horizon_days=horizon_days,
            cot_daily=cot_daily,
        )
        rows.append(feature_row)
        ret = target_close / current_close - 1
        y_return.append(float(ret))
        y_direction.append(1 if ret > 0 else 0)
        bases.append(current_close)
        sample_dates.append(current_date)

    if not rows:
        empty_x = pd.DataFrame(columns=DIRECT_FEATURE_COLUMNS)
        empty_dates = pd.Series(dtype="datetime64[ns]")
        return empty_x, pd.Series(dtype=float), pd.Series(dtype=int), pd.Series(dtype=float), empty_dates

    x = pd.DataFrame(rows)
    for col in DIRECT_FEATURE_COLUMNS:
        if col not in x.columns:
            x[col] = 0.0
    x = x[DIRECT_FEATURE_COLUMNS]
    return (
        x,
        pd.Series(y_return, dtype=float),
        pd.Series(y_direction, dtype=int),
        pd.Series(bases, dtype=float),
        pd.Series(sample_dates, dtype="datetime64[ns]"),
    )


def _evaluate(
    reg: GradientBoostingRegressor,
    cls: Optional[GradientBoostingClassifier],
    x_test: pd.DataFrame,
    y_test: pd.Series,
    y_dir_test: pd.Series,
    base_test: pd.Series,
) -> Dict[str, Any]:
    if len(x_test) == 0:
        return {
            "mae": None,
            "rmse": None,
            "mape_pct": None,
            "direction_accuracy": None,
        }

    pred_ret = reg.predict(x_test)
    pred_close = base_test.values * (1 + pred_ret)
    actual_close = base_test.values * (1 + y_test.values)
    error = pred_close - actual_close
    abs_pct = np.abs(error) / np.maximum(np.abs(actual_close), 1e-8) * 100
    pred_dir = (pred_ret > 0).astype(int)

    cls_dir_acc = None
    if cls is not None:
        cls_pred = cls.predict(x_test)
        cls_dir_acc = float(np.mean(cls_pred == y_dir_test.values) * 100)

    return {
        "mae": round(float(np.abs(error).mean()), 4),
        "rmse": round(float(np.sqrt(np.mean(np.square(error)))), 4),
        "mape_pct": round(float(np.nanmean(abs_pct)), 4),
        "direction_accuracy": round(float(np.mean(pred_dir == y_dir_test.values) * 100), 2),
        "cls_direction_accuracy": round(cls_dir_acc, 2) if cls_dir_acc is not None else None,
    }


def _clip_return(
    pred_return: float,
    vol_5: float,
    horizon_days: int,
    jump_regime_code: float = 0.0,
    jump_signal: float = 0.0,
) -> float:
    base_vol = max(float(vol_5 or 0.0), 0.005) * np.sqrt(max(horizon_days, 1))
    jump_multiplier = 1.0 + 0.22 * float(jump_regime_code) + 0.10 * min(float(jump_signal), 2.0)
    cap = max(0.015, min(0.12, 2.2 * base_vol * jump_multiplier))
    return float(np.clip(pred_return, -cap, cap))


def _compute_asymmetric_range_multipliers(
    pred_return: float,
    overnight_gap_pct: float,
    jump_regime_code: float,
    jump_signal: float,
    branch_name: str | None = None,
) -> Tuple[float, float]:
    upper_mult = 1.0
    lower_mult = 1.0
    if jump_regime_code <= 0:
        return upper_mult, lower_mult

    asym_scale = 0.18 * float(jump_regime_code) + 0.08 * min(float(jump_signal), 2.0)
    if branch_name == "jump_up":
        directional_hint = 1.0
    elif branch_name == "jump_down":
        directional_hint = -1.0
    else:
        directional_hint = float(np.sign(pred_return))
        if directional_hint == 0.0:
            directional_hint = float(np.sign(overnight_gap_pct))

    if directional_hint >= 0:
        upper_mult += asym_scale * 1.20
        lower_mult += asym_scale * 0.45
    else:
        lower_mult += asym_scale * 1.20
        upper_mult += asym_scale * 0.45
    return float(upper_mult), float(lower_mult)


def _directional_jump_branch_name(
    jump_regime_code: float,
    overnight_gap_pct: float,
    ret_1: float,
) -> str:
    if jump_regime_code < 1.0:
        return "normal"
    directional_score = float(overnight_gap_pct) + 0.5 * float(ret_1)
    return "jump_up" if directional_score >= 0 else "jump_down"


def _trend_branch_name(trend_regime_code: float) -> str:
    if trend_regime_code <= -1.0:
        return "trend_down"
    if trend_regime_code >= 1.0:
        return "trend_up"
    return "normal"


def _train_horizon_model(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    horizon_days: int,
    lookback_days: int,
    cot_daily: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    x, y_ret, y_dir, bases, sample_dates = _build_training_dataset(
        daily_df=daily_df,
        comex_daily=comex_daily,
        usdcny_daily=usdcny_daily,
        cross_market=cross_market,
        horizon_days=horizon_days,
        lookback_days=lookback_days,
        cot_daily=cot_daily,
    )
    if len(x) < 50:
        return {"trained": False, "reason": f"insufficient data ({len(x)} < 50)"}

    split = int(len(x) * 0.8)
    x_train, x_test = x.iloc[:split], x.iloc[split:]
    y_ret_train, y_ret_test = y_ret.iloc[:split], y_ret.iloc[split:]
    y_dir_train, y_dir_test = y_dir.iloc[:split], y_dir.iloc[split:]
    base_test = bases.iloc[split:]
    train_dates = sample_dates.iloc[:split]
    train_weights = _build_recency_weights(train_dates, horizon_days)

    reg, cls = _fit_branch_pair(x_train, y_ret_train, y_dir_train, train_weights)

    metrics = _evaluate(reg, cls, x_test, y_ret_test, y_dir_test, base_test)
    metrics["train_size"] = len(x_train)
    metrics["test_size"] = len(x_test)
    metrics["train_weight_mean"] = round(float(train_weights.mean()), 4)
    metrics["recent_weight_mean"] = round(float(train_weights.tail(min(len(train_weights), 10)).mean()), 4)

    tail_size = min(len(x_train), 10 if horizon_days <= 2 else 6)
    recent_bias_return = 0.0
    if tail_size > 0:
        tail_pred = reg.predict(x_train.tail(tail_size))
        tail_actual = y_ret_train.tail(tail_size).values
        recent_bias_return = float(np.mean(tail_actual - tail_pred))
        bias_cap = 0.012 if horizon_days <= 2 else 0.008
        recent_bias_return = float(np.clip(recent_bias_return, -bias_cap, bias_cap))
    metrics["recent_bias_return_pct"] = round(recent_bias_return * 100, 3)

    drift_bias_by_regime: Dict[str, float] = {}
    drift_tail = min(len(x_train), 14 if horizon_days <= 2 else 8)
    if drift_tail > 0:
        drift_x = x_train.tail(drift_tail)
        drift_pred = reg.predict(drift_x)
        drift_actual = y_ret_train.tail(drift_tail).values
        drift_resid = drift_actual - drift_pred
        trend_tail = drift_x["trend_regime_code"]
        drift_masks = {
            "trend_down": trend_tail <= -1.0,
            "trend_up": trend_tail >= 1.0,
            "normal": trend_tail.abs() < 1.0,
        }
        drift_cap = 0.014 if horizon_days <= 2 else 0.010
        for regime_name, regime_mask in drift_masks.items():
            if int(regime_mask.sum()) == 0:
                continue
            regime_bias = float(np.mean(drift_resid[regime_mask.values]))
            drift_bias_by_regime[regime_name] = float(np.clip(regime_bias, -drift_cap, drift_cap))

    branch_models: Dict[str, Any] = {}
    branch_blend_weights: Dict[str, float] = {}
    if horizon_days <= 2:
        jump_mask = x_train["jump_regime_code"] >= 1.0
        trend_down_mask = x_train["trend_regime_code"] <= -1.0
        trend_up_mask = x_train["trend_regime_code"] >= 1.0
        directional_score = x_train["overnight_gap_pct"] + 0.5 * x_train["ret_1"]
        jump_up_mask = jump_mask & (directional_score >= 0)
        jump_down_mask = jump_mask & (directional_score < 0)
        branch_specs = {
            "jump_up": jump_up_mask,
            "jump_down": jump_down_mask,
            "jump": jump_mask,
            "trend_down": trend_down_mask & ~jump_mask,
            "trend_up": trend_up_mask & ~jump_mask,
            "normal": ~jump_mask,
        }
        for branch_name, mask in branch_specs.items():
            branch_x = x_train.loc[mask]
            if branch_name in {"jump_up", "jump_down"}:
                min_samples = 8
            elif branch_name == "jump":
                min_samples = 12
            elif branch_name in {"trend_down", "trend_up"}:
                min_samples = 10
            else:
                min_samples = 16
            if len(branch_x) < min_samples:
                continue
            branch_y_ret = y_ret_train.loc[mask]
            branch_y_dir = y_dir_train.loc[mask]
            branch_weights = train_weights.loc[mask]
            branch_reg, branch_cls = _fit_branch_pair(branch_x, branch_y_ret, branch_y_dir, branch_weights)

            branch_tail = min(len(branch_x), 8)
            branch_bias = 0.0
            if branch_tail > 0:
                tail_pred = branch_reg.predict(branch_x.tail(branch_tail))
                tail_actual = branch_y_ret.tail(branch_tail).values
                branch_bias = float(np.mean(tail_actual - tail_pred))
                branch_bias = float(np.clip(branch_bias, -0.014, 0.014))

            branch_models[branch_name] = {
                "reg_model": branch_reg,
                "cls_model": branch_cls,
                "sample_count": int(len(branch_x)),
                "recent_bias_return": branch_bias,
            }
        if "jump_up" in branch_models:
            branch_blend_weights["jump_up"] = 0.78
        if "jump_down" in branch_models:
            branch_blend_weights["jump_down"] = 0.78
        if "jump" in branch_models:
            branch_blend_weights["jump"] = 0.65
        if "trend_down" in branch_models:
            branch_blend_weights["trend_down"] = 0.72
        if "trend_up" in branch_models:
            branch_blend_weights["trend_up"] = 0.68
        if "normal" in branch_models:
            branch_blend_weights["normal"] = 0.55

    return {
        "trained": True,
        "reg_model": reg,
        "cls_model": cls,
        "metrics": metrics,
        "recent_bias_return": recent_bias_return,
        "drift_bias_by_regime": drift_bias_by_regime,
        "branch_models": branch_models,
        "branch_blend_weights": branch_blend_weights,
    }


def run_direct_multi_day_prediction(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    target_dates: Sequence[pd.Timestamp],
    lookback_days: int = 240,
    verbose: bool = True,
    cot_daily: Optional[pd.DataFrame] = None,
) -> List[Dict[str, Any]]:
    if not target_dates:
        return []

    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    current_close = float(daily_sorted.iloc[-1]["close"])
    current_date = pd.Timestamp(daily_sorted.iloc[-1]["date"])
    regime_info = compute_regime_info(daily_sorted["close"].astype(float))
    regime = regime_info["regime"]

    if verbose:
        print(
            f"  [Regime] {regime} (vol={regime_info['annualized_vol']}%, dampening={regime_info['dampening']})"
        )

    models: Dict[int, Dict[str, Any]] = {}
    for horizon_days in range(1, len(target_dates) + 1):
        if verbose:
            print(f"  [Train] T+{horizon_days} direct model ...", end=" ")
        model_info = _train_horizon_model(
            daily_df=daily_sorted,
            comex_daily=comex_daily,
            usdcny_daily=usdcny_daily,
            cross_market=cross_market,
            horizon_days=horizon_days,
            lookback_days=lookback_days,
            cot_daily=cot_daily,
        )
        models[horizon_days] = model_info
        if verbose:
            if model_info["trained"]:
                m = model_info["metrics"]
                print(
                    f"OK (n={m['train_size']}+{m['test_size']}, "
                    f"dir={m['direction_accuracy']}%, mape={m['mape_pct']}%)"
                )
            else:
                print(f"SKIP ({model_info.get('reason', 'unknown')})")

    history_window = daily_sorted.iloc[max(0, len(daily_sorted) - 21):].copy()
    predictions: List[Dict[str, Any]] = []
    for horizon_days, target_date in enumerate(target_dates, start=1):
        model_info = models.get(horizon_days, {})
        if not model_info.get("trained", False):
            continue

        feature_row = _build_direct_feature_row(
            daily_history=history_window,
            current_close=current_close,
            current_date=current_date,
            comex_daily=comex_daily,
            usdcny_daily=usdcny_daily,
            cross_market=cross_market,
            horizon_days=horizon_days,
            cot_daily=cot_daily,
        )
        x_row = pd.DataFrame([[feature_row[col] for col in DIRECT_FEATURE_COLUMNS]], columns=DIRECT_FEATURE_COLUMNS)
        vol_5 = float(feature_row.get("vol_5", 0.0))
        jump_regime_code = float(feature_row.get("jump_regime_code", 0.0))
        jump_signal = float(feature_row.get("jump_signal", 0.0))
        trend_regime_code = float(feature_row.get("trend_regime_code", 0.0))
        trend_signal = float(feature_row.get("trend_signal", 0.0))
        overnight_gap_pct = float(feature_row.get("overnight_gap_pct", 0.0))
        ret_1 = float(feature_row.get("ret_1", 0.0))

        pred_return = float(model_info["reg_model"].predict(x_row)[0])
        preferred_branch = _directional_jump_branch_name(jump_regime_code, overnight_gap_pct, ret_1)
        branch_models = model_info.get("branch_models", {})
        branch_blend_weights = model_info.get("branch_blend_weights", {})
        branch_name = None
        branch_info = None
        if preferred_branch in {"jump_up", "jump_down"}:
            if preferred_branch in branch_models:
                branch_name = preferred_branch
                branch_info = branch_models[branch_name]
            elif "jump" in branch_models:
                branch_name = "jump"
                branch_info = branch_models[branch_name]
        elif abs(trend_regime_code) >= 1.0:
            trend_branch = _trend_branch_name(trend_regime_code)
            if trend_branch in branch_models:
                branch_name = trend_branch
                branch_info = branch_models[branch_name]
        elif "normal" in branch_models:
            branch_name = "normal"
            branch_info = branch_models[branch_name]

        branch_blend_weight = float(branch_blend_weights.get(branch_name, 0.0)) if branch_name else 0.0
        branch_used = False
        if branch_info is not None and branch_blend_weight > 0.0:
            branch_pred = float(branch_info["reg_model"].predict(x_row)[0])
            pred_return = (1.0 - branch_blend_weight) * pred_return + branch_blend_weight * branch_pred
            branch_used = True

        bias_adjustment = float(model_info.get("recent_bias_return", 0.0))
        if horizon_days >= 3:
            bias_adjustment *= 0.65
        drift_bias_by_regime = model_info.get("drift_bias_by_regime", {})
        if abs(trend_regime_code) >= 1.0:
            drift_key = _trend_branch_name(trend_regime_code)
        else:
            drift_key = "normal"
        bias_adjustment += 0.70 * float(drift_bias_by_regime.get(drift_key, 0.0))
        if branch_info is not None:
            branch_bias = float(branch_info.get("recent_bias_return", 0.0))
            bias_adjustment = 0.55 * bias_adjustment + 0.45 * branch_bias
        pred_return += bias_adjustment
        pred_return = _clip_return(
            pred_return,
            vol_5,
            horizon_days,
            jump_regime_code=jump_regime_code,
            jump_signal=jump_signal,
        )
        pred_close_raw = current_close * (1 + pred_return)
        pred_close = float(dampen_prediction(pred_close_raw, current_close, regime))

        up_prob = None
        cls_model = model_info.get("cls_model")
        if branch_info is not None and branch_info.get("cls_model") is not None and branch_used:
            cls_model = branch_info.get("cls_model")
        if cls_model is not None:
            probs = cls_model.predict_proba(x_row)[0]
            up_prob = float(probs[1]) if len(probs) > 1 else None

        metrics = model_info.get("metrics", {})
        prob_conf = abs(up_prob - 0.5) * 2 if up_prob is not None else 0.0
        dir_acc = float(metrics.get("direction_accuracy") or 50.0) / 100.0
        horizon_decay = max(0.45, 1.0 - 0.10 * (horizon_days - 1))
        confidence = (0.55 * prob_conf + 0.45 * dir_acc) * 100 * horizon_decay

        range_pct = max(float(metrics.get("mape_pct") or 1.0) / 100.0, 0.005)
        range_pct *= min(1.6, 1.0 + 0.12 * (horizon_days - 1))
        if jump_regime_code > 0:
            range_pct *= 1.0 + 0.18 * jump_regime_code + 0.08 * min(jump_signal, 2.0)
        upper_mult, lower_mult = _compute_asymmetric_range_multipliers(
            pred_return=pred_return,
            overnight_gap_pct=overnight_gap_pct,
            jump_regime_code=jump_regime_code,
            jump_signal=jump_signal,
            branch_name=branch_name if branch_used else None,
        )
        range_low = pred_close * (1 - range_pct * lower_mult)
        range_high = pred_close * (1 + range_pct * upper_mult)

        delta = pred_close - current_close
        direction = "涨" if delta > 0.5 else ("跌" if delta < -0.5 else "平")
        predictions.append(
            {
                "date": pd.Timestamp(target_date).strftime("%Y-%m-%d"),
                "close": round(pred_close, 2),
                "direction": direction,
                "confidence": round(float(np.clip(confidence, 0.0, 95.0)), 1),
                "range_low": round(range_low, 2),
                "range_high": round(range_high, 2),
                "regime": regime,
                "n_models": 1,
                "model_details": {
                    "model_name": "direct_gbm_multi_horizon_v2",
                    "horizon_days": horizon_days,
                    "pred_return_pct": round(pred_return * 100, 3),
                    "up_probability": round(up_prob, 4) if up_prob is not None else None,
                    "test_mape_pct": metrics.get("mape_pct"),
                    "test_direction_accuracy": metrics.get("direction_accuracy"),
                    "recent_weight_mean": metrics.get("recent_weight_mean"),
                    "recent_bias_return_pct": metrics.get("recent_bias_return_pct"),
                    "jump_regime_code": jump_regime_code,
                    "jump_signal": round(jump_signal, 3),
                    "trend_regime_code": trend_regime_code,
                    "trend_signal": round(trend_signal, 3),
                    "branch_used": branch_used,
                    "branch_name": branch_name if branch_used else None,
                    "effective_base": round(current_close, 2),
                },
            }
        )

    return predictions


def rolling_backtest_direct(
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    lookback: int = 240,
    max_horizon: int = 5,
    stride: int = 10,
    cot_daily: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    start_idx = max(lookback, 80)
    end_idx = len(daily_sorted) - max_horizon
    origins = list(range(start_idx, end_idx, max(stride, 1)))
    total = len(origins)
    records: List[Dict[str, Any]] = []

    for done, oi in enumerate(origins):
        history_daily = daily_sorted.iloc[: oi + 1].copy()
        origin_close = float(history_daily.iloc[-1]["close"])
        origin_date = pd.Timestamp(history_daily.iloc[-1]["date"])
        future_dates = []
        for h in range(1, max_horizon + 1):
            ti = oi + h
            if ti < len(daily_sorted):
                future_dates.append(pd.Timestamp(daily_sorted.iloc[ti]["date"]))

        if not future_dates:
            continue

        try:
            cot_truncated = None
            if cot_daily is not None and not cot_daily.empty and "date" in cot_daily.columns:
                cot_truncated = cot_daily[cot_daily["date"] <= origin_date]
            preds = run_direct_multi_day_prediction(
                daily_df=history_daily,
                comex_daily=comex_daily[comex_daily["date"] <= origin_date],
                usdcny_daily=usdcny_daily[usdcny_daily["date"] <= origin_date],
                cross_market=cross_market[cross_market["date"] <= origin_date],
                target_dates=future_dates,
                lookback_days=lookback,
                verbose=False,
                cot_daily=cot_truncated,
            )
        except Exception:
            continue

        for h_idx, pred in enumerate(preds):
            ti = oi + h_idx + 1
            if ti >= len(daily_sorted):
                break
            records.append(
                {
                    "horizon": h_idx + 1,
                    "origin_close": origin_close,
                    "pred_close": pred["close"],
                    "actual_close": float(daily_sorted.iloc[ti]["close"]),
                    "regime": pred.get("regime", "unknown"),
                    "confidence": pred.get("confidence", 0),
                }
            )

        if (done + 1) % 10 == 0:
            print(f"    回测进度: {done + 1}/{total}")

    print(f"    回测完成: {len(records)} 条记录")
    return pd.DataFrame(records)
