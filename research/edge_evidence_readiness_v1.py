"""Fail-closed evidence readiness for Oracle-Q strategy profitability research.

Never converts observed quotes or forward signals into trades or realized P&L.
"""
import json
from pathlib import Path
from edge_profitability_scorecard_v1 import score

def evaluate(payload):
    if not isinstance(payload, dict) or payload.get("schema") != "oracle-q-edge-evidence-input-v1" or payload.get("mode") != "RESEARCH_ONLY" or payload.get("orders_enabled") is not False:
        raise ValueError("unsafe or invalid evidence envelope")
    observations = payload.get("observations", [])
    trades = payload.get("settled_paper_trades", [])
    if not isinstance(observations, list) or not isinstance(trades, list):
        raise ValueError("invalid evidence collections")
    for observation in observations:
        if not isinstance(observation, dict) or observation.get("broker_fills_verified") is not False or observation.get("realized_pnl_available") is not False:
            raise ValueError("observation falsely claims realized trade evidence")
    if trades:
        metrics = score(trades)
        # A scorecard computes metrics; it does not establish provenance, price validity,
        # trade chronology or benchmark superiority on its own.
        status = "SETTLED_PAPER_METRICS_UNVERIFIED_PROVENANCE"
        blockers = ["independent_trade_lineage_unverified",
                    "walk_forward_and_benchmark_not_verified",
                    "cost_model_not_independently_verified"]
    else:
        metrics = None
        status = "NO_SETTLED_PAPER_TRADES"
        blockers = ["no_settled_paper_trades",
                    "cannot_infer_pnl_from_forward_observations"]
    return {"schema": "oracle-q-edge-evidence-readiness-v1",
            "mode": "RESEARCH_ONLY", "orders_enabled": False,
            "observation_count": len(observations),
            "settled_paper_trade_count": len(trades),
            "status": status, "blockers": blockers,
            "metrics": metrics, "verified_edge": False,
            "promotion_authorized": False, "broker_fills_verified": False}

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("usage: python research/edge_evidence_readiness_v1.py evidence-input.json")
    print(json.dumps(evaluate(json.loads(Path(sys.argv[1]).read_text())), indent=2))
