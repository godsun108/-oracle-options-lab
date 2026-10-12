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

from research.edge_forward_paper import verify

MIN_OUTCOMES_FOR_REVIEW = 60

def _mean(values):
    return round(statistics.fmean(values), 6) if values else None

def score(ledger, *, expected_pairs=None):
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
            "status":("INSUFFICIENT_FORWARD_SAMPLE" if n<MIN_OUTCOMES_FOR_REVIEW
                      else "REVIEW_REQUIRED_NOT_PROVEN"),
            "edge_proven":False, "eligible_for_live_trading":False,
        })
    return {
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
            "Overlapping markets, correlated strategies, regime changes and multiple testing remain unadjusted.",
            "No forward alpha, robust slippage, drawdown distribution, or live profitability is proven."
        ]
    }

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
        if market.get("status")!="HISTORICAL_OPEN_PROXY_BACKTEST_ONLY":
            raise ValueError("invalid market research source")
        expected.extend((market["symbol"],s["strategy_id"]) for s in market["strategies"])
    result=score(ledger,expected_pairs=expected)
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Forward scorecard:",len(result["pairs"]),"pairs,",result["outcomes_total"],"outcomes, no proven edge")

if __name__=="__main__":
    main()
