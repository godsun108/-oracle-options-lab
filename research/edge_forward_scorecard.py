"""Descriptive scorecard for delayed forward paper observations, never a proven edge.

Uses only tamper-checked recorded observations. Does not optimize, fit or select
strategy parameters. A 60-outcome threshold permits review, not deployment.
"""
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

from research.edge_forward_paper import verify, parse_utc_timestamp
from research.edge_session_calendar import expected_entry_exit, session_bounds, PUBLICATION_BUFFER
from research.edge_forward_uncertainty import assess

MIN_OUTCOMES_FOR_REVIEW = 60

def _mean(values):
    return round(statistics.fmean(values), 6) if values else None

def pending_schedule(events, as_of):
    """Describe maturity, never infer prices, fills, or completed outcomes."""
    stamp = parse_utc_timestamp(as_of)
    closed = {(e["symbol"], e["strategy_id"], e["signal_date"]) for e in events
              if e["type"] in ("PAPER_OUTCOME_OBSERVED", "SIGNAL_EXCLUDED_TIMING")}
    rows = []
    for event in events:
        if event["type"] != "SIGNAL_REGISTERED":
            continue
        key = (event["symbol"], event["strategy_id"], event["signal_date"])
        if key in closed:
            continue
        if "registered_at" not in event:
            rows.append(dict(zip(("symbol", "strategy_id", "signal_date"), key),
                             status="UNVERIFIABLE_REGISTRATION_TIME"))
            continue
        registered = parse_utc_timestamp(event["registered_at"])
        if registered > stamp:
            raise ValueError("schedule snapshot precedes registration")
        entry, exit_day = expected_entry_exit(event["signal_date"], registered)
        entry_at = session_bounds(entry)[0]
        exit_at, close_at = session_bounds(exit_day)
        eligible = close_at + PUBLICATION_BUFFER
        status = ("WAITING_FOR_ENTRY_SESSION" if stamp < entry_at else
                  "WAITING_FOR_EXIT_SESSION" if stamp < exit_at else
                  "WAITING_FOR_DAILY_BAR_ELIGIBILITY" if stamp < eligible else
                  "ELIGIBLE_AWAITING_VALIDATED_DATA_OR_SETTLEMENT")
        rows.append({"symbol":key[0], "strategy_id":key[1], "signal_date":key[2],
                     "entry_session":entry, "exit_session":exit_day,
                     "earliest_data_eligibility_utc":eligible.isoformat(), "status":status})
    return {"as_of":stamp.isoformat(), "pending":rows,
            "warning":"Eligibility is calendar policy, not guaranteed publication or workflow execution; no outcome is inferred."}


def score(ledger, *, expected_pairs=None, as_of=None):
    events = verify(ledger)
    groups = defaultdict(list)
    signals = defaultdict(int)
    exclusions = defaultdict(int)
    registered = set()
    for event in events:
        if event["type"] == "SOURCE_OPEN_CHECKPOINT":
            continue  # Source prices are not trading signals or settled outcomes.
        key = (event["symbol"], event["strategy_id"])
        if event["type"] == "SIGNAL_REGISTERED":
            registered.add(key)
            signals[key] += 1
        elif event["type"] == "PAPER_OUTCOME_OBSERVED":
            groups[key].append(event)
        elif event["type"] == "SIGNAL_EXCLUDED_TIMING":
            exclusions[key] += 1
    if expected_pairs is not None:
        expected = set(tuple(pair) for pair in expected_pairs)
        if registered - expected:
            raise ValueError("unexpected symbol/strategy in forward ledger")
    else:
        expected = registered
    results = []
    for symbol, strategy_id in sorted(expected):
        rows = groups[(symbol, strategy_id)]
        # Older schema outcomes remain valid, but must not be counted as
        # benchmark-verified if they predate the paired benchmark fields.
        returns = []
        benchmark = []
        excess = []
        dates = set()
        for event in rows:
            day = event["signal_date"]
            if day in dates:
                raise ValueError("duplicate outcome date")
            dates.add(day)
            value = event.get("hypothetical_net_return_pct")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise ValueError("invalid paper outcome")
            returns.append(value)
            bench = event.get("hypothetical_buy_hold_return_pct")
            delta = event.get("hypothetical_excess_vs_buy_hold_pct")
            if bench is not None and delta is not None:
                if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (bench, delta)):
                    raise ValueError("invalid paired benchmark")
                if abs((value-bench)-delta)>0.000003:
                    raise ValueError("benchmark excess mismatch")
                benchmark.append(bench)
                excess.append(delta)
        n = len(returns)
        paired = len(excess)
        results.append({
            "symbol":symbol, "strategy_id":strategy_id,
            "signals_registered":signals[(symbol,strategy_id)],
            "outcomes_observed":n,
            "signals_excluded_timing":exclusions[(symbol,strategy_id)],
            "pending":signals[(symbol,strategy_id)]-n-exclusions[(symbol,strategy_id)],
            "paired_benchmark_observations":paired,
            "mean_hypothetical_return_pct":_mean(returns),
            "median_hypothetical_return_pct":round(statistics.median(returns),6) if n else None,
            "positive_observations":sum(v>0 for v in returns),
            "positive_observation_rate":round(sum(v>0 for v in returns)/n,6) if n else None,
            "mean_buy_hold_pct":_mean(benchmark) if paired==n else None,
            "mean_excess_vs_buy_hold_pct":_mean(excess) if paired==n else None,
            "exploratory_uncertainty":assess(excess if paired==n else [],family_size=len(expected),minimum=MIN_OUTCOMES_FOR_REVIEW),
            "status":("INSUFFICIENT_FORWARD_SAMPLE" if n<MIN_OUTCOMES_FOR_REVIEW
                      else "REVIEW_REQUIRED_NOT_PROVEN"),
            "edge_proven":False, "eligible_for_live_trading":False,
        })
    result = {
        "schema":"oracle-q-edge-forward-scorecard-v1",
        "status":"FORWARD_PAPER_RESEARCH_ONLY",
        "minimum_outcomes_for_review":MIN_OUTCOMES_FOR_REVIEW,
        "outcomes_total":sum(row["outcomes_observed"] for row in results),
        "signals_excluded_timing":sum(row["signals_excluded_timing"] for row in results),
        "pairs":results, "orders_enabled":False, "fill_verified":False,
        "edge_proven":False, "eligible_for_live_trading":False,
        "limitations":[
            "Descriptive hypothetical open-to-open observations are not executable fills.",
            "60 observations permits manual review only; it does not establish statistical significance.",
            "An exploratory Bonferroni-adjusted block bootstrap is computed only after 60 paired outcomes; it does not eliminate correlated strategies, regime changes or repeated testing.",
            "No forward alpha, robust slippage, drawdown distribution, or live profitability is proven."
        ]
    }
    if as_of is not None:
        result["maturity"] = pending_schedule(events, as_of)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--ledger",required=True)
    parser.add_argument("--report",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    ledger=json.loads(Path(args.ledger).read_text())
    report=json.loads(Path(args.report).read_text())
    if report.get("schema")!="oracle-q-edge-lab-v1" or report.get("orders_enabled") is not False:
        raise ValueError("invalid research source")
    expected=[]
    for market in report["reports"]:
        if market.get("status") not in ("HISTORICAL_OPEN_PROXY_BACKTEST_ONLY","FORWARD_OPEN_INPUTS_ONLY"):
            raise ValueError("invalid market research source")
        expected.extend((market["symbol"],s["strategy_id"]) for s in market["strategies"])
    result=score(ledger,expected_pairs=expected,as_of=datetime.now(timezone.utc).isoformat())
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Forward scorecard:",len(result["pairs"]),"pairs,",result["outcomes_total"],"outcomes, no proven edge")
    states=defaultdict(int)
    for item in result["maturity"]["pending"]:
        states[item["status"]]+=1
    print("Forward maturity:",json.dumps(dict(states),sort_keys=True))

if __name__=="__main__":
    main()
