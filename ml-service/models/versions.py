"""Version registry for the gold forecast.

Every version maps the same inputs (origin close, model return, horizon) to a
predicted close. Keeping them as pure functions makes the benchmark and the
daily job share exactly one definition of "what version X means".

Design rule: a version may only shrink or reweight the model return. Nothing
here may look at the target date's data.
"""
from __future__ import annotations

from typing import Callable, Dict, NamedTuple

# Shrinkage applied to the model's predicted return, by horizon (days).
HORIZON_SHRINK: Dict[int, float] = {1: 0.30, 3: 0.25, 5: 0.20, 10: 0.10}


class Version(NamedTuple):
    name: str
    description: str
    shrink: Callable[[int], float]


def _const(alpha: float) -> Callable[[int], float]:
    return lambda horizon: alpha


def _closest_horizon(table: Dict[int, float], horizon: int) -> float:
    """Shrinks step down for horizons between the calibrated anchor points.

    Horizon 2 resolves to the T+3 anchor (0.25) rather than the T+10 one, so an
    unlisted horizon never silently gets the most aggressive shrink.
    """
    keys = sorted(table)
    for k in keys:
        if horizon <= k:
            return table[k]
    return table[keys[-1]]


def _horizon_table(table: Dict[int, float]) -> Callable[[int], float]:
    return lambda horizon: _closest_horizon(table, int(horizon))


VERSIONS: Dict[str, Version] = {
    "v0": Version("v0", "persistence: predict the origin close", _const(0.0)),
    "v1": Version("v1", "current model, guards included", _const(1.0)),
    "v3": Version("v3", "model return x 0.5", _const(0.5)),
    "v4": Version("v4", "model return x 0.3", _const(0.3)),
    "v7": Version(
        "v7",
        "model return x horizon-specific shrink (0.30/0.25/0.20/0.10)",
        _horizon_table(HORIZON_SHRINK),
    ),
}

CHAMPION_DEFAULT = "v7"
FALLBACK = "v0"


def get(name: str) -> Version:
    key = name.strip().lower()
    if key not in VERSIONS:
        raise KeyError(f"unknown version {name!r}; known: {', '.join(sorted(VERSIONS))}")
    return VERSIONS[key]


def predict_close(version: str, origin_close: float, model_return: float, horizon: int) -> float:
    """Apply a version to a model return. Returns the predicted close in CNY/g."""
    alpha = get(version).shrink(int(horizon))
    if alpha == 0.0:
        return float(origin_close)
    return float(origin_close) * (1.0 + alpha * float(model_return))


def shrink_table() -> Dict[str, Dict[int, float]]:
    """Effective shrink by version and horizon, for documentation/audit."""
    return {v.name: {h: v.shrink(h) for h in (1, 3, 5, 10)} for v in VERSIONS.values()}