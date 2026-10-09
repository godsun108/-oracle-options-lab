import unittest
from research.paco_signal_gated_audit import gate

def comparison():
    return {"schema":"paco-premium-comparison-v1","orders_enabled":False,"status":"COMPARABLE","matched_contracts":2,
            "earlier_collection":"2026-10-09T14:00:00+00:00","later_collection":"2026-10-09T15:00:00+00:00",
            "contracts":[{"occ_symbol":"SPY_PUT","earlier_ask":2.5,"later_bid":2.6},{"occ_symbol":"SPY_CALL","earlier_ask":2,"later_bid":3}]}
def signal():
    return {"orders_enabled":False,"status":"CANDIDATES_REQUIRE_HISTORICAL_OPTION_QUOTES","spx_record_close":True,
            "trigger_date":"2026-10-08","history_bars":252,"history_coverage_complete_verified":True,"candidates":[{"symbol":"SPY_PUT"}]}
class SignalGateTests(unittest.TestCase):
    def test_only_selected_candidate(self):
        r=gate(comparison(),signal())
        self.assertEqual(r["eligible_contracts"],1)
        self.assertEqual(r["hypothetical_outcomes"][0]["occ_symbol"],"SPY_PUT")
        self.assertFalse(r["strategy_profitability_proven"])
    def test_no_signal(self):
        s=signal();s["spx_record_close"]=False
        self.assertEqual(gate(comparison(),s)["eligible_contracts"],0)
    def test_no_same_day_lookahead(self):
        s=signal();s["trigger_date"]="2026-10-09"
        self.assertEqual(gate(comparison(),s)["eligible_contracts"],0)
    def test_insufficient_history(self):
        s=signal();s["history_bars"]=251
        self.assertEqual(gate(comparison(),s)["eligible_contracts"],0)

    def test_unverified_historical_coverage_rejected(self):
        s=signal();s["history_coverage_complete_verified"]=False
        self.assertEqual(gate(comparison(),s)["eligible_contracts"],0)
    def test_missing_historical_coverage_rejected(self):
        s=signal();del s["history_coverage_complete_verified"]
        self.assertEqual(gate(comparison(),s)["eligible_contracts"],0)
