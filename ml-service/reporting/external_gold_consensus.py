from __future__ import annotations

from datetime import datetime
from math import exp, log
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Curated survey snapshot based on current English-language financial coverage.
# External curve uses these sources as a primary anchor for near-term direction.
EXTERNAL_SURVEY_SNAPSHOT: List[Dict[str, Any]] = [
    {
        "source": "FXStreet",
        "published_at": "2026-03-09",
        "url": "https://www.fxstreet.com/analysis/gold-price-forecast-xau-usd-bears-the-brunt-of-energy-shock-amid-widening-middle-east-war-202603090319/",
        "type": "support_resistance",
        "weight": 0.35,
        "support": 4999.94,
        "resistance": 5141.05,
        "bias": "gentle_upside",
        "horizon_days": 5,
        "summary": "Short-term technical article still described momentum as mildly constructive while keeping nearby support intact.",
    },
    {
        "source": "Investing.com Technical",
        "published_at": "2026-03-09",
        "url": "https://www.investing.com/technical/commodities-technical-analysis",
        "type": "signal_mix",
        "weight": 0.35,
        "horizon_days": 5,
        "signals": {
            "30m": "Neutral",
            "hourly": "Strong Sell",
            "5h": "Strong Sell",
            "daily": "Neutral",
            "weekly": "Strong Buy",
            "monthly": "Strong Buy",
        },
        "summary": "The time-frame mix is weak in the short end but still constructive on weekly and monthly views.",
    },
    {
        "source": "Reuters/Investing - JP Morgan",
        "published_at": "2026-02-25",
        "url": "https://www.investing.com/news/economy-news/jp-morgan-raises-longterm-gold-price-forecast-to-4500-4524848",
        "type": "dated_target",
        "weight": 0.15,
        "current_ref": 5248.89,
        "target_ref": 6300.0,
        "target_date": "2026-12-31",
        "summary": "JP Morgan kept a bullish medium-term frame and still pointed to a higher year-end target.",
    },
    {
        "source": "Reuters/Investing - Macquarie",
        "published_at": "2026-02-05",
        "url": "https://www.investing.com/news/economy-news/factboxmacquarie-hikes-gold-forecasts-for-2026-4488571",
        "type": "dated_target",
        "weight": 0.15,
        "current_ref": 4875.71,
        "target_ref": 4590.0,
        "target_date": "2026-03-31",
        "summary": "Macquarie expected a corrective phase into the end of the quarter despite staying constructive for 2026 as a whole.",
    },
]

_SIGNAL_SCORE = {
    "Strong Sell": -2.0,
    "Sell": -1.0,
    "Neutral": 0.0,
    "Buy": 1.0,
    "Strong Buy": 2.0,
}

_BIAS_WEIGHTS = {
    "bearish": 0.3,
    "gentle_downside": 0.4,
    "neutral": 0.5,
    "gentle_upside": 0.65,
    "bullish": 0.7,
}


def _business_days_between(start_date: str, end_date: str) -> int:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if end <= start:
        return 1
    return max(len(pd.bdate_range(start=start, end=end)), 1)


def _compound_curve(total_return: float, step_count: int) -> np.ndarray:
    if step_count <= 0:
        return np.array([1.0])
    daily_return = (1 + total_return) ** (1 / step_count) - 1
    day_index = np.arange(0, step_count + 1)
    return np.power(1 + daily_return, day_index)


def _curve_from_support_resistance(source: Dict[str, Any], step_count: int) -> Dict[str, Any]:
    support = float(source["support"])
    resistance = float(source["resistance"])
    center = (support + resistance) / 2
    bias_weight = _BIAS_WEIGHTS.get(source.get("bias", "neutral"), 0.5)
    target = support * (1 - bias_weight) + resistance * bias_weight
    implied_return = target / center - 1
    return {
        "curve_ratio": _compound_curve(implied_return, step_count),
        "implied_return_pct": implied_return * 100,
        "bias": "Bullish" if implied_return > 0 else "Bearish" if implied_return < 0 else "Neutral",
        "anchor": round(target, 2),
    }


def _curve_from_signal_mix(source: Dict[str, Any], step_count: int) -> Dict[str, Any]:
    weights = {
        "30m": 0.05,
        "hourly": 0.3,
        "5h": 0.3,
        "daily": 0.2,
        "weekly": 0.1,
        "monthly": 0.05,
    }
    weighted_score = 0.0
    for key, weight in weights.items():
        weighted_score += _SIGNAL_SCORE.get(source["signals"].get(key, "Neutral"), 0.0) * weight

    implied_return = float(np.clip(weighted_score * 0.01, -0.015, 0.015))
    return {
        "curve_ratio": _compound_curve(implied_return, step_count),
        "implied_return_pct": implied_return * 100,
        "bias": "Bullish" if implied_return > 0 else "Bearish" if implied_return < 0 else "Neutral",
        "anchor": round(weighted_score, 3),
    }


def _curve_from_dated_target(source: Dict[str, Any], step_count: int, horizon_days: float) -> Dict[str, Any]:
    total_days = _business_days_between(source["published_at"], source["target_date"])
    target_return = float(source["target_ref"]) / float(source["current_ref"]) - 1
    log_daily_return = log(1 + target_return) / total_days
    total_horizon_return = exp(log_daily_return * horizon_days) - 1
    return {
        "curve_ratio": _compound_curve(total_horizon_return, step_count),
        "implied_return_pct": total_horizon_return * 100,
        "bias": "Bullish" if total_horizon_return > 0 else "Bearish" if total_horizon_return < 0 else "Neutral",
        "anchor": round(float(source["target_ref"]), 2),
    }


def _fit_curve(prices: np.ndarray) -> np.ndarray:
    day_index = np.arange(len(prices))
    degree = min(2, len(prices) - 1)
    if degree <= 0:
        return prices.astype(float)
    coeffs = np.polyfit(day_index, prices.astype(float), degree)
    fitted = np.polyval(coeffs, day_index)
    return fitted.astype(float)


def _classify_deviation(internal_price: float, external_price: float) -> str:
    if external_price == 0:
        return "UNKNOWN"
    diff_pct = (internal_price / external_price - 1) * 100
    abs_diff = abs(diff_pct)
    if abs_diff >= 5:
        return "过于激进(偏多)" if diff_pct > 0 else "过于激进(偏空)"
    if abs_diff >= 2:
        return "偏离较大(偏多)" if diff_pct > 0 else "偏离较大(偏空)"
    return "接近外部主线"


def _format_timestamp(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d %H:%M")


def build_external_gold_curve_comparison(
    latest_price: float,
    forecast_frame: pd.DataFrame,
    reference_time: pd.Timestamp | None = None,
    horizon_days: float | None = None,
    blend_weight_external: float = 0.7,
) -> Dict[str, Any]:
    if forecast_frame.empty:
        raise ValueError("forecast_frame 不能为空")

    forecast_dates = pd.to_datetime(forecast_frame["date"])
    step_count = len(forecast_frame)
    if reference_time is None:
        if len(forecast_dates) > 1:
            reference_time = forecast_dates.iloc[0] - (forecast_dates.iloc[1] - forecast_dates.iloc[0])
        else:
            reference_time = pd.Timestamp(datetime.now())
    if horizon_days is None:
        horizon_days = max((forecast_dates.iloc[-1] - reference_time).total_seconds() / 86400, 1 / 6)

    survey_rows: List[Dict[str, Any]] = []
    curve_stack: List[np.ndarray] = []
    weight_stack: List[float] = []

    for source in EXTERNAL_SURVEY_SNAPSHOT:
        if source["type"] == "support_resistance":
            result = _curve_from_support_resistance(source, step_count)
        elif source["type"] == "signal_mix":
            result = _curve_from_signal_mix(source, step_count)
        else:
            result = _curve_from_dated_target(source, step_count, horizon_days)

        curve_stack.append(result["curve_ratio"])
        weight_stack.append(float(source["weight"]))
        survey_rows.append(
            {
                "Source": source["source"],
                "Published": source["published_at"],
                "Type": source["type"],
                "Weight": round(float(source["weight"]), 2),
                "Bias": result["bias"],
                "Implied Horizon Return %": round(float(result["implied_return_pct"]), 2),
                "Anchor": result["anchor"],
                "Summary": source["summary"],
                "URL": source["url"],
            }
        )

    weights = np.array(weight_stack, dtype=float)
    weights = weights / weights.sum()
    external_ratio = np.average(np.vstack(curve_stack), axis=0, weights=weights)
    external_raw = latest_price * external_ratio
    internal_raw = np.concatenate(([latest_price], forecast_frame["close"].astype(float).values))
    blended_raw = blend_weight_external * external_raw + (1 - blend_weight_external) * internal_raw

    external_fitted = _fit_curve(external_raw)
    internal_fitted = _fit_curve(internal_raw)
    blended_fitted = _fit_curve(blended_raw)

    compare_rows: List[Dict[str, Any]] = []
    for idx, current_date in enumerate(forecast_dates, start=1):
        external_price = float(external_fitted[idx])
        internal_price = float(internal_fitted[idx])
        blended_price = float(blended_fitted[idx])
        deviation_pct = (internal_price / external_price - 1) * 100 if external_price else np.nan
        compare_rows.append(
            {
                "Date": _format_timestamp(current_date),
                "External Main": round(external_price, 2),
                "Internal Model": round(internal_price, 2),
                "Blended Curve": round(blended_price, 2),
                "Internal vs External %": round(float(deviation_pct), 2),
                "Deviation Label": _classify_deviation(internal_price, external_price),
            }
        )

    consensus_return_pct = (external_fitted[-1] / latest_price - 1) * 100 if latest_price else 0.0
    summary = {
        "survey_as_of": datetime.now().strftime("%Y-%m-%d"),
        "external_curve_role": "primary",
        "blend_weight_external": blend_weight_external,
        "external_horizon_return_pct": round(float(consensus_return_pct), 2),
        "horizon_days": round(float(horizon_days), 2),
        "step_count": step_count,
        "source_count": len(survey_rows),
    }

    return {
        "survey_frame": pd.DataFrame(survey_rows),
        "comparison_frame": pd.DataFrame(compare_rows),
        "curve_frame": pd.DataFrame(
            {
                "step": np.arange(0, step_count + 1),
                "date": [_format_timestamp(reference_time)] + [_format_timestamp(d) for d in forecast_dates],
                "external_main": np.round(external_fitted, 2),
                "internal_model": np.round(internal_fitted, 2),
                "blended_curve": np.round(blended_fitted, 2),
            }
        ),
        "summary": summary,
    }
