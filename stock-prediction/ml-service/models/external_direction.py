from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Fallback viewpoints when local CSV is missing or invalid.
DEFAULT_AUTHORITY_VIEWPOINTS: List[Dict[str, Any]] = [
    {
        "source": "World Gold Council Outlook 2026",
        "published_at": "2025-12-04",
        "direction_score": 0.20,
        "confidence": 1.0,
        "half_life_days": 45,
    },
    {
        "source": "LBMA Forecast Survey 2026",
        "published_at": "2026-01-10",
        "direction_score": 0.25,
        "confidence": 0.9,
        "half_life_days": 40,
    },
    {
        "source": "Reuters/Goldman target raise",
        "published_at": "2026-01-22",
        "direction_score": 0.35,
        "confidence": 0.9,
        "half_life_days": 30,
    },
    {
        "source": "Reuters/UBS target raise",
        "published_at": "2026-01-30",
        "direction_score": 0.40,
        "confidence": 0.9,
        "half_life_days": 30,
    },
    {
        "source": "Reuters/Wells Fargo target raise",
        "published_at": "2026-02-04",
        "direction_score": 0.35,
        "confidence": 0.85,
        "half_life_days": 30,
    },
]

DEFAULT_EXTERNAL_DIRECTION_CSV = Path(__file__).resolve().parents[1] / "data" / "external_direction_signal.csv"

EXTERNAL_DIRECTION_COLUMNS = [
    "ext_dir_level",
    "ext_dir_ema_5",
    "ext_dir_ema_20",
    "ext_dir_delta_3",
    "ext_conf_level",
    "ext_stance_dispersion",
]

_COLUMN_RENAME = {
    "date": "published_at",
    "published_at": "published_at",
    "publish_date": "published_at",
    "source": "source",
    "direction_score": "direction_score",
    "direction": "direction_score",
    "score": "direction_score",
    "confidence": "confidence",
    "weight": "confidence",
    "half_life_days": "half_life_days",
    "half_life": "half_life_days",
}


def _normalize_point(point: Dict[str, Any]) -> Dict[str, Any]:
    published = pd.Timestamp(point["published_at"]).strftime("%Y-%m-%d")
    return {
        "source": str(point["source"]),
        "published_at": published,
        "direction_score": float(np.clip(float(point["direction_score"]), -1.0, 1.0)),
        "confidence": float(np.clip(float(point["confidence"]), 0.0, 1.0)),
        "half_life_days": float(max(float(point["half_life_days"]), 1.0)),
    }


def _build_meta(mode: str, points: List[Dict[str, Any]], csv_path: Path, warning: str | None = None) -> Dict[str, Any]:
    return {
        "mode": mode,
        "csv_path": str(csv_path),
        "point_count": len(points),
        "latest_published_at": max((p["published_at"] for p in points), default=None),
        "warning": warning,
    }


def load_external_direction_points(
    csv_path: str | None = None,
    allow_fallback: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    path = Path(csv_path).expanduser().resolve() if csv_path else DEFAULT_EXTERNAL_DIRECTION_CSV

    if not path.exists():
        if not allow_fallback:
            raise FileNotFoundError(f"外部方向因子 CSV 不存在: {path}")
        fallback = [_normalize_point(p) for p in DEFAULT_AUTHORITY_VIEWPOINTS]
        return fallback, _build_meta("fallback", fallback, path, warning="csv_not_found")

    raw = pd.read_csv(path)
    if raw.empty:
        if not allow_fallback:
            raise ValueError(f"外部方向因子 CSV 为空: {path}")
        fallback = [_normalize_point(p) for p in DEFAULT_AUTHORITY_VIEWPOINTS]
        return fallback, _build_meta("fallback", fallback, path, warning="csv_empty")

    normalized_columns = {col: _COLUMN_RENAME[col.lower()] for col in raw.columns if col.lower() in _COLUMN_RENAME}
    frame = raw.rename(columns=normalized_columns)
    required = {"published_at", "source", "direction_score", "confidence", "half_life_days"}
    missing = [col for col in required if col not in frame.columns]
    if missing:
        msg = f"CSV 缺少必需列: {missing}"
        if not allow_fallback:
            raise ValueError(msg)
        fallback = [_normalize_point(p) for p in DEFAULT_AUTHORITY_VIEWPOINTS]
        return fallback, _build_meta("fallback", fallback, path, warning=msg)

    cleaned = frame[list(required)].copy()
    cleaned["published_at"] = pd.to_datetime(cleaned["published_at"], errors="coerce")
    cleaned["direction_score"] = pd.to_numeric(cleaned["direction_score"], errors="coerce")
    cleaned["confidence"] = pd.to_numeric(cleaned["confidence"], errors="coerce")
    cleaned["half_life_days"] = pd.to_numeric(cleaned["half_life_days"], errors="coerce")
    cleaned["source"] = cleaned["source"].astype(str)
    cleaned = cleaned.dropna().reset_index(drop=True)
    if cleaned.empty:
        msg = "CSV 所有行都无效，已回退到默认观点"
        if not allow_fallback:
            raise ValueError(msg)
        fallback = [_normalize_point(p) for p in DEFAULT_AUTHORITY_VIEWPOINTS]
        return fallback, _build_meta("fallback", fallback, path, warning=msg)

    points = [_normalize_point(row) for row in cleaned.to_dict(orient="records")]
    points = sorted(points, key=lambda x: x["published_at"])
    return points, _build_meta("csv", points, path)


def build_external_direction_features(
    dates: pd.Series,
    csv_path: str | None = None,
    allow_fallback: bool = True,
    return_meta: bool = False,
):
    points, meta = load_external_direction_points(csv_path=csv_path, allow_fallback=allow_fallback)

    date_series = pd.to_datetime(dates).reset_index(drop=True)
    count = len(date_series)
    if count == 0:
        empty = pd.DataFrame(columns=EXTERNAL_DIRECTION_COLUMNS)
        if return_meta:
            return empty, meta
        return empty

    weighted_sum = np.zeros(count, dtype=float)
    weight_total = np.zeros(count, dtype=float)
    weighted_abs_deviation = np.zeros(count, dtype=float)

    for item in points:
        published_at = pd.Timestamp(item["published_at"])
        score = float(item["direction_score"])
        confidence = float(item["confidence"])
        half_life_days = float(item["half_life_days"])

        age_days = (date_series - published_at).dt.days.astype(float).to_numpy()
        active = age_days >= 0
        decay = np.zeros(count, dtype=float)
        decay[active] = np.exp(-age_days[active] / half_life_days)
        weight = confidence * decay

        weighted_sum += weight * score
        weight_total += weight

    level = np.divide(
        weighted_sum,
        weight_total,
        out=np.zeros(count, dtype=float),
        where=weight_total > 1e-12,
    )

    for item in points:
        published_at = pd.Timestamp(item["published_at"])
        score = float(item["direction_score"])
        confidence = float(item["confidence"])
        half_life_days = float(item["half_life_days"])

        age_days = (date_series - published_at).dt.days.astype(float).to_numpy()
        active = age_days >= 0
        decay = np.zeros(count, dtype=float)
        decay[active] = np.exp(-age_days[active] / half_life_days)
        weight = confidence * decay
        weighted_abs_deviation += weight * np.abs(score - level)

    stance_dispersion = np.divide(
        weighted_abs_deviation,
        weight_total,
        out=np.zeros(count, dtype=float),
        where=weight_total > 1e-12,
    )

    direction = pd.Series(level)
    ext_frame = pd.DataFrame(
        {
            "ext_dir_level": direction,
            "ext_dir_ema_5": direction.ewm(span=5, adjust=False).mean(),
            "ext_dir_ema_20": direction.ewm(span=20, adjust=False).mean(),
            "ext_dir_delta_3": direction.diff(3).fillna(0.0),
            "ext_conf_level": np.log1p(weight_total),
            "ext_stance_dispersion": stance_dispersion,
        }
    ).fillna(0.0)

    if return_meta:
        return ext_frame, meta
    return ext_frame
