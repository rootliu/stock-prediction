"""Availability-time filtering for the daily SHFE forecasting path.

Daily OHLC is assumed complete at 16:00 Asia/Shanghai. External providers may
supply timezone-aware ``available_at``. Date-only legacy external bars use an
explicit conservative fallback: 08:00 Shanghai on the following calendar day.
That fallback is an assumption, not a reconstructed exchange publication time.
"""
from __future__ import annotations

import pandas as pd

LOCAL_TZ = "Asia/Shanghai"


def daily_cutoff(date: pd.Timestamp, prediction_at=None) -> pd.Timestamp:
    day = pd.Timestamp(date)
    day = day.tz_localize(LOCAL_TZ) if day.tzinfo is None else day.tz_convert(LOCAL_TZ)
    close = day.normalize() + pd.Timedelta(hours=16)
    if prediction_at is None:
        return close
    cutoff = pd.Timestamp(prediction_at)
    if cutoff.tzinfo is None:
        raise ValueError("prediction_at must include a timezone")
    cutoff = cutoff.tz_convert(LOCAL_TZ)
    if cutoff.normalize() != close.normalize() or cutoff < close:
        raise ValueError("Daily OHLC prediction_at must be on the origin date at/after 16:00 Shanghai")
    return cutoff


def available_observations(frame: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    cutoff = pd.Timestamp(cutoff)
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must include a timezone")
    if "available_at" in frame:
        # Reject ambiguous timestamps; do not silently interpret local time as UTC.
        stamps = frame["available_at"].map(pd.Timestamp)
        if stamps.isna().any() or any(t.tzinfo is None for t in stamps):
            raise ValueError("available_at must contain non-null timezone-aware timestamps")
        available = pd.to_datetime(stamps, utc=True)
    else:
        dates = pd.to_datetime(frame["date"])
        if dates.dt.tz is not None:
            dates = dates.dt.tz_localize(None)
        available = (dates.dt.normalize() + pd.Timedelta(days=1, hours=8)).dt.tz_localize(LOCAL_TZ)
    # A later revision of a historical bar must not replace the earlier vintage
    # until its own publication time has passed.
    result = frame.loc[available <= cutoff].copy()
    result["_available_at"] = available.loc[result.index]
    return (result.sort_values(["date", "_available_at"])
            .drop_duplicates("date", keep="last").drop(columns="_available_at"))


def availability_audit(frame: pd.DataFrame, cutoff: pd.Timestamp) -> dict:
    used = available_observations(frame, cutoff)
    policy = "explicit" if "available_at" in frame else "assumed_next_day_0800_shanghai"
    if used.empty:
        return {"policy": policy, "rows": 0, "last_source_date": None, "last_available_at": None}
    last = used.iloc[-1]
    if "available_at" in used:
        available = pd.Timestamp(last["available_at"])
    else:
        available = pd.Timestamp(last["date"]).tz_localize(None).normalize()
        available = (available + pd.Timedelta(days=1, hours=8)).tz_localize(LOCAL_TZ)
    return {"policy": policy, "rows": len(used), "last_source_date": str(pd.Timestamp(last["date"]).date()),
            "last_available_at": available.isoformat(), "age_hours": (cutoff-available).total_seconds()/3600}
