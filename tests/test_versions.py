import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-service"))
sys.path.insert(0, str(ROOT / "scripts"))

from models.versions import VERSIONS, predict_close  # noqa: E402
import bench_versions as bench  # noqa: E402


def test_persistence_ignores_the_model_entirely():
    assert predict_close("v0", 900.0, 0.05, 5) == 900.0
    assert predict_close("v0", 900.0, -0.20, 1) == 900.0


def test_shrink_never_increases_distance_from_origin():
    origin, ret = 900.0, 0.04
    for horizon in (1, 3, 5, 10):
        raw = predict_close("v1", origin, ret, horizon)
        shrunk = predict_close("v7", origin, ret, horizon)
        assert abs(shrunk - origin) <= abs(raw - origin) + 1e-9


def test_v7_uses_nearest_anchor_for_unlisted_horizon():
    # horizon 2 must resolve to the T+3 anchor, not to the T+10 one.
    assert VERSIONS["v7"].shrink(2) == VERSIONS["v7"].shrink(3) == 0.25
    assert VERSIONS["v7"].shrink(10) == 0.10
    assert VERSIONS["v7"].shrink(30) == 0.10


def test_unknown_version_is_loud():
    with pytest.raises(KeyError):
        predict_close("v99", 900.0, 0.01, 1)


def _board(skill_by_version: dict[str, float], coverage: float = 0.80) -> pd.DataFrame:
    rows = []
    for name, skill in skill_by_version.items():
        for horizon in (1, 3, 5, 10):
            rows.append(
                {
                    "version": name,
                    "horizon": horizon,
                    "n": 69,
                    "skill": skill,
                    "coverage": coverage,
                    "direction_ci_low": 48.0,
                }
            )
    return pd.DataFrame(rows)


def test_every_version_below_the_band_falls_back_to_persistence():
    verdict = bench.select_champion(_board({"v0": 0.0, "v1": -0.09, "v7": -0.05}))
    assert verdict["champion"] == "v0"
    assert verdict["reason"] == "all_models_negative"


def test_near_baseline_version_is_allowed_as_least_worse():
    # -0.013 is inside the -0.02 tolerance: informative but not materially worse.
    verdict = bench.select_champion(_board({"v0": 0.0, "v1": -0.09, "v7": -0.013}))
    assert verdict["champion"] == "v7"
    assert verdict["directional_edge"] is False


def test_positive_version_wins_over_the_rest():
    verdict = bench.select_champion(_board({"v0": 0.0, "v4": 0.01, "v7": 0.03}))
    assert verdict["champion"] == "v7"
    assert verdict["directional_edge"] is False  # 48% CI low < 50% is disclosed


def test_bad_coverage_disqualifies_an_otherwise_good_version():
    verdict = bench.select_champion(_board({"v0": 0.0, "v7": 0.03}, coverage=0.50))
    assert verdict["champion"] == "v0"


def test_rolling_skill_is_one_when_forecast_equals_actual():
    history = pd.DataFrame(
        {
            "origin_date": pd.to_datetime(["2026-01-05"] * 3),
            "target_date": pd.to_datetime(["2026-01-06"] * 3),
            "horizon": [1, 3, 5],
            "origin_close": [900.0, 900.0, 900.0],
            "pred_close": [905.0, 910.0, 915.0],
            "actual_close": [905.0, 910.0, 915.0],
        }
    )
    import gold_daily

    assert gold_daily.rolling_skill(history, "v1") == pytest.approx(1.0)