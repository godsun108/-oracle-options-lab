"""Fixed hypothetical cost stresses on audited observations; never fill evidence."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from research.edge_forward_integrity_audit import audit

# Total assumed spread/slippage/fee drag per side, not measured market quotes.
COSTS_BPS = (0, 10, 25, 50)


def summarize(ledger):
    audit(ledger)
    opens = {}
    signals = {}
    outcomes = defaultdict(list)
    pairs = set()
    for event in ledger["events"]:
        kind = event["type"]
        if kind == "SOURCE_OPEN_CHECKPOINT":
            opens[(event["symbol"], event["open_date"])] = event["open_price"]
        elif kind == "SIGNAL_REGISTERED":
            pair = (event["symbol"], event["strategy_id"])
            pairs.add(pair)
            signals[(*pair, event["signal_date"])] = event["signal"]
        elif kind == "PAPER_OUTCOME_OBSERVED":
            outcomes[(event["symbol"], event["strategy_id"])].append(event)
    rows = []
    for pair in sorted(pairs):
        samples = []
        for event in outcomes[pair]:
            gross = 100 * (opens[(pair[0], event["exit_date"])] /
                           opens[(pair[0], event["entry_date"])] - 1)
            direction = signals[(*pair, event["signal_date"])]
            samples.append((gross, direction))
        scenarios = []
        for cost in COSTS_BPS:
            net = [direction * (gross - 2 * cost / 100) for gross, direction in samples]
            benchmark = [gross - 2 * cost / 100 for gross, _ in samples]
            active_net = [gross - 2 * cost / 100 for gross, direction in samples if direction]
            gross_benchmark = [gross for gross, _ in samples]
            scenarios.append({
                "assumed_total_cost_per_side_bps": cost,
                "mean_net_return_pct": round(statistics.fmean(net), 6) if net else None,
                "mean_paired_benchmark_pct": round(statistics.fmean(benchmark), 6) if net else None,
                "mean_excess_pct": round(statistics.fmean(a-b for a,b in zip(net, benchmark)), 6) if net else None,
                "positive_observations": sum(v > 0 for v in net) if net else None,
                "mean_excess_vs_zero_yield_cash_pct": round(statistics.fmean(net), 6) if net else None,
                "mean_cost_free_market_return_pct": round(statistics.fmean(gross_benchmark), 6) if net else None,
                "mean_excess_vs_cost_free_market_pct": round(statistics.fmean(a-b for a,b in zip(net, gross_benchmark)), 6) if net else None,
                "mean_invested_net_return_pct": round(statistics.fmean(active_net), 6) if active_net else None,
                "worst_invested_observation_pct": round(min(active_net), 6) if active_net else None,
                "invested_loss_observations": sum(v < 0 for v in active_net) if active_net else None,
            })
        rows.append({"symbol": pair[0], "strategy_id": pair[1],
                     "outcomes": len(samples), "invested_observations": sum(d for _,d in samples),
                     "cash_observations": sum(d == 0 for _,d in samples),
                     "invested_observation_fraction": sum(d for _,d in samples)/len(samples) if samples else None,
                     "status": "HYPOTHETICAL_COST_STRESS_ONLY" if samples else "NO_FORWARD_OUTCOMES",
                     "scenarios": scenarios})
    return {"schema": "oracle-q-execution-sensitivity-v1", "ledger_head_sha256": ledger["head_sha256"],
            "pairs": rows, "orders_enabled": False, "fill_verified": False,
            "edge_proven": False, "eligible_for_live_trading": False,
            "limitations": [
                "Costs are fixed assumed total per-side drag, not measured spreads, fees or slippage.",
                "Each invested observation assumes a separate round trip; this is not a continuous portfolio.",
                "Zero-yield cash is a nominal comparator, not a measured interest-bearing cash or Treasury return.",
                "The cost-free market comparator avoids improving relative results by increasing benchmark transaction costs; it is not an executable portfolio.",
                "Invested observation fraction is a sample count, not time-weighted exposure. Worst observation is not portfolio drawdown.",
                "Cash signals incur no trading costs; higher benchmark costs can mechanically improve cash-relative excess.",
                "Zero cost is a diagnostic only. No auction eligibility, liquidity, market impact or fills verified.",
                "Scenario means are descriptive, not statistical confirmation or expected future returns."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = summarize(json.loads(Path(args.ledger).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print("Execution sensitivity:", sum(r["outcomes"] for r in result["pairs"]),
          "outcomes; assumed per-side bps:", COSTS_BPS, "; fills unverified")


if __name__ == "__main__":
    main()
