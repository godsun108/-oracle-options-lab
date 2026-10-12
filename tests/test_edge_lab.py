import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from research.edge_lab import signal, segment, evaluate, run

REGISTRY=json.loads(Path("research/edge_registry.json").read_text())
NOW=datetime(2026,10,12,22,0,tzinfo=timezone.utc)

def bars(n=420):
    start=datetime(2025,1,1,tzinfo=timezone.utc)
    out=[]
    day=start
    while len(out)<n:
        if day.weekday()<5:
            v=100+len(out)*0.15
            out.append({"date":day.date().isoformat(),"open":v,"high":v+1,
                        "low":v-1,"close":v+0.05})
        day+=timedelta(days=1)
    return out

class EdgeLabTests(unittest.TestCase):
    def test_signals_use_prior_completed_closes(self):
        c=[100+i for i in range(220)]
        self.assertEqual(signal("tsmom_63",c),1)
        self.assertEqual(signal("trend_200",c),1)
        self.assertEqual(signal("reversal_5",c),0)
    def test_costs_charged_without_price_movement(self):
        flat=[{"open":100.0,"close":100.0} for _ in range(203)]
        r=segment(flat,"trend_200",200,202,benchmark=True)
        self.assertEqual(r["position_changes"],2)
        self.assertLess(r["net_return_pct"],0)
    def test_historical_holdout_never_proves_edge(self):
        result=evaluate("SPY",bars(),REGISTRY,now=NOW)
        self.assertEqual(result["status"],"HISTORICAL_PROXY_BACKTEST_ONLY")
        self.assertEqual(len(result["strategies"]),3)
        self.assertFalse(result["forward_paper_verified"])
        self.assertFalse(result["edge_proven"])
        self.assertLess(result["train_start"],result["holdout_start"])
        self.assertLess(result["holdout_start"],result["holdout_end"])
        self.assertEqual(len(result["ohlc_sha256"]),64)
    def test_insufficient_history_fails_closed(self):
        r=evaluate("SPY",bars(250),REGISTRY,now=NOW)
        self.assertEqual(r["status"],"INSUFFICIENT_COMPLETED_BARS")
    def test_no_data_not_marked_as_edge(self):
        r=run(REGISTRY,"read-only-token",fetch=lambda *args:[],now=NOW)
        self.assertTrue(all(x["status"]=="INSUFFICIENT_COMPLETED_BARS" for x in r["reports"]))
        self.assertFalse(r["edge_proven"])
    def test_unregistered_symbol_rejected(self):
        with self.assertRaises(ValueError):
            evaluate("BTCUSD",bars(),REGISTRY,now=NOW)

if __name__=="__main__":
    unittest.main()
