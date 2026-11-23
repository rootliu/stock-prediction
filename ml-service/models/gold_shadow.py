"""Shadow-only 80% price intervals. No directional probabilities or point adjustments."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAL = ROOT / "config/gold_versions/calibration.json"
FROZEN = pd.Timestamp("2026-11-02")
RULE = "asym-risk-shadow-1"


def features(daily, comex, origin):
    history = daily.loc[daily.date <= origin].sort_values("date").tail(26)
    if len(history) < 26 or history.date.iloc[-1] != origin:
        raise ValueError("SHFE origin or history unavailable")
    prev = history.close.shift()
    ranges = (history.high - history.low) / prev
    typical = float(ranges.iloc[1:-5].mean())
    if not np.isfinite(typical) or typical <= 0:
        raise ValueError("invalid reference range")
    ratio = float(ranges.tail(5).mean()) / typical
    gap = float((history.open / prev - 1).iloc[-1])
    # No same-date US close is known at the SHFE 16:00 origin.
    us = comex.loc[comex.date < origin].sort_values("date").tail(2)
    overnight = float(us.close.iloc[-1] / us.close.iloc[0] - 1) if len(us) == 2 else 0.
    stress = float(np.clip(ratio - 1, 0, 1))
    down_shock = float(np.clip(max(-gap, -overnight, 0) / typical, 0, 1))
    return {"range_ratio": ratio, "gap_pct": 100 * gap, "us_last_return_pct": 100 * overnight,
            "us_session": str(us.date.max().date()) if len(us) else None,
            "lower_factor": 1 + .65 * stress + .25 * down_shock, "upper_factor": 1 + .25 * stress}


def interval(cal, origin, h, point, signals, history):
    if origin <= FROZEN:
        raise ValueError("frozen calibration not yet available at origin")
    k = min(cal, key=lambda key: (abs(int(key) - h), int(key)))
    q = cal[k]
    low, high = np.array([q["q_low"], q["q_high"]]) * np.sqrt(h / int(k))
    a, b = low, high
    n = 0
    if history is not None and not history.empty:
        mask = ((history.origin_date < origin) & (history.target_date <= origin)
                & (history.origin_date > FROZEN) & (history.horizon == h))
        mature = (history.loc[mask].dropna(subset=["residual"]).sort_values("target_date")
                  .drop_duplicates("origin_date").tail(60))
        n = len(mature)
        if n >= 5:
            weight = n / (n + 30.)
            lq, uq = mature.residual.quantile([.1, .9])
            a = min(-.01, (1 - weight) * low + weight * lq)
            b = max(.01, (1 - weight) * high + weight * uq)
    return dict(horizon=h, point=point, fixed_low=round(point + low, 2), fixed_high=round(point + high, 2),
                shadow_low=round(point + a * signals["lower_factor"], 2),
                shadow_high=round(point + b * signals["upper_factor"], 2), mature_n=n, frozen_n=q["n"])


def issued_history(folder, daily, origin):
    records = []
    closes = daily.set_index("date").close
    for path in sorted(Path(folder).glob("*/manifest.json")) if folder else ():
        m = json.loads(path.read_bytes())
        key = os.environ.get("GOLD_HISTORY_KEY")
        if m["status"] != "ok" or m.get("model") != "direct/v1" or not key or m.get("history_key") != key:
            continue
        issued = pd.Timestamp(m["generated_at"]).tz_convert("Asia/Shanghai").tz_localize(None)
        start = pd.Timestamp(m["origin"])
        if start >= origin or issued > origin + pd.Timedelta(hours=16):
            continue
        bundle = path.parent / Path(m["files"]["scenario_json"]).name
        raw = bundle.read_bytes()
        if hashlib.sha256(raw).hexdigest() != m["sha256"]["scenario_json"]:
            raise ValueError("issued scenario digest mismatch")
        for h, row in enumerate(json.loads(raw)["predictions"], 1):
            target = pd.Timestamp(row["date"])
            if target <= origin and target in closes and issued < target + pd.Timedelta(hours=16):
                records.append(dict(origin_date=start, target_date=target, horizon=h,
                                    residual=closes[target] - row["close"]))
    return pd.DataFrame(records)


def report(daily, comex, origin, predictions):
    if os.environ.get("GOLD_SHADOW_INTERVAL", "1") == "0":
        return {"status": "disabled"}
    try:
        history = issued_history(os.environ.get("GOLD_RUN_HISTORY"), daily, origin)
        signals = features(daily, comex, origin)
        cal = json.loads(CAL.read_bytes())["versions"]["v1"]
        rows = [dict(date=p["date"], **interval(cal, origin, h, float(p["close"]), signals, history))
                for h, p in enumerate(predictions, 1)]
        return dict(status="shadow_only", rule=RULE, calibration_sha256=hashlib.sha256(CAL.read_bytes()).hexdigest(),
                    features=signals, rows=rows)
    except (KeyError, OSError, ValueError, TypeError, IndexError) as exc:
        return dict(status="unavailable", reason=str(exc))
