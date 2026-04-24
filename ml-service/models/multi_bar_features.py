"""
Multi-bar feature engineering for gold price prediction.

Aggregates SHFE AU 60min K-line data into checkpoint bars,
then builds rich feature vectors for each checkpoint.
"""

from __future__ import annotations

from datetime import time as dt_time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Checkpoint definitions
# ---------------------------------------------------------------------------

CHECKPOINTS = ["04:00", "09:00", "12:00", "16:00", "20:00", "24:00"]

# Each checkpoint defines which 60min bars to aggregate.
# Ranges are (start_hour, end_hour) — bars whose *close time* falls within.
# For night session bars that cross midnight, we use two ranges.
CHECKPOINT_BAR_RANGES: Dict[str, List[Tuple[int, int]]] = {
    "04:00": [(0, 3)],                 # late-night tail (00:00-02:30)
    "09:00": [(21, 24), (0, 3)],       # full night session
    "12:00": [(9, 12)],                # morning day session
    "16:00": [(9, 16)],               # full day session
    "20:00": [(9, 16)],               # same as 16:00 (post-close perspective)
    "24:00": [(21, 24)],              # first half of night session
}

CHECKPOINT_TARGET_OFFSET: Dict[str, str] = {
    "04:00": "same_day",    # predicts today's 16:00
    "09:00": "same_day",
    "12:00": "same_day",
    "16:00": "next_day",    # predicts tomorrow's 16:00
    "20:00": "next_day",
    "24:00": "next_day",    # predicts tomorrow's 16:00
}

FEATURE_COLUMNS_INTRADAY = [
    "session_return",
    "session_range",
    "session_volume_ratio",
    "gap_from_prev_close",
    "high_low_position",
    "vwap_deviation",
    "bar_count",
    "momentum_3bar",
    "last_bar_return",
]

FEATURE_COLUMNS_DAILY = [
    "lag_1", "lag_2", "lag_3", "lag_5",
    "ret_1", "ret_3", "ret_5",
    "ma_5", "ma_10", "ma_20",
    "ma_gap_5", "ma_gap_10", "ma_gap_20",
    "vol_5",
    "close_vs_high",
    "close_vs_vwap",
    "intraday_range_pct",
    "overnight_gap_pct",
]

FEATURE_COLUMNS_CROSS = [
    "comex_overnight_return",
    "comex_shfe_premium",
    "dxy_5d_change",
    "vix_level",
    "vix_regime",
    "us10y_5d_change",
    "usdcny_direction",
]

FEATURE_COLUMNS_META = [
    "hours_to_target",
    "day_of_week",
]

# CFTC Commitments of Traders (gold futures) features
# Source: ml-service/data_collector/cot_fetcher.py (Disaggregated Fut-Only)
FEATURE_COLUMNS_COT = [
    "cot_mm_net_pct_oi",       # Managed Money net / OI (primary speculator signal)
    "cot_mm_net_change_1w",    # 1-week change of mm_net / OI
    "cot_mm_net_change_4w",    # 4-week change (trend)
    "cot_mm_net_zscore_52w",   # 52-week z-score (extreme positioning)
    "cot_mm_long_pct_oi",
    "cot_mm_short_pct_oi",
    "cot_comm_net_pct_oi",     # Commercial net (reverse signal)
    "cot_oi_change_1w_pct",    # Open Interest 1w change (participation)
]

TROY_OZ_TO_GRAM = 31.1035


def all_feature_columns() -> List[str]:
    return (
        FEATURE_COLUMNS_INTRADAY
        + FEATURE_COLUMNS_DAILY
        + FEATURE_COLUMNS_CROSS
        + FEATURE_COLUMNS_META
    )


# ---------------------------------------------------------------------------
# 60min bar aggregation
# ---------------------------------------------------------------------------

def _filter_bars_for_checkpoint(
    bars_60min: pd.DataFrame,
    checkpoint: str,
    target_date: pd.Timestamp,
) -> pd.DataFrame:
    """Select 60min bars relevant to a checkpoint on target_date."""
    ranges = CHECKPOINT_BAR_RANGES[checkpoint]
    mask = pd.Series(False, index=bars_60min.index)

    for start_h, end_h in ranges:
        if start_h >= 21:
            # Night session bars: belong to prev calendar date's session
            # but their timestamp is on the prev date evening or target_date early morning
            prev_date = target_date - pd.Timedelta(days=1)
            hour_mask = bars_60min["date"].dt.hour.between(start_h, min(end_h, 23))
            date_mask = bars_60min["date"].dt.date == prev_date.date()
            mask |= (hour_mask & date_mask)
        elif start_h < 9:
            # Early morning bars (00:00-02:30): timestamp is target_date
            hour_mask = bars_60min["date"].dt.hour.between(start_h, end_h - 1)
            date_mask = bars_60min["date"].dt.date == target_date.date()
            mask |= (hour_mask & date_mask)
        else:
            # Day session bars
            hour_mask = bars_60min["date"].dt.hour.between(start_h, end_h - 1)
            date_mask = bars_60min["date"].dt.date == target_date.date()
            mask |= (hour_mask & date_mask)

    return bars_60min.loc[mask].sort_values("date")


def aggregate_checkpoint_bar(
    filtered_bars: pd.DataFrame,
    prev_close_16: float,
    avg_session_volume: float,
) -> Dict[str, float]:
    """Aggregate filtered 60min bars into a single checkpoint summary."""
    if filtered_bars.empty:
        return {col: 0.0 for col in FEATURE_COLUMNS_INTRADAY}

    o = float(filtered_bars.iloc[0]["open"])
    h = float(filtered_bars["high"].max())
    lo = float(filtered_bars["low"].min())
    c = float(filtered_bars.iloc[-1]["close"])
    vol = float(filtered_bars["volume"].sum())
    amount = float(filtered_bars["amount"].sum()) if "amount" in filtered_bars.columns else c * vol

    session_return = (c / prev_close_16 - 1) if prev_close_16 > 0 else 0.0
    session_range = (h - lo) / prev_close_16 if prev_close_16 > 0 else 0.0
    gap = (o / prev_close_16 - 1) if prev_close_16 > 0 else 0.0
    hlp = (c - lo) / (h - lo) if (h - lo) > 0.01 else 0.5
    vwap = amount / vol if vol > 0 else c
    vwap_dev = (c / vwap - 1) if vwap > 0 else 0.0
    vol_ratio = vol / avg_session_volume if avg_session_volume > 0 else 1.0

    # momentum: direction consistency of last 3 bars
    if len(filtered_bars) >= 3:
        last3 = filtered_bars.tail(3)
        dirs = np.sign(last3["close"].values - last3["open"].values)
        momentum = float(dirs.sum()) / 3.0
    else:
        momentum = 0.0

    last_bar_ret = float(filtered_bars.iloc[-1]["close"] / filtered_bars.iloc[-1]["open"] - 1) if len(filtered_bars) > 0 else 0.0

    return {
        "session_return": session_return,
        "session_range": session_range,
        "session_volume_ratio": vol_ratio,
        "gap_from_prev_close": gap,
        "high_low_position": hlp,
        "vwap_deviation": vwap_dev,
        "bar_count": float(len(filtered_bars)),
        "momentum_3bar": momentum,
        "last_bar_return": last_bar_ret,
    }


# ---------------------------------------------------------------------------
# Daily history features (same as original predictor)
# ---------------------------------------------------------------------------

def build_daily_features(daily_input: pd.Series | pd.DataFrame) -> Dict[str, float]:
    """Build lag/return/ma features from daily history.

    Accepts either:
    - a close-only series (legacy callers)
    - a daily OHLC dataframe (new callers, richer volatility features)
    """
    if isinstance(daily_input, pd.DataFrame):
        df = daily_input.copy()
        if "close" not in df.columns:
            return {col: 0.0 for col in FEATURE_COLUMNS_DAILY}
        s = pd.to_numeric(df["close"], errors="coerce").astype(float)
    else:
        df = None
        s = pd.to_numeric(daily_input, errors="coerce").astype(float)

    if len(s) < 20:
        return {col: 0.0 for col in FEATURE_COLUMNS_DAILY}

    ret_1 = s.iloc[-1] / s.iloc[-2] - 1 if len(s) >= 2 else 0.0
    ret_3 = s.iloc[-1] / s.iloc[-4] - 1 if len(s) >= 4 else 0.0
    ret_5 = s.iloc[-1] / s.iloc[-6] - 1 if len(s) >= 6 else 0.0

    ma_5 = s.tail(5).mean()
    ma_10 = s.tail(10).mean()
    ma_20 = s.tail(20).mean()

    close_vs_high = 0.0
    close_vs_vwap = 0.0
    intraday_range_pct = 0.0
    overnight_gap_pct = 0.0

    if df is not None:
        latest = df.iloc[-1]
        prev_close = float(s.iloc[-2]) if len(s) >= 2 else float(s.iloc[-1])
        latest_close = float(s.iloc[-1])
        latest_high = float(pd.to_numeric(latest.get("high"), errors="coerce") or np.nan)
        latest_low = float(pd.to_numeric(latest.get("low"), errors="coerce") or np.nan)
        latest_open = float(pd.to_numeric(latest.get("open"), errors="coerce") or np.nan)

        amount_value = pd.to_numeric(latest.get("amount"), errors="coerce")
        volume_value = pd.to_numeric(latest.get("volume"), errors="coerce")
        if pd.notna(amount_value) and pd.notna(volume_value) and float(volume_value) > 0:
            vwap = float(amount_value) / float(volume_value)
        elif pd.notna(latest_open) and pd.notna(latest_high) and pd.notna(latest_low):
            vwap = (float(latest_open) + float(latest_high) + float(latest_low) + latest_close) / 4.0
        else:
            vwap = latest_close

        if pd.notna(latest_high) and latest_high > 0:
            close_vs_high = latest_close / latest_high - 1
        if pd.notna(vwap) and float(vwap) > 0:
            close_vs_vwap = latest_close / float(vwap) - 1
        if pd.notna(latest_high) and pd.notna(latest_low) and prev_close > 0:
            intraday_range_pct = (float(latest_high) - float(latest_low)) / prev_close
        if pd.notna(latest_open) and prev_close > 0:
            overnight_gap_pct = float(latest_open) / prev_close - 1

    return {
        "lag_1": float(s.iloc[-1]),
        "lag_2": float(s.iloc[-2]),
        "lag_3": float(s.iloc[-3]) if len(s) >= 3 else float(s.iloc[-1]),
        "lag_5": float(s.iloc[-5]) if len(s) >= 5 else float(s.iloc[-1]),
        "ret_1": float(ret_1),
        "ret_3": float(ret_3),
        "ret_5": float(ret_5),
        "ma_5": float(ma_5),
        "ma_10": float(ma_10),
        "ma_20": float(ma_20),
        "ma_gap_5": float(s.iloc[-1] / ma_5 - 1) if ma_5 > 0 else 0.0,
        "ma_gap_10": float(s.iloc[-1] / ma_10 - 1) if ma_10 > 0 else 0.0,
        "ma_gap_20": float(s.iloc[-1] / ma_20 - 1) if ma_20 > 0 else 0.0,
        "vol_5": float(s.pct_change().tail(5).std() or 0.0),
        "close_vs_high": float(close_vs_high),
        "close_vs_vwap": float(close_vs_vwap),
        "intraday_range_pct": float(intraday_range_pct),
        "overnight_gap_pct": float(overnight_gap_pct),
    }


# ---------------------------------------------------------------------------
# Cross-market features
# ---------------------------------------------------------------------------

def build_cross_market_features(
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    shfe_close: float,
    target_date: pd.Timestamp,
) -> Dict[str, float]:
    """Build cross-market features from external data sources."""
    result: Dict[str, float] = {col: 0.0 for col in FEATURE_COLUMNS_CROSS}

    # COMEX overnight return
    if not comex_daily.empty and len(comex_daily) >= 2:
        comex_sorted = comex_daily.sort_values("date")
        comex_last = comex_sorted[comex_sorted["date"] <= target_date]
        if len(comex_last) >= 2:
            result["comex_overnight_return"] = float(
                comex_last.iloc[-1]["close"] / comex_last.iloc[-2]["close"] - 1
            )

    # COMEX-SHFE premium
    if not comex_daily.empty and not usdcny_daily.empty and shfe_close > 0:
        comex_last = comex_daily[comex_daily["date"] <= target_date]
        usdcny_last = usdcny_daily[usdcny_daily["date"] <= target_date]
        if len(comex_last) > 0 and len(usdcny_last) > 0:
            comex_usd = float(comex_last.iloc[-1]["close"])
            rate = float(usdcny_last.iloc[-1]["usdcny"])
            comex_cny_g = comex_usd * rate / TROY_OZ_TO_GRAM
            if comex_cny_g > 0:
                result["comex_shfe_premium"] = (shfe_close - comex_cny_g) / comex_cny_g

    # Cross-market indicators
    if not cross_market.empty:
        cm = cross_market[cross_market["date"] <= target_date].sort_values("date")
        if "dxy" in cm.columns and len(cm) >= 6:
            dxy = cm["dxy"].dropna()
            if len(dxy) >= 6:
                result["dxy_5d_change"] = float(dxy.iloc[-1] / dxy.iloc[-6] - 1)

        if "vix" in cm.columns and cm["vix"].notna().any():
            vix_val = float(cm["vix"].dropna().iloc[-1])
            result["vix_level"] = vix_val
            if vix_val < 15:
                result["vix_regime"] = 0.0
            elif vix_val < 25:
                result["vix_regime"] = 1.0
            elif vix_val < 35:
                result["vix_regime"] = 2.0
            else:
                result["vix_regime"] = 3.0

        if "us10y" in cm.columns and len(cm) >= 6:
            y = cm["us10y"].dropna()
            if len(y) >= 6:
                result["us10y_5d_change"] = float(y.iloc[-1] / y.iloc[-6] - 1)

    # USDCNY direction
    if not usdcny_daily.empty:
        u = usdcny_daily[usdcny_daily["date"] <= target_date].sort_values("date")
        if len(u) >= 6:
            result["usdcny_direction"] = float(u["usdcny"].iloc[-1] / u["usdcny"].iloc[-6] - 1)

    return result


# ---------------------------------------------------------------------------
# Full feature vector builder
# ---------------------------------------------------------------------------

HOURS_TO_TARGET = {
    "04:00": 12.0,
    "09:00": 7.0,
    "12:00": 4.0,
    "16:00": 0.0,
    "20:00": 20.0,  # next day
    "24:00": 16.0,  # next day
}


def build_checkpoint_features(
    checkpoint: str,
    bars_60min: pd.DataFrame,
    daily_closes: pd.Series,
    prev_close_16: float,
    avg_session_volume: float,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    target_date: pd.Timestamp,
) -> Dict[str, float]:
    """Build full feature vector for one checkpoint."""
    filtered = _filter_bars_for_checkpoint(bars_60min, checkpoint, target_date)
    intraday = aggregate_checkpoint_bar(filtered, prev_close_16, avg_session_volume)

    # Use latest available close: intraday if available, else daily
    current_close = prev_close_16
    if not filtered.empty:
        current_close = float(filtered.iloc[-1]["close"])

    daily = build_daily_features(daily_closes)
    cross = build_cross_market_features(
        comex_daily, usdcny_daily, cross_market, current_close, target_date,
    )

    meta = {
        "hours_to_target": HOURS_TO_TARGET.get(checkpoint, 0.0),
        "day_of_week": float(target_date.dayofweek),
    }

    features: Dict[str, float] = {}
    features.update(intraday)
    features.update(daily)
    features.update(cross)
    features.update(meta)
    return features


# ---------------------------------------------------------------------------
# Training data builder
# ---------------------------------------------------------------------------

def build_training_dataset(
    bars_60min: pd.DataFrame,
    daily_df: pd.DataFrame,
    comex_daily: pd.DataFrame,
    usdcny_daily: pd.DataFrame,
    cross_market: pd.DataFrame,
    checkpoint: str,
    lookback_days: int = 240,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Build (X, y_return, y_direction) training data for one checkpoint.

    y is always the return from current effective close to the target 16:00 close.
    """
    daily_sorted = daily_df.sort_values("date").reset_index(drop=True)
    if len(daily_sorted) < lookback_days:
        lookback_days = len(daily_sorted) - 1

    start_idx = max(20, len(daily_sorted) - lookback_days)
    offset = CHECKPOINT_TARGET_OFFSET[checkpoint]

    rows: List[Dict[str, float]] = []
    targets_return: List[float] = []
    targets_direction: List[int] = []

    # Average volume for normalization
    if not bars_60min.empty:
        vol_by_date = bars_60min.groupby(bars_60min["date"].dt.date)["volume"].sum()
        avg_vol = float(vol_by_date.tail(60).mean()) if len(vol_by_date) > 0 else 1.0
    else:
        avg_vol = 1.0

    for i in range(start_idx, len(daily_sorted)):
        target_idx = i if offset == "same_day" else i + 1
        if target_idx >= len(daily_sorted):
            break

        current_date = pd.Timestamp(daily_sorted.iloc[i]["date"])
        target_close = float(daily_sorted.iloc[target_idx]["close"])
        prev_close = float(daily_sorted.iloc[i - 1]["close"]) if i > 0 else target_close

        daily_closes = daily_sorted.iloc[max(0, i - 20):i + 1]["close"]

        features = build_checkpoint_features(
            checkpoint=checkpoint,
            bars_60min=bars_60min,
            daily_closes=daily_closes,
            prev_close_16=prev_close,
            avg_session_volume=avg_vol / 6,  # rough per-session estimate
            comex_daily=comex_daily,
            usdcny_daily=usdcny_daily,
            cross_market=cross_market,
            target_date=current_date,
        )

        # Effective base: use intraday close if available, else prev daily close
        filtered = _filter_bars_for_checkpoint(bars_60min, checkpoint, current_date)
        if not filtered.empty:
            effective_base = float(filtered.iloc[-1]["close"])
        else:
            effective_base = prev_close

        if effective_base <= 0:
            continue

        ret = target_close / effective_base - 1
        targets_return.append(ret)
        targets_direction.append(1 if ret > 0 else 0)
        rows.append(features)

    if not rows:
        cols = all_feature_columns()
        return pd.DataFrame(columns=cols), pd.Series(dtype=float), pd.Series(dtype=int)

    X = pd.DataFrame(rows)
    # Ensure column order
    for col in all_feature_columns():
        if col not in X.columns:
            X[col] = 0.0
    X = X[all_feature_columns()]

    return X, pd.Series(targets_return, dtype=float), pd.Series(targets_direction, dtype=int)


def build_cot_features(
    cot_daily: "pd.DataFrame | None",
    target_date: pd.Timestamp,
) -> Dict[str, float]:
    """Build CFTC COT features for a given target_date.

    Args:
        cot_daily: Daily-frequency DataFrame from upsample_cot_to_daily(),
            must contain column 'date' plus derived COT fields.
            When None or empty, returns all-zero features (graceful fallback).
        target_date: Date for which to compute features (look-ahead prevented
            by alignment of cot_daily's key_col at upsample time).

    Returns:
        Dict with 8 keys matching FEATURE_COLUMNS_COT.
    """
    zero = {col: 0.0 for col in FEATURE_COLUMNS_COT}

    if cot_daily is None or cot_daily.empty or "date" not in cot_daily.columns:
        return zero

    df = cot_daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    # Filter strictly <= target_date
    df = df[df["date"] <= pd.Timestamp(target_date)].reset_index(drop=True)
    if df.empty:
        return zero

    # mm_net_pct_oi time series for derived features.
    # df is daily (forward-filled from weekly); deduplicate by tracking
    # consecutive-changes only, not values (flat periods are valid history).
    if "mm_net_pct_oi" not in df.columns:
        return zero
    series = pd.to_numeric(df["mm_net_pct_oi"], errors="coerce")

    # Use a "group by value change" pattern: keep first row of each run of
    # identical values. This preserves flat weeks vs. weekly changes correctly.
    shifted = series.shift(1)
    is_change = (series != shifted).fillna(True)
    series_weekly = series[is_change].reset_index(drop=True)
    if series_weekly.empty:
        return zero

    latest = float(series_weekly.iloc[-1])
    change_1w = latest - float(series_weekly.iloc[-2]) if len(series_weekly) >= 2 else 0.0
    change_4w = latest - float(series_weekly.iloc[-5]) if len(series_weekly) >= 5 else 0.0

    if len(series_weekly) >= 10:
        window = series_weekly.iloc[-52:]
        mu = float(window.mean())
        sigma = float(window.std(ddof=0))
        zscore = (latest - mu) / sigma if sigma > 1e-9 else 0.0
    else:
        zscore = 0.0

    def _latest(col: str) -> float:
        if col not in df.columns:
            return 0.0
        val = pd.to_numeric(df[col].iloc[-1], errors="coerce")
        return float(val) if pd.notna(val) else 0.0

    # OI 1w change
    oi_series = pd.to_numeric(df.get("open_interest", pd.Series(dtype=float)),
                              errors="coerce").dropna().drop_duplicates()
    if len(oi_series) >= 2:
        oi_latest = float(oi_series.iloc[-1])
        oi_prev = float(oi_series.iloc[-2])
        oi_change_pct = (oi_latest - oi_prev) / oi_prev if oi_prev > 0 else 0.0
    else:
        oi_change_pct = 0.0

    return {
        "cot_mm_net_pct_oi": round(latest, 6),
        "cot_mm_net_change_1w": round(change_1w, 6),
        "cot_mm_net_change_4w": round(change_4w, 6),
        "cot_mm_net_zscore_52w": round(zscore, 4),
        "cot_mm_long_pct_oi": round(_latest("mm_long_pct_oi"), 6),
        "cot_mm_short_pct_oi": round(_latest("mm_short_pct_oi"), 6),
        "cot_comm_net_pct_oi": round(_latest("comm_net_pct_oi"), 6),
        "cot_oi_change_1w_pct": round(oi_change_pct, 6),
    }
