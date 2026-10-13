"""Regression coverage for label maturity in both historical batch scorers."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from oracle_q import score_batch_001, score_batch_002


class BatchScorerChronologyTests(unittest.TestCase):
    modules = (score_batch_001, score_batch_002)

    def frame(self):
        dates = pd.date_range("2026-01-01", periods=20)
        return pd.DataFrame({
            "signal_date": dates, "exit_date": dates + pd.Timedelta(days=3),
            "decision_at": dates.tz_localize("UTC"),
            "feature__published_at": (dates - pd.Timedelta(days=1)).tz_localize("UTC"),
            "feature__observed_at": (dates - pd.Timedelta(hours=1)).tz_localize("UTC"),
            "feature": np.arange(20) % 3,
            "option_return": np.where(np.arange(20) % 2, .1, -.1),
            "one_contract_pnl": np.where(np.arange(20) % 2, 10., -10.),
        })

    def test_unavailable_targets_do_not_change_predictions(self):
        frame = self.frame()
        cutoff = frame.signal_date.iloc[12]
        changed = frame.copy()
        mask = changed.exit_date >= cutoff
        changed.loc[mask, ["option_return", "one_contract_pnl"]] *= -7
        for module in self.modules:
            for target in ("win_probability", "expected_return"):
                with self.subTest(module=module.__name__, target=target), patch.object(module, "MIN_TRAIN", 5):
                    before = module.walk(frame, ["feature"], target)
                    after = module.walk(changed, ["feature"], target)
                    # Realized evaluation outcomes may change; predictions must not.
                    columns = ["signal_date", "pred", "n_train"]
                    pd.testing.assert_frame_equal(
                        before.loc[before.signal_date <= cutoff, columns].reset_index(drop=True),
                        after.loc[after.signal_date <= cutoff, columns].reset_index(drop=True))
                    self.assertEqual(int(before.loc[before.signal_date == cutoff, "n_train"].iloc[0]), 9)

    def test_minimum_counts_mature_labels_and_empty_results_are_usable(self):
        frame = self.frame()
        frame["exit_date"] = pd.Timestamp("2027-01-01")
        for module in self.modules:
            with self.subTest(module=module.__name__), patch.object(module, "MIN_TRAIN", 5):
                q = module.walk(frame, ["feature"], "win_probability")
                h = q[pd.to_datetime(q.signal_date).dt.year >= 2022]
                self.assertTrue(h.empty)
                self.assertIn("n_train", h)
                summary = module.econ(h, (lambda z: z.pred > .5) if module is score_batch_001 else "win_probability")
                self.assertEqual(summary, {"trades": 0})

    def test_duplicate_signal_dates_cannot_train_on_each_other(self):
        frame = self.frame()
        duplicate = frame.iloc[[12]].copy()
        duplicate["option_return"] = 123.
        duplicate["one_contract_pnl"] = 12300.
        frame = pd.concat([frame, duplicate], ignore_index=True)
        for module in self.modules:
            with self.subTest(module=module.__name__), patch.object(module, "MIN_TRAIN", 5):
                q = module.walk(frame, ["feature"], "expected_return")
                same = q[q.signal_date == duplicate.signal_date.iloc[0]]
                self.assertEqual(same.n_train.tolist(), [9, 9])
                self.assertEqual(same.pred.nunique(), 1)

    def test_invalid_chronology_fails_even_below_training_minimum(self):
        for module in self.modules:
            frame = self.frame().iloc[:1].copy()
            for bad in (frame.drop(columns="exit_date"), frame.assign(exit_date=pd.NaT),
                        frame.assign(exit_date=pd.Timestamp("2025-01-01"))):
                with self.subTest(module=module.__name__), self.assertRaises(ValueError):
                    module.walk(bad, ["feature"], "win_probability")


if __name__ == "__main__":
    unittest.main()
