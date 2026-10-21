"""Synthetic-only tests for forward observation admissibility."""
import unittest
from forward_observation_admissibility_v1 import evaluate

def sample():
    return {"schema_version":"oracle-q-forward-evidence-v1",
            "research_only":True,"orders_enabled":False,
            "underlying_source":{"data_cutoff":"2026-10-20",
              "session_policy":"exclude_current_date_before_16:15_ET","raw_sha256":"a"*64},
            "canonical_signal":{"signal_date":"2026-10-20","signal":True},
            "prospective_options":{"status":"OBSERVED","signal_date":"2026-10-20",
              "chain_rows":302,"selected_contract":{"underlying":"SPY",
              "provider":"tradier","bid":2.57,"ask":2.59}}}

class ForwardObservationTests(unittest.TestCase):
    def check(self, data, overrides=None):
        return evaluate({"2026-10-20.json":data},overrides)["records"][0]

    def test_valid_observation_is_not_trade(self):
        row=self.check(sample())
        self.assertTrue(row["observation_admissible"])
        self.assertFalse(row["trade_verified"])
        self.assertFalse(row["realized_pnl_available"])

    def test_rejects_unsafe_orders(self):
        data=sample();data["orders_enabled"]=True
        self.assertIn("unsafe_mode",self.check(data)["reasons"])

    def test_rejects_date_mismatch(self):
        data=sample();data["canonical_signal"]["signal_date"]="2026-10-19"
        self.assertIn("date_mismatch",self.check(data)["reasons"])

    def test_rejects_crossed_quote(self):
        data=sample();data["prospective_options"]["selected_contract"]["bid"]=3.0
        self.assertIn("invalid_quote",self.check(data)["reasons"])

    def test_manual_exclusion(self):
        row=self.check(sample(),{"2026-10-20.json":{"admissible":False,"reason":"partial"}})
        self.assertFalse(row["observation_admissible"])
        self.assertTrue(any(s.startswith("manual_exclusion") for s in row["reasons"]))

    def test_rejects_invalid_hash(self):
        data=sample();data["underlying_source"]["raw_sha256"]="no"
        self.assertIn("invalid_source_hash",self.check(data)["reasons"])

if __name__=="__main__":
    unittest.main()
