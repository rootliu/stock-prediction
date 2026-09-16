"""Offline regression tests for directional probability semantics."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml-service"))
from models.direction_confidence import (
    calibration_rows, maturity_calibration_rows, direction_label, directional_confidence, fit_calibration,
)


class ConfidenceTests(unittest.TestCase):
    def test_maturity_handles_missing_samples(self):
        origins = pd.Series(pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-07", "2026-01-08"]))
        targets = pd.Series(pd.to_datetime(["2026-01-07", "2026-01-08", "2026-01-12", "2026-01-13"]))
        self.assertEqual(maturity_calibration_rows(origins, targets, 0).tolist(), [0, 2])

    def test_invalid_probability_rejected(self):
        self.assertEqual(len(fit_calibration([-1, 2], [1, -1])["raw_up"]), 0)
        with self.assertRaises(ValueError):
            fit_calibration([.5, .6], [1])
        self.assertIn("missing_classifier", directional_confidence({}, 2, "涨")["confidence_reasons"])

    def test_purge_and_nonoverlap(self):
        for horizon in range(1, 11):
            indices = calibration_rows(240, 192, horizon)
            self.assertTrue(np.all(indices > 191 + horizon))
            self.assertTrue(np.all(np.diff(indices) >= horizon))

    def test_sum_and_direction_correspondence(self):
        cal = fit_calibration([0.9] * 30, [4] * 24 + [-4] * 6)
        for direction, field in [("涨", "up_probability"), ("跌", "down_probability"), ("平", "flat_probability")]:
            result = directional_confidence(cal, 0.9, direction)
            self.assertAlmostEqual(sum(result[k] for k in ("up_probability", "down_probability", "flat_probability")), 1)
            self.assertEqual(result["confidence"], round(result[field] * 100, 1))
            self.assertLess(result["confidence_low"], result["confidence_high"])
        self.assertEqual(directional_confidence(cal, 0.9, "跌")["direction_signal"], "watch")

    def test_scarcity_and_missing(self):
        for cal, raw in [(fit_calibration([], []), 0.99), (fit_calibration([0.99], [5]), 0.99), ({}, None)]:
            result = directional_confidence(cal, raw, "涨")
            self.assertEqual(result["direction_signal"], "watch")
            self.assertLess(result["confidence"], 60)

    def test_flat_threshold_and_invalid_values(self):
        self.assertEqual([direction_label(x) for x in [-0.51, -0.5, 0.5, 0.51]], ["跌", "平", "平", "涨"])
        cal = fit_calibration([0.5, np.nan, 0.5], [0.5, 1, np.inf])
        result = directional_confidence(cal, 0.5, "平")
        self.assertEqual(result["calibration_count"], 1)


if __name__ == "__main__":
    unittest.main()
