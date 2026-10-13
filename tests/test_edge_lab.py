import json
import unittest
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from research.edge_lab import signal, segment, evaluate, run, diagnose_raw_bars, validate_open_bars
from research.edge_lab import fetch_with_transport_retries
from research.edge_lab import evaluate_forward, forward_start

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
    def test_forward_window_preserves_every_strategy_signal(self):
        raw=bars(420)
        historical=evaluate("SPY",raw,REGISTRY,now=NOW)
        forward=evaluate_forward("SPY",raw[-200:],REGISTRY,now=NOW)
        self.assertEqual(forward["bars"],200)
        self.assertNotIn("holdout_start",forward)
        self.assertEqual(forward_start(NOW.date()),raw[-200]["date"])
        self.assertEqual([x["next_session_paper_signal"] for x in historical["strategies"]],
                         [x["next_session_paper_signal"] for x in forward["strategies"]])
        # Also compare declining and oscillating inputs, not only an uptrend.
        for prices in ([500-i for i in range(420)],[100+i%11 for i in range(420)]):
            for row,price in zip(raw,prices):row["open"]=price
            h=evaluate("SPY",raw,REGISTRY,now=NOW)
            f=evaluate_forward("SPY",raw[-200:],REGISTRY,now=NOW)
            self.assertEqual([x["next_session_paper_signal"] for x in h["strategies"]],
                             [x["next_session_paper_signal"] for x in f["strategies"]])

    def test_forward_window_is_chosen_before_fetch_and_replayed(self):
        from research.edge_source_replay import audit
        calls=[];raw=bars(200)
        def fetch(*args):calls.append(args);return raw
        result=run(REGISTRY,"token",fetch=fetch,now=NOW,mode="forward")
        self.assertTrue(all(x[2:]==(raw[0]["date"],raw[-1]["date"]) for x in calls))
        self.assertEqual(audit(result,REGISTRY)["status"],"SOURCE_REPLAY_MATCHED")

    def test_forward_missing_invalid_extra_or_stale_bars_fail_closed(self):
        import copy
        raw=bars(200)
        invalid=copy.deepcopy(raw);invalid[10]["open"]="NaN"
        for bad in (invalid,raw[1:],raw[:-1],bars(201),raw+[raw[-1]]):
            with self.assertRaises(ValueError):evaluate_forward("SPY",bad,REGISTRY,now=NOW)

    def test_old_defect_still_blocks_historical_mode(self):
        raw=bars(420);raw[0]["open"]="NaN"
        with self.assertRaises(ValueError):evaluate("SPY",raw,REGISTRY,now=NOW)
        # Separate inputs, not an automatic retry/fallback after that failure.
        self.assertEqual(evaluate_forward("SPY",raw[-200:],REGISTRY,now=NOW)["status"],"FORWARD_OPEN_INPUTS_ONLY")

    def test_forward_mode_preserves_existing_ledger_on_same_session(self):
        from research.edge_forward_paper import advance
        current={"schema":"oracle-q-edge-lab-v1","orders_enabled":False,"edge_proven":False,
                 "observed_at":NOW.isoformat(),"reports":[evaluate("SPY",bars(420),REGISTRY,now=NOW)]}
        prior=advance(None,current)
        current["reports"]=[evaluate_forward("SPY",bars(420)[-200:],REGISTRY,now=NOW)]
        after=advance(prior,current)
        self.assertEqual(prior["events"],after["events"])
        self.assertEqual(prior["head_sha256"],after["head_sha256"])

    def test_transport_retries_are_bounded_and_recorded(self):
        trace=[]; delays=[]; calls=[]
        def fetch():
            calls.append(1)
            if len(calls)<3:raise TimeoutError("SECRET must never appear")
            return [{"open":100}]
        self.assertEqual(fetch_with_transport_retries(fetch,(),trace,sleep=delays.append),[{"open":100}])
        self.assertEqual(delays,[1,2]);self.assertEqual(len(trace),3)
        self.assertNotIn("SECRET",str(trace))
        self.assertEqual(trace[-1]["status"],"RESPONSE_RECEIVED")
        trace=[]
        def fail():raise TimeoutError("never ready")
        with self.assertRaises(TimeoutError):fetch_with_transport_retries(fail,(),trace,sleep=lambda _:None)
        self.assertEqual(len(trace),3);self.assertFalse(trace[-1]["retry_scheduled"])

    def test_auth_rate_limits_and_invalid_responses_are_not_retried(self):
        for exc in [urllib.error.HTTPError("hidden",code,"hidden",{},None) for code in (401,403,429,404)]+[ValueError("invalid JSON")]:
            trace=[]
            def fail():raise exc
            with self.subTest(exc=type(exc).__name__),self.assertRaises(type(exc)):
                fetch_with_transport_retries(fail,(),trace,sleep=lambda _:self.fail("unexpected retry"))
            self.assertEqual(len(trace),1)
        trace=[]
        rows=[{"open":"NaN"}]
        self.assertIs(fetch_with_transport_retries(lambda:rows,(),trace),rows)
        self.assertEqual(len(trace),1)

    def test_only_allowlisted_gateway_statuses_retry(self):
        for code in (502,503,504):
            trace=[]
            def fail():raise urllib.error.HTTPError("hidden",code,"hidden",{},None)
            with self.assertRaises(urllib.error.HTTPError):
                fetch_with_transport_retries(fail,(),trace,sleep=lambda _:None)
            self.assertEqual(len(trace),3)
            self.assertTrue(all(x["http_status"]==code for x in trace))

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
