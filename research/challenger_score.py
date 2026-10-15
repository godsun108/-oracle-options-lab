"""Independent research-only challenger scoring on complete, sealed paper observations.

Not connected to the frozen 2026 ETF season, broker or live orders.
"""
import math
from collections import defaultdict
from research.challenger_registry import verify_registration

def score_shadow_league(registrations, observations, *, required_windows, starting_capital=10000):
    if not isinstance(required_windows, (list, tuple)) or not required_windows or len(set(required_windows)) != len(required_windows):
        raise ValueError("distinct required windows needed")
    if type(starting_capital) not in (int, float) or not math.isfinite(starting_capital) or starting_capital <= 0:
        raise ValueError("invalid equal capital")
    registered = {}
    for item in registrations:
        if not verify_registration(item):
            raise ValueError("unverified candidate registration")
        cid = item["candidate_id"]
        if cid in registered:
            raise ValueError("duplicate registration")
        registered[cid] = item
    observed = defaultdict(dict)
    for item in observations:
        if set(item) != {"candidate_id", "window", "net_return", "evidence_sha256"}:
            raise ValueError("observation schema mismatch")
        cid, window = item["candidate_id"], item["window"]
        if cid not in registered or window not in required_windows or window in observed[cid]:
            raise ValueError("unknown candidate/window or duplicate observation")
        value = item["net_return"]
        if type(value) not in (float, int) or not math.isfinite(value) or value <= -1:
            raise ValueError("invalid net return")
        digest = item["evidence_sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("missing evidence hash")
        observed[cid][window] = float(value)
    rows = []
    for cid, reg in sorted(registered.items()):
        missing = [w for w in required_windows if w not in observed[cid]]
        row = {"candidate_id": cid, "market": reg["market"], "status": "INCOMPLETE_EVIDENCE" if missing else "COMPLETE_DESCRIPTIVE",
               "missing_windows": missing, "net_profit_usd": None, "net_return_pct": None,
               "first_positive_window": None, "max_drawdown_pct": None,
               "edge_proven": False, "eligible_for_live_trading": False}
        if not missing:
            equity = peak = 1.0
            worst = 0.0
            first = None
            for w in required_windows:
                equity *= 1 + observed[cid][w]
                peak = max(peak, equity)
                worst = min(worst, equity / peak - 1)
                if first is None and equity > 1:
                    first = w
            row.update(net_profit_usd=round(starting_capital*(equity-1), 2),
                       net_return_pct=round(100*(equity-1), 6),
                       first_positive_window=first,
                       max_drawdown_pct=round(100*worst, 6))
        rows.append(row)
    groups = defaultdict(list)
    for row in rows:
        if row["status"] == "COMPLETE_DESCRIPTIVE":
            groups[row["market"]].append(row)
    within = {market: [r["candidate_id"] for r in sorted(items, key=lambda r: (-r["net_profit_usd"], r["candidate_id"]))]
              for market, items in sorted(groups.items())}
    across = [r["candidate_id"] for r in sorted((r for r in rows if r["status"] == "COMPLETE_DESCRIPTIVE"),
                                               key=lambda r: (-r["net_return_pct"], r["candidate_id"]))]
    return {"schema": "oracle-q-shadow-league-score-v1", "rows": rows,
            "within_market_descriptive_order": within,
            "cross_market_descriptive_order": across,
            "orders_enabled": False, "promotion_authorized": False,
            "limitations": "Inputs require independent provenance verification; supplied hashes alone do not authenticate returns. Positive return is not proof of edge. No automatic promotion."}
