"""Audit contracts: reject heuristic scores and thin before direction grouping."""
import unittest
import pandas as pd

from evaluate_direction_confidence import direction_audit, evaluate


class EvaluationTests(unittest.TestCase):
    def test_thin_before_direction_filter(self):
        frame = pd.DataFrame({
            "horizon": [2, 2, 2],
            "origin_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "target_date": ["2026-01-03", "2026-01-04", "2026-01-05"],
            "pred_delta": [1, -1, 1], "confidence": [65, 80, 55],
            "direction_match_3class": [True, False, False],
        })
        audit = direction_audit(frame).set_index(["direction", "threshold"])
        self.assertEqual(audit.loc[("all", 0), "n"], 2)
        self.assertEqual(audit.loc[("down", 0), "n"], 0)
        self.assertEqual(audit.loc[("up", 60), "n"], 1)
        self.assertEqual(audit.loc[("all", 0), "accuracy"], .5)
        self.assertEqual(audit.loc[("all", 0), "status"], "insufficient_evidence")

    def test_invalid_and_legacy_probabilities(self):
        frame = pd.DataFrame({"down_probability": [.4], "flat_probability": [.1],
                              "up_probability": [.5],
                              "confidence_method": ["legacy_score_not_probability"]})
        with self.assertRaisesRegex(ValueError, "Legacy"):
            evaluate(frame)
        frame["up_probability"] = .8
        with self.assertRaisesRegex(ValueError, "Invalid"):
            evaluate(frame)


if __name__ == "__main__":
    unittest.main()
