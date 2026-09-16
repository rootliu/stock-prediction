"""Conservative, held-out directional calibration, independent of price guards."""
from __future__ import annotations

import numpy as np
from scipy.stats import beta


LABELS = ("跌", "平", "涨")


def direction_label(delta):
    return "涨" if delta > 0.5 else ("跌" if delta < -0.5 else "平")


def calibration_rows(size, split, horizon):
    # Purge overlapping training labels; thin overlapping calibration outcomes.
    return np.arange(split + horizon, size, horizon, dtype=int)


def maturity_calibration_rows(origins, targets, split):
    """For an already purged fit, retain disjoint label intervals by date.

    Unlike row strides, this works when invalid observations removed samples.
    Equal endpoints are allowed: adjacent returns share no return increment.
    """
    selected = []
    previous_target = None
    for i in range(split, len(origins)):
        origin, target = origins.iloc[i], targets.iloc[i]
        if target <= origin:
            raise ValueError("Calibration target must follow origin")
        if previous_target is None or origin >= previous_target:
            selected.append(i)
            previous_target = target
    return np.asarray(selected, dtype=int)


def fit_calibration(raw_up, deltas):
    raw_up = np.asarray(raw_up, dtype=float)
    deltas = np.asarray(deltas, dtype=float)
    if raw_up.ndim != 1 or deltas.shape != raw_up.shape:
        raise ValueError("Calibration inputs must be equally sized 1D arrays")
    valid = np.isfinite(raw_up) & np.isfinite(deltas) & (raw_up >= 0) & (raw_up <= 1)
    return {"raw_up": raw_up[valid], "deltas": deltas[valid]}


def directional_confidence(calibration, raw_up, direction):
    """Bin frequencies with a fixed symmetric prior, NOT a guarantee of accuracy.

    Beta intervals describe the selected bin's latent frequency under the model;
    they do not include distribution shift or cross-market timestamp uncertainty.
    """
    raw = np.asarray(calibration.get("raw_up", []), dtype=float)
    deltas = np.asarray(calibration.get("deltas", []), dtype=float)
    available = raw_up is not None and np.isfinite(raw_up) and 0 <= raw_up <= 1
    edges = [1 / 3, 2 / 3]
    selected = (np.digitize(raw, edges) == np.digitize(raw_up, edges)) if available else np.zeros(len(raw), dtype=bool)
    outcomes = deltas[selected]
    counts = np.array([(outcomes < -0.5).sum(), (np.abs(outcomes) <= 0.5).sum(), (outcomes > 0.5).sum()], dtype=float)
    posterior = counts + np.array([4.75, 0.5, 4.75])
    probabilities = posterior / posterior.sum()
    index = LABELS.index(direction)
    lower, upper = beta.ppf([0.05, 0.95], posterior[index], posterior.sum() - posterior[index])
    reasons = []
    if not available:
        reasons.append("missing_classifier")
    if len(outcomes) < 10:
        reasons.append("insufficient_calibration_samples")
    if int(np.argmax(probabilities)) != index:
        reasons.append("price_probability_disagreement")
    if probabilities[index] < 0.60 or lower <= 0.50:
        reasons.append("weak_direction_evidence")
    return {
        "confidence": round(float(probabilities[index] * 100), 1),
        "confidence_method": "maturity_bin_dirichlet_v2",
        "confidence_status": "experimental_not_validated",
        "confidence_kind": "experimental_direction_probability",
        "up_probability": float(probabilities[2]),
        "down_probability": float(probabilities[0]),
        "flat_probability": float(probabilities[1]),
        "direction_signal": "watch" if reasons else "supported",
        "confidence_reasons": "|".join(reasons) or "supported",
        "confidence_low": round(float(lower * 100), 1),
        "confidence_high": round(float(upper * 100), 1),
        "calibration_count": int(len(outcomes)),
        "calibration_total": int(len(raw)),
        "calibration_raw_up": float(raw_up) if available else None,
    }
