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
from research.edge_lab import IDS
from research.multi_market_observer import SYMBOLS
from research.edge_regime_context import validate as validate_regime

MIN_OUTCOMES_FOR_REVIEW = 60

def _mean(values):
    return round(statistics.fmean(values), 6) if values else None

def regime_coverage(events, pair):
    """Coverage only, from original registration context; no hindsight labels."""
    labels = [direction+'/'+vol for direction in ('UP_OR_FLAT','DOWN')
              for vol in ('LOW_VOL','HIGH_VOL')] + ['UNCLASSIFIED']
    buckets = {label: {'regime':label, 'valid_signals':0, 'completed_observations':0,
                       'pending':0} for label in labels}
    signals = {}
    excluded = set()
    outcomes = set()
    for event in events:
        if (event.get('symbol'),event.get('strategy_id')) != pair:
            continue
        day = event['signal_date']
        kind = event['type']
        if kind == 'SIGNAL_REGISTERED':
            if day in signals:
                raise ValueError('duplicate regime registration')
            signals[day] = event
        elif kind == 'SIGNAL_EXCLUDED_TIMING':
            excluded.add(day)
        elif kind == 'PAPER_OUTCOME_OBSERVED':
            outcomes.add(day)
    for day,event in signals.items():
        if day in excluded or 'registered_at' not in event:
            continue
        label = 'UNCLASSIFIED'
        if 'regime_context' in event:
            validate_regime(event['regime_context'],day)
            label = event['regime_context']['label']
        bucket = buckets[label]
        bucket['valid_signals'] += 1
        bucket['completed_observations'] += int(day in outcomes)
        bucket['pending'] += int(day not in outcomes)
    for bucket in buckets.values():
        bucket['status'] = ('DESCRIPTIVE_COVERAGE_ONLY' if bucket['completed_observations']
                            else 'NO_COMPLETED_FORWARD_EVIDENCE')
    return list(buckets.values())

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
            "regime_coverage":regime_coverage(events,(symbol,strategy_id)),
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
        "distinct_outcome_exit_sessions":len({e['exit_date'] for e in events if e['type']=='PAPER_OUTCOME_OBSERVED'}),
        "signals_excluded_timing":sum(row["signals_excluded_timing"] for row in results),
        "pairs":results, "orders_enabled":False, "fill_verified":False,
        "edge_proven":False, "eligible_for_live_trading":False,
        "limitations":[
            "Regime buckets report coverage only, not profitability or significance; older labels are never inferred. Regime-specific inference needs its own multiple-testing plan.",
            "Outcomes across markets and strategies can share the same session and are not independent samples. Distinct sessions are not an effective sample size estimate.",
            "Descriptive hypothetical open-to-open observations are not executable fills.",
            "60 observations permits manual review only; it does not establish statistical significance.",
            "An exploratory Bonferroni-adjusted block bootstrap is computed only after 60 paired outcomes; it does not eliminate correlated strategies, regime changes or repeated testing.",
            "No forward alpha, robust slippage, drawdown distribution, or live profitability is proven."
        ]
    }
    if as_of is not None:
        result["maturity"] = pending_schedule(events, as_of)
    return result

def score_report(ledger, report, *, as_of, allow_partial=False):
    if report.get("schema")!="oracle-q-edge-lab-v1" or report.get("orders_enabled") is not False:
        raise ValueError("invalid research source")
    expected=[]
    blocked=[]
    if sorted(m["symbol"] for m in report["reports"])!=sorted(SYMBOLS):
        raise ValueError("scorecard requires complete market coverage")
    for market in report["reports"]:
        if allow_partial and report.get("collection_mode")=="forward" and market.get("status")=="DATA_OR_VALIDATION_FAILURE":
            blocked.append(market["symbol"])
            expected.extend((market["symbol"],sid) for sid in IDS)
            continue
        if market.get("status") not in ("HISTORICAL_OPEN_PROXY_BACKTEST_ONLY","FORWARD_OPEN_INPUTS_ONLY"):
            raise ValueError("invalid market research source")
        if sorted(s["strategy_id"] for s in market["strategies"])!=sorted(IDS):
            raise ValueError("scorecard requires complete strategy coverage")
        expected.extend((market["symbol"],sid) for sid in IDS)
    if len(blocked)==len(SYMBOLS):
        raise ValueError("no validated markets")
    result=score(ledger,expected_pairs=expected,as_of=as_of)
    result["blocked_markets"]=blocked
    result["collection_health"]="PARTIAL_MARKET_DATA" if blocked else "ALL_MARKETS_VALIDATED"
    for pair in result["pairs"]:
        pair["current_market_data_status"]="BLOCKED" if pair["symbol"] in blocked else "VALIDATED"
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--ledger",required=True)
    parser.add_argument("--report",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--allow-partial",action="store_true")
    args=parser.parse_args()
    ledger=json.loads(Path(args.ledger).read_text())
    report=json.loads(Path(args.report).read_text())
    result=score_report(ledger,report,as_of=datetime.now(timezone.utc).isoformat(),allow_partial=args.allow_partial)
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Forward scorecard:",len(result["pairs"]),"pairs,",result["outcomes_total"],"outcomes, no proven edge")
    states=defaultdict(int)
    for item in result["maturity"]["pending"]:
        states[item["status"]]+=1
    print("Forward maturity:",json.dumps(dict(states),sort_keys=True))
    print("Collection health:",result["collection_health"],"blocked:",result["blocked_markets"])
    classified=sum(b['completed_observations'] for p in result['pairs'] for b in p['regime_coverage'] if b['regime']!='UNCLASSIFIED')
    print("Regime coverage:",classified,"classified outcomes; distinct exit sessions:",result['distinct_outcome_exit_sessions'],"; no regime profitability established")

if __name__=="__main__":
    main()
