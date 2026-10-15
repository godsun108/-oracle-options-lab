"""Read-only profitability triage from an audited forward scorecard.

Sorting is descriptive and does not select a winner or certify an edge.
"""
import argparse
import json
import math
from pathlib import Path


def project(scorecard):
    if scorecard.get("schema") != "oracle-q-edge-forward-scorecard-v1":
        raise ValueError("unexpected scorecard schema")
    if scorecard.get("status") != "FORWARD_PAPER_RESEARCH_ONLY":
        raise ValueError("not a forward paper research scorecard")
    if any(scorecard.get(k) is not False for k in
           ("orders_enabled", "fill_verified", "edge_proven", "eligible_for_live_trading")):
        raise ValueError("unsafe scorecard claims")
    rows = scorecard.get("pairs")
    if not isinstance(rows, list) or len(rows) != 18:
        raise ValueError("complete 18-pair scorecard required")
    from research.league_fixtures import MARKETS, STRATEGIES
    expected = {m + "::" + s for m in MARKETS for s in STRATEGIES}
    observed = set()
    candidates = []
    for pair in rows:
        key = pair["symbol"] + "::" + pair["strategy_id"]
        if key not in expected or key in observed:
            raise ValueError("duplicate or unknown strategy")
        observed.add(key)
        n = pair["outcomes_observed"]
        paired = pair["paired_benchmark_observations"]
        if type(n) is not int or type(paired) is not int or n < 0 or not 0 <= paired <= n:
            raise ValueError("invalid observation counts")
        mean = pair.get("mean_hypothetical_return_pct")
        excess = pair.get("mean_excess_vs_buy_hold_pct")
        if n == 0 and mean is not None:
            raise ValueError("profit without observations")
        if n and (type(mean) not in (int, float) or not math.isfinite(mean)):
            raise ValueError("invalid observed profit")
        if paired != n:
            excess = None
        elif n and (type(excess) not in (int, float) or not math.isfinite(excess)):
            raise ValueError("invalid benchmark comparison")
        candidates.append({
            "agent_id": key,
            "forward_observations": n,
            "paired_benchmark_observations": paired,
            "mean_net_hypothetical_return_pct": mean,
            "mean_excess_vs_buy_hold_pct": excess,
            "positive_observations": pair.get("positive_observations"),
            "review_status": pair.get("candidate_review", {}).get("status", "NOT_REVIEWED"),
            "observed_net_positive": bool(n and mean > 0),
            "observed_excess_positive": bool(n and excess is not None and excess > 0),
            "edge_proven": False,
        })
    candidates.sort(key=lambda r: (
        r["mean_net_hypothetical_return_pct"] is None,
        -(r["mean_net_hypothetical_return_pct"] or 0),
        r["agent_id"]))
    return {
        "schema": "oracle-q-forward-profit-triage-v1",
        "status": "DESCRIPTIVE_FORWARD_PAPER_ONLY",
        "ledger_head_sha256": scorecard.get("ledger_head_sha256"),
        "candidates": candidates,
        "agents_with_positive_observed_mean": sum(r["observed_net_positive"] for r in candidates),
        "agents_with_positive_observed_excess": sum(r["observed_excess_positive"] for r in candidates),
        "orders_enabled": False,
        "edge_proven": False,
        "winner_certified": False,
        "warning": "Mean of individually observed hypothetical outcomes, NOT compounded portfolio P&L; descriptive sorting of 18 tested hypotheses is selection-biased. No executable fill or durable profitability proven."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = project(json.loads(Path(args.scorecard).read_text()))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
