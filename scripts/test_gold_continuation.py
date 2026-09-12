"""Regression checks for continuation alignment and invocation-local caching."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import run_gold_continuation_backtest as backtest
from models import multi_day_direct_predictor as model


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        dates = pd.bdate_range("2025-01-01", periods=75)
        close = 600 + np.arange(75) + np.sin(np.arange(75)) * 4
        self.daily = pd.DataFrame({"date": dates, "close": close,
                                   "open": close - 1, "high": close + 3,
                                   "low": close - 3, "volume": 1000})
        self.empty = pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]")})

    def test_cached_training_inputs_equal_uncached(self):
        cache = {}
        with patch.object(model, "_build_direct_feature_row",
                          wraps=model._build_direct_feature_row) as build:
            for horizon in (1, 3, 10):
                args = (self.daily, self.empty, self.empty, self.empty, horizon, 30)
                expected = model._build_training_dataset(*args)
                before = build.call_count
                actual = model._build_training_dataset(*args, feature_cache=cache)
                calls = build.call_count - before
                for left, right in zip(expected, actual):
                    if isinstance(left, pd.DataFrame):
                        pd.testing.assert_frame_equal(left, right)
                    else:
                        pd.testing.assert_series_equal(left, right)
                self.assertLessEqual(calls, 30 if horizon == 1 else horizon)

    def test_missing_prediction_keeps_original_horizon(self):
        cutoff = self.daily.date.iloc[-3]

        def predict(**kwargs):
            dates = kwargs["target_dates"]
            self.assertTrue(all(dates[h - 1] > cutoff
                                for h in kwargs["horizons_to_train"]))
            # Simulate an untrained T+1 model; only T+2 is returned.
            if len(dates) < 2 or 2 not in kwargs["horizons_to_train"]:
                return []
            return [{"date": str(dates[1].date()), "close": 650,
                     "model_details": {"horizon_days": 2}}]

        with patch.object(backtest, "run_direct_multi_day_prediction", side_effect=predict):
            result = backtest._build_records(self.daily, self.empty, self.empty,
                                            self.empty, cutoff, 30, 3)
        self.assertTrue((result.horizon == 2).all())
        self.assertEqual(len(result), 2)
        self.assertEqual(result.target_date.iloc[-1], str(self.daily.date.iloc[-1].date()))


if __name__ == "__main__":
    unittest.main()
