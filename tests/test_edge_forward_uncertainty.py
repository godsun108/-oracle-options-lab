import unittest
from research.edge_forward_uncertainty import assess

class UncertaintyTests(unittest.TestCase):
    def test_insufficient_sample_is_not_estimated(self):
        result=assess([0.5]*59,family_size=18)
        self.assertEqual(result["statistical_evidence"],"NOT_ESTIMABLE")
        self.assertIsNone(result["bonferroni_adjusted_p"])
        self.assertFalse(result["statistically_confirmed_edge"])
    def test_flat_excess_never_passes(self):
        result=assess([0.0]*60,family_size=18)
        self.assertEqual(result["bonferroni_adjusted_p"],1)
        self.assertEqual(result["bootstrap_mean_excess_95pct_interval"],[0.0,0.0])
        self.assertFalse(result["eligible_for_live_trading"])
    def test_reproducible_adjustment_not_proof(self):
        values=[0.8 if i%5 else -0.4 for i in range(75)]
        first=assess(values,family_size=18)
        self.assertEqual(first,assess(values,family_size=18))
        self.assertGreaterEqual(first["bonferroni_adjusted_p"],first["raw_one_sided_p"])
        self.assertEqual(first["statistical_evidence"],"EXPLORATORY_UNCERTAINTY_ESTIMATE_ONLY")
        self.assertFalse(first["statistically_confirmed_edge"])
    def test_bad_values_rejected(self):
        with self.assertRaises(ValueError):
            assess([float("nan")]*60,family_size=18)
        with self.assertRaises(ValueError):
            assess([1.0]*60,family_size=0)

if __name__=="__main__":
    unittest.main()
