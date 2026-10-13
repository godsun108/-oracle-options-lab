import unittest
import pandas as pd
from oracle_q.feature_timing import FeatureTimingError, validate_feature_timing
from oracle_q import score_batch_001, score_batch_002


class FeatureTimingTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({"decision_at": ["2026-10-13T09:30:00-04:00"], "x": [1.],
                             "x__published_at": ["2026-10-13T13:29:00Z"],
                             "x__observed_at": ["2026-10-13T13:29:59Z"]})

    def test_explicit_offsets_compare_in_utc(self):
        validate_feature_timing(self.frame(), ["x"])

    def test_late_or_same_instant_receipt_and_reversed_publication_rejected(self):
        for published, observed in [("13:29:00", "13:30:00"), ("13:29:00", "13:31:00"),
                                    ("13:29:59", "13:29:58")]:
            frame = self.frame()
            frame["x__published_at"] = f"2026-10-13T{published}Z"
            frame["x__observed_at"] = f"2026-10-13T{observed}Z"
            with self.subTest(observed=observed), self.assertRaises(FeatureTimingError):
                validate_feature_timing(frame, ["x"])

    def test_unknown_dates_never_become_midnight_evidence(self):
        for field in ("decision_at", "x__published_at", "x__observed_at"):
            for value in (None, pd.NaT, "2026-10-13", "2026-10-13T13:00:00", 0, "bad"):
                with self.subTest(field=field, value=value), self.assertRaises(FeatureTimingError):
                    validate_feature_timing(self.frame().assign(**{field: value}), ["x"])

    def test_decision_cannot_be_shifted_to_a_later_day_to_admit_late_features(self):
        with self.assertRaisesRegex(FeatureTimingError, "must match"):
            validate_feature_timing(self.frame().assign(signal_date="2026-10-12"), ["x"], "signal_date")

    def test_every_selected_feature_requires_evidence(self):
        for column in self.frame().columns:
            with self.subTest(column=column), self.assertRaises(FeatureTimingError):
                validate_feature_timing(self.frame().drop(columns=column), ["x"])
        with self.assertRaises(FeatureTimingError):
            validate_feature_timing(self.frame().assign(y=2), ["x", "y"])

    def test_both_scorers_block_legacy_inputs_before_model_training(self):
        for module in (score_batch_001, score_batch_002):
            with self.subTest(module=module.__name__), self.assertRaisesRegex(FeatureTimingError, "missing feature timing evidence"):
                module.walk(pd.DataFrame({"signal_date": ["2026-10-13"], "x": [1]}), ["x"], "win_probability")


if __name__ == "__main__":
    unittest.main()
