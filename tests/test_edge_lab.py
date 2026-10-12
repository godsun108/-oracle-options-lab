import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from research.edge_lab import signal, segment, evaluate, run, diagnose_raw_bars, validate_open_bars

from research.edge_session_calendar import is_session

REGISTRY=json.loads(Path("research/edge_registry.json").read_text())
NOW=datetime(2026,10,12,22,0,tzinfo=timezone.utc)

def bars(n=420):
    sessions=[]
    day=NOW
    while len(sessions)<n:
        if is_session(day.date()):
            sessions.append(day.date().isoformat())
        day-=timedelta(days=1)
    return [{"date":day,"open":100+i*.15,"high":101+i*.15,
             "low":99+i*.15,"close":100.05+i*.15}
            for i,day in enumerate(reversed(sessions))]

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
        self.assertEqual(result["status"],"HISTORICAL_OPEN_PROXY_BACKTEST_ONLY")
        self.assertEqual(len(result["strategies"]),3)
        self.assertFalse(result["forward_paper_verified"])
        self.assertFalse(result["edge_proven"])
        self.assertLess(result["train_start"],result["holdout_start"])
        self.assertLess(result["holdout_start"],result["holdout_end"])
        self.assertEqual(len(result["open_series_sha256"]),64)
        self.assertEqual(result["price_field"],"open_only")
    def test_insufficient_history_fails_closed(self):
        r=evaluate("SPY",bars(250),REGISTRY,now=NOW)
        self.assertEqual(r["status"],"INSUFFICIENT_COMPLETED_BARS")
    def test_no_data_not_marked_as_edge(self):
        r=run(REGISTRY,"read-only-token",fetch=lambda *args:[],now=NOW)
        self.assertTrue(all(x["status"]=="INSUFFICIENT_COMPLETED_BARS" for x in r["reports"]))
        self.assertFalse(r["edge_proven"])
    def test_inconsistent_ohlc_identified_without_repair(self):
        raw=bars(330)
        raw[12]["close"]=raw[12]["high"]+5
        d=diagnose_raw_bars(raw,now=NOW)
        self.assertEqual(d["reason"],"INCONSISTENT_OHLC")
        r=run(REGISTRY,"token",fetch=lambda *args:raw,now=NOW)
        self.assertEqual(r["reports"][0]["status"],"HISTORICAL_OPEN_PROXY_BACKTEST_ONLY")
        self.assertEqual(r["reports"][0]["price_field"],"open_only")
        self.assertFalse(r["edge_proven"])
    def test_invalid_open_still_blocks_market(self):
        raw=bars(330)
        raw[12]["open"]=float("nan")
        self.assertRaises(ValueError,validate_open_bars,raw,now=NOW)
        r=run(REGISTRY,"token",fetch=lambda *args:raw,now=NOW)
        self.assertTrue(all(x["status"]=="DATA_OR_VALIDATION_FAILURE" for x in r["reports"]))
        self.assertFalse(r["edge_proven"])
    def test_unregistered_symbol_rejected(self):
        with self.assertRaises(ValueError):
            evaluate("BTCUSD",bars(),REGISTRY,now=NOW)

if __name__=="__main__":
    unittest.main()
