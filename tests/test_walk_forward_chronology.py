import unittest
import numpy as np
import pandas as pd

from oracle_q.walk_forward import available_training_rows, walk_forward_predict


class TrainingChronologyTests(unittest.TestCase):
    def test_same_day_and_unsettled_labels_are_excluded(self):
        rows = pd.DataFrame({"date": ["2026-10-01", "2026-10-02", "2026-10-05", "2026-10-05"],
                             "exit_date": ["2026-10-02", "2026-10-06", "2026-10-05", "2026-10-07"]})
        selected = available_training_rows(rows, "2026-10-05")
        self.assertEqual(selected.index.tolist(), [0])

    def test_missing_or_impossible_availability_fails_closed(self):
        for rows in ({"date": ["2026-10-05"]},
                     {"date": ["2026-10-05"], "exit_date": [None]},
                     {"date": ["2026-10-05"], "exit_date": ["2026-10-04"]}):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                available_training_rows(pd.DataFrame(rows), "2026-10-06")

    def test_unknown_future_targets_cannot_change_earlier_predictions(self):
        dates = pd.date_range("2026-01-01", periods=20, tz="UTC")
        frame = pd.DataFrame({"date": dates, "exit_date": dates + pd.Timedelta(days=3),
                              "feature": np.arange(20) % 3, "target": np.arange(20) % 2})
        baseline = walk_forward_predict(frame, ["feature"], "target", min_train=5)
        cutoff = dates[12]
        changed = frame.copy()
        mask = changed.exit_date >= cutoff
        changed.loc[mask, "target"] = 1 - changed.loc[mask, "target"]
        result = walk_forward_predict(changed, ["feature"], "target", min_train=5)
        before = baseline[baseline.date <= cutoff].reset_index(drop=True)
        after = result[result.date <= cutoff].reset_index(drop=True)
        pd.testing.assert_frame_equal(before, after)
        self.assertEqual(int(baseline.loc[baseline.date == cutoff, "n_train"].iloc[0]), 9)

    def test_no_mature_labels_returns_typed_empty_result(self):
        frame = pd.DataFrame({"date": ["2026-10-05"], "exit_date": ["2026-10-06"],
                              "feature": [1], "target": [1]})
        result = walk_forward_predict(frame, ["feature"], "target", min_train=1)
        self.assertTrue(result.empty)
        self.assertIn("p_model", result.columns)


if __name__ == "__main__":
    unittest.main()
