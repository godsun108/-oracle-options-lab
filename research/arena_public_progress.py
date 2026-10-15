"""Fail-closed public projection of an audited frozen paper-league review artifact.

This module does not audit the ledger itself. The caller must verify GitHub Actions
run provenance and must use the output of research.export_arena_frozen_league,
which calls the frozen-season ledger audit. No orders or edge certificates.
"""
import argparse
import json
import math
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

MARKETS = {"SPY", "QQQ", "IWM", "SMH", "TLT", "GLD"}
STATES = {"ACCUMULATING_FORWARD_EVIDENCE", "INCOMPLETE_EVIDENCE",
          "FIXED_WINDOW_DESCRIPTIVE_RESULT"}
HASH = re.compile(r"^[0-9a-f]{64}$")


def project(review, *, now, max_age_hours=96):
    if review.get("schema") != "oracle-q-arena-frozen-league-v1" or review.get("source_kind") != "AUDITED_FROZEN_PAPER_LEAGUE":
        raise ValueError("unrecognized frozen-league review")
    if any(review.get(k) is not False for k in ("live", "orders_enabled", "edge_proven")):
        raise ValueError("unsafe trading/edge flags")
    if not all(isinstance(review.get(k), str) and HASH.fullmatch(review[k])
               for k in ("ledger_head_sha256", "rules_sha256")):
        raise ValueError("missing ledger or rules digest")
    if review.get("season_id") != "etf-open-paper-2026-10-v1":
        raise ValueError("unexpected season")
    timestamp = datetime.fromisoformat(review["as_of"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone aware")
    now = now.astimezone(timezone.utc)
    age = now - timestamp.astimezone(timezone.utc)
    if age < timedelta(minutes=-5) or age > timedelta(hours=max_age_hours):
        raise ValueError("stale or future evidence snapshot")
    rows = review.get("rows")
    if not isinstance(rows, list) or len(rows) != len(MARKETS):
        raise ValueError("must include exactly six registered markets")
    result = []
    seen = set()
    for row in rows:
        market = row.get("market")
        if market not in MARKETS or market in seen:
            raise ValueError("missing, duplicate or unexpected market")
        seen.add(market)
        if row.get("candidate_id") != market + "::frozen-three-strategy-basket":
            raise ValueError("unexpected frozen basket identity")
        if row.get("status") not in STATES:
            raise ValueError("unexpected status")
        if row.get("edge_proven") is not False or row.get("eligible_for_live_trading") is not False:
            raise ValueError("unauthorized edge or live trading claim")
        done, required = row.get("completed_common_sessions"), row.get("required_sessions")
        if type(done) is not int or type(required) is not int or required != 60 or not 0 <= done <= 60:
            raise ValueError("invalid session progress")
        if not isinstance(row.get("missing_eligible_windows"), list):
            raise ValueError("missing evidence-window accounting")
        complete = row["status"] == "FIXED_WINDOW_DESCRIPTIVE_RESULT"
        if complete != (done == 60):
            raise ValueError("premature or suppressed completed season")
        if not complete and (row.get("net_return_pct") is not None or row.get("max_drawdown_pct") is not None):
            raise ValueError("partial season cannot show performance")
        if complete:
            for key in ("net_return_pct", "max_drawdown_pct"):
                v = row.get(key)
                if type(v) not in (float, int) or not math.isfinite(v):
                    raise ValueError("nonfinite final performance")
        result.append({key: row[key] for key in
                       ("candidate_id", "market", "status", "completed_common_sessions",
                        "required_sessions", "net_return_pct", "max_drawdown_pct")})
    return {"schema": "oracle-q-arena-feed-v1", "generated_at": now.isoformat(),
            "source_as_of": timestamp.isoformat(), "source_kind": "AUDITED_FROZEN_PAPER_LEAGUE",
            "season_id": review["season_id"], "ledger_head_sha256": review["ledger_head_sha256"],
            "rules_sha256": review["rules_sha256"], "live": False, "orders_enabled": False,
            "edge_proven": False, "rows": result,
            "warning": "Audited ledger consistency is not independent price-source attestation. Fixed hypothetical paper strategies; no live orders or proven edge. Rankings only after 60 complete common sessions."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    feed = project(json.loads(Path(args.review).read_text()), now=datetime.now(timezone.utc))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(feed, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
