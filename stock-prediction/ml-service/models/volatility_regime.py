"""
Volatility regime detection and adaptive dampening.

Classifies market into low/normal/high/extreme regimes based on
realized volatility, and provides dampening factors to scale
prediction magnitude accordingly.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


REGIME_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    "low": (0.0, 0.15),
    "normal": (0.15, 0.30),
    "high": (0.30, 0.50),
    "extreme": (0.50, float("inf")),
}

REGIME_DAMPENING: Dict[str, float] = {
    "low": 1.0,
    "normal": 0.85,
    "high": 0.55,
    "extreme": 0.30,
}

REGIME_DIRECTION_THRESHOLD: Dict[str, float] = {
    "low": 0.50,
    "normal": 0.55,
    "high": 0.60,
    "extreme": 0.65,
}


def realized_volatility(closes: pd.Series, window: int = 20) -> float:
    """Compute annualized realized volatility from daily closes."""
    if len(closes) < max(window, 5):
        return 0.0
    rets = closes.pct_change().dropna().tail(window)
    if len(rets) < 3:
        return 0.0
    return float(rets.std() * np.sqrt(252))


def classify_regime(ann_vol: float) -> str:
    """Map annualized vol to regime label."""
    for regime, (lo, hi) in REGIME_THRESHOLDS.items():
        if lo <= ann_vol < hi:
            return regime
    return "extreme"


def get_dampening(regime: str) -> float:
    """Return dampening multiplier for predicted change."""
    return REGIME_DAMPENING.get(regime, 0.55)


def get_direction_threshold(regime: str) -> float:
    """Minimum confidence to trust direction in this regime."""
    return REGIME_DIRECTION_THRESHOLD.get(regime, 0.55)


def dampen_prediction(
    predicted_close: float,
    base_close: float,
    regime: str,
) -> float:
    """Apply regime-aware dampening to a raw prediction."""
    raw_change = predicted_close - base_close
    dampening = get_dampening(regime)
    return base_close + raw_change * dampening


def compute_regime_info(daily_closes: pd.Series, window: int = 20) -> Dict:
    """Full regime analysis for display/logging."""
    ann_vol = realized_volatility(daily_closes, window)
    regime = classify_regime(ann_vol)
    return {
        "annualized_vol": round(ann_vol * 100, 1),
        "regime": regime,
        "dampening": get_dampening(regime),
        "direction_threshold": get_direction_threshold(regime),
        "window": window,
    }
