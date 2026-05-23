"""
Multi-dimensional market regime detection.

Extends single-axis volatility regime with:
  1. Trend regime       — uptrend / sideways / downtrend (EMA slope)
  2. Momentum regime    — strong_bull / mild_bull / neutral / mild_bear / strong_bear (RSI + ROC)
  3. Cross-asset regime — risk_on / risk_off / neutral (USDCNY + COMEX signals)

Composite regime rolls the four dimensions into a single actionable tag
that downstream risk-budget and scenario-generation logic can consume.

Design goals:
  - Pure-function; no I/O, no model state
  - Accepts pandas Series / DataFrame the same shape run_gold_analysis already has
  - Safe on short histories (returns 'unknown' rather than raising)
  - Cheap to compute (rolling ops only)
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from .volatility_regime import compute_regime_info as compute_vol_regime_info


# ──────────────────────────────────────────────────────────────────
# Trend regime (EMA slope based)
# ──────────────────────────────────────────────────────────────────

TREND_THRESHOLDS = {
    # annualized slope (%) derived from 20-day EMA log-return
    "uptrend": 0.15,       # > +15% annualized
    "downtrend": -0.15,    # < -15% annualized
    # otherwise sideways
}


def classify_trend(closes: pd.Series, window: int = 20) -> Dict:
    if len(closes) < window + 5:
        return {"trend": "unknown", "ema_slope_ann": 0.0, "window": window}
    ema = closes.ewm(span=window, adjust=False).mean()
    # slope = log-return over last `window` days, annualized
    recent = ema.tail(window + 1)
    if recent.iloc[0] <= 0:
        return {"trend": "unknown", "ema_slope_ann": 0.0, "window": window}
    log_ret = np.log(recent.iloc[-1] / recent.iloc[0])
    ann_slope = log_ret * (252.0 / window)
    if ann_slope > TREND_THRESHOLDS["uptrend"]:
        trend = "uptrend"
    elif ann_slope < TREND_THRESHOLDS["downtrend"]:
        trend = "downtrend"
    else:
        trend = "sideways"
    return {
        "trend": trend,
        "ema_slope_ann": round(float(ann_slope) * 100, 2),  # %
        "window": window,
    }


# ──────────────────────────────────────────────────────────────────
# Momentum regime (RSI + ROC)
# ──────────────────────────────────────────────────────────────────

def _rsi(closes: pd.Series, period: int = 14) -> float:
    if len(closes) < period + 2:
        return float("nan")
    delta = closes.diff().dropna()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    if loss.iloc[-1] == 0 or pd.isna(loss.iloc[-1]):
        return 100.0 if gain.iloc[-1] > 0 else 50.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100 - 100 / (1 + rs))


def _roc(closes: pd.Series, period: int = 10) -> float:
    if len(closes) < period + 1:
        return float("nan")
    past = closes.iloc[-(period + 1)]
    now = closes.iloc[-1]
    if past <= 0:
        return float("nan")
    return float((now / past - 1.0) * 100)


def classify_momentum(closes: pd.Series,
                       rsi_period: int = 14,
                       roc_period: int = 10) -> Dict:
    rsi = _rsi(closes, rsi_period)
    roc = _roc(closes, roc_period)
    if pd.isna(rsi) or pd.isna(roc):
        return {"momentum": "unknown", "rsi": None, "roc_pct": None}

    # Combined scoring: RSI centers on 50, ROC in %
    # strong bull: rsi > 65 and roc > +4
    # mild bull:   rsi > 55 or roc > +1.5
    # strong bear: rsi < 35 and roc < -4
    # mild bear:   rsi < 45 or roc < -1.5
    # neutral:     otherwise
    if rsi > 65 and roc > 4:
        mom = "strong_bull"
    elif rsi < 35 and roc < -4:
        mom = "strong_bear"
    elif rsi > 55 or roc > 1.5:
        mom = "mild_bull"
    elif rsi < 45 or roc < -1.5:
        mom = "mild_bear"
    else:
        mom = "neutral"

    return {
        "momentum": mom,
        "rsi": round(rsi, 1),
        "roc_pct": round(roc, 2),
    }


# ──────────────────────────────────────────────────────────────────
# Cross-asset regime (USDCNY + COMEX)
# ──────────────────────────────────────────────────────────────────

def classify_cross_asset(
    comex_closes: Optional[pd.Series] = None,
    usdcny_closes: Optional[pd.Series] = None,
    shfe_closes: Optional[pd.Series] = None,
    window: int = 20,
) -> Dict:
    """
    Risk-on / risk-off heuristic for gold context:
      - COMEX gold up + USDCNY up (CNY weak) = classic safe-haven bid → risk_off
      - COMEX gold down + USDCNY down = risk_on (USD assets bid)
      - Low SHFE-COMEX correlation = regime breakdown signal
    """
    out = {
        "cross_asset": "unknown",
        "shfe_comex_corr": None,
        "usdcny_chg_pct": None,
        "comex_chg_pct": None,
    }

    def _pct_change(s: pd.Series, w: int) -> Optional[float]:
        if s is None or len(s) < w + 1:
            return None
        past = float(s.iloc[-(w + 1)])
        now = float(s.iloc[-1])
        if past <= 0:
            return None
        return (now / past - 1.0) * 100

    comex_chg = _pct_change(comex_closes, window)
    usdcny_chg = _pct_change(usdcny_closes, window)
    out["comex_chg_pct"] = None if comex_chg is None else round(comex_chg, 2)
    out["usdcny_chg_pct"] = None if usdcny_chg is None else round(usdcny_chg, 2)

    # Correlation gauge (regime stability)
    if (shfe_closes is not None and comex_closes is not None
            and len(shfe_closes) >= window + 5 and len(comex_closes) >= window + 5):
        s1 = shfe_closes.tail(window + 5).pct_change().dropna().tail(window)
        s2 = comex_closes.tail(window + 5).pct_change().dropna().tail(window)
        n = min(len(s1), len(s2))
        if n >= 5:
            corr = float(np.corrcoef(s1.tail(n).values, s2.tail(n).values)[0, 1])
            if not np.isnan(corr):
                out["shfe_comex_corr"] = round(corr, 2)

    # Regime labeling — needs both signals
    if comex_chg is None or usdcny_chg is None:
        return out

    # Thresholds in % over the window
    gold_up = comex_chg > 2
    gold_dn = comex_chg < -2
    cny_weak = usdcny_chg > 1      # USDCNY up → CNY weaker → safe-haven bid
    cny_strong = usdcny_chg < -1

    if gold_up and cny_weak:
        out["cross_asset"] = "risk_off"   # strong safe-haven
    elif gold_dn and cny_strong:
        out["cross_asset"] = "risk_on"    # risk appetite returning
    elif gold_up or cny_weak:
        out["cross_asset"] = "mild_risk_off"
    elif gold_dn or cny_strong:
        out["cross_asset"] = "mild_risk_on"
    else:
        out["cross_asset"] = "neutral"

    return out


# ──────────────────────────────────────────────────────────────────
# Composite regime
# ──────────────────────────────────────────────────────────────────

def _severity_score(vol_regime: str, momentum: str, cross_asset: str) -> int:
    """0=calm, 4=panic; used to decide extra dampening."""
    s = 0
    s += {"low": 0, "normal": 1, "high": 2, "extreme": 3}.get(vol_regime, 1)
    s += {"strong_bull": 1, "strong_bear": 1}.get(momentum, 0)
    s += {"risk_off": 1, "risk_on": 1}.get(cross_asset, 0)
    return s


def compute_market_regime(
    shfe_daily_closes: pd.Series,
    comex_daily_closes: Optional[pd.Series] = None,
    usdcny_daily_closes: Optional[pd.Series] = None,
    window: int = 20,
) -> Dict:
    """
    Full multi-dimensional regime snapshot.

    Returns a dict ready for pretty-printing and scenario scaling.
    Keys:
      volatility: {regime, annualized_vol, dampening, direction_threshold, window}
      trend:      {trend, ema_slope_ann, window}
      momentum:   {momentum, rsi, roc_pct}
      cross_asset:{cross_asset, shfe_comex_corr, usdcny_chg_pct, comex_chg_pct}
      composite:  {label, severity, extra_dampening}
    """
    vol = compute_vol_regime_info(shfe_daily_closes, window=window)
    trend = classify_trend(shfe_daily_closes, window=window)
    momentum = classify_momentum(shfe_daily_closes)
    cross = classify_cross_asset(
        comex_closes=comex_daily_closes,
        usdcny_closes=usdcny_daily_closes,
        shfe_closes=shfe_daily_closes,
        window=window,
    )

    severity = _severity_score(
        vol.get("regime", "normal"),
        momentum.get("momentum", "neutral"),
        cross.get("cross_asset", "neutral"),
    )
    # Extra dampening layered on top of vol-only dampening
    # (multiplied; does not replace existing logic).
    extra_damp = {0: 1.00, 1: 0.95, 2: 0.85, 3: 0.75, 4: 0.65}.get(severity, 0.80)

    # Human-readable composite label
    vol_lbl = vol["regime"].upper()
    trend_lbl = trend["trend"]
    mom_lbl = momentum["momentum"]
    cross_lbl = cross["cross_asset"]
    composite_label = f"VOL:{vol_lbl} · TREND:{trend_lbl} · MOM:{mom_lbl} · CROSS:{cross_lbl}"

    return {
        "volatility": vol,
        "trend": trend,
        "momentum": momentum,
        "cross_asset": cross,
        "composite": {
            "label": composite_label,
            "severity": severity,   # 0..4
            "extra_dampening": extra_damp,
        },
    }


def format_regime_report(regime: Dict) -> str:
    """Pretty multi-line string for console / Feishu reports."""
    v = regime["volatility"]
    t = regime["trend"]
    m = regime["momentum"]
    c = regime["cross_asset"]
    cp = regime["composite"]

    lines = [
        f"  [Regime] {cp['label']}",
        f"    · Volatility : {v['regime'].upper():<8} "
        f"年化 {v['annualized_vol']:>5.1f}%  "
        f"压缩 {(1 - v['dampening']) * 100:>3.0f}%  "
        f"方向阈值 {v['direction_threshold'] * 100:>3.0f}%",
        f"    · Trend      : {t['trend']:<8} "
        f"EMA{t['window']}斜率 {t['ema_slope_ann']:>+6.2f}%/年",
        f"    · Momentum   : {m['momentum']:<12} "
        f"RSI14={m['rsi']}  ROC10={m['roc_pct']}%"
        if m['rsi'] is not None else f"    · Momentum   : unknown (样本不足)",
        f"    · CrossAsset : {c['cross_asset']:<14} "
        f"SHFE-COMEX corr={c['shfe_comex_corr']}  "
        f"USDCNY Δ={c['usdcny_chg_pct']}%  COMEX Δ={c['comex_chg_pct']}%",
        f"    · Composite  : severity={cp['severity']}/4  "
        f"extra_dampening={cp['extra_dampening']:.2f}",
    ]
    return "\n".join(lines)
