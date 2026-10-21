import unittest
from datetime import datetime,timedelta,timezone
from forex_quant_research_v1 import evaluate,PAIRS

def bars():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    return [{"timestamp":(start+timedelta(hours=i)).isoformat(),"mid":1.1+i*0.0001} for i in range(61)]

class FxResearchTests(unittest.TestCase):
    def test_all_seven_pairs_are_research_only(self):
        for pair in PAIRS:
            result=evaluate(pair,bars(),spread_bps=1.5)
            self.assertFalse(result["ordersEnabled"])
            self.assertFalse(result["edgeProven"])
            self.assertFalse(result["realizedPnlAvailable"])
            self.assertEqual(len(result["strategies"]),3)
    def test_trend_on_increasing_prices(self):
        self.assertEqual(evaluate("EURUSD",bars(),spread_bps=2)["strategies"]["trend_20_60"],"LONG")
    def test_rejects_duplicate_timestamps(self):
        b=bars();b[-1]["timestamp"]=b[-2]["timestamp"]
        with self.assertRaisesRegex(ValueError,"nonchronological"):evaluate("EURUSD",b,spread_bps=2)
    def test_rejects_missing_history(self):
        with self.assertRaisesRegex(ValueError,"61"):evaluate("EURUSD",bars()[:10],spread_bps=2)
    def test_rejects_invalid_cost(self):
        with self.assertRaisesRegex(ValueError,"spread"):evaluate("EURUSD",bars(),spread_bps=-1)
    def test_rejects_unrecognized_pair(self):
        with self.assertRaisesRegex(ValueError,"unsupported"):evaluate("BTCUSD",bars(),spread_bps=2)

if __name__=="__main__":unittest.main()
