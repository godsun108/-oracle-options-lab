import unittest
from research.paco_evidence_readiness import assess

def continuity(n=2):
    return {"schema":"paco-snapshot-continuity-v1","orders_enabled":False,
            "runs_recorded":n,"entries":[{} for _ in range(n)]}

def comparison(same_day):
    return {"schema":"paco-premium-comparison-v1","orders_enabled":False,
            "status":"SAME_DAY_OBSERVATIONAL_ONLY" if same_day else "COMPARABLE",
            "same_utc_day":same_day,"matched_contracts":3}

class ReadinessTests(unittest.TestCase):
    def test_same_day_is_not_cross_day(self):
        result=assess(continuity(23),comparison(True),{"orders_enabled":False})
        self.assertFalse(result["cross_day_quote_pair_observed"])
        self.assertFalse(result["strategy_profitability_proven"])
        self.assertEqual(result["continuity_runs"],23)
    def test_cross_day_does_not_prove_edge(self):
        result=assess(continuity(),comparison(False),{"orders_enabled":False})
        self.assertTrue(result["cross_day_quote_pair_observed"])
        self.assertFalse(result["strategy_profitability_proven"])
        self.assertFalse(result["trade_fills_verified"])
    def test_bad_continuity_fails_closed(self):
        with self.assertRaises(ValueError):
            assess(continuity(3),comparison(False),{"orders_enabled":True})
        with self.assertRaises(ValueError):
            assess({"schema":"paco-snapshot-continuity-v1","orders_enabled":False,
                    "runs_recorded":3,"entries":[{}]},comparison(False),{"orders_enabled":False})
