"""Conservative challenger promotion recommendation; never executes trades.

The caller must independently verify evidence provenance and prospective timing.
No automatic replacement of existing paper season or live strategies.
"""
import math
from research.challenger_registry import verify_registration

def evaluate_promotion(challenger, incumbent, *, independent_audit_passed,
                       prospective_windows, holdout_untouched,
                       multiple_testing_control_passed, risk_limits_passed,
                       min_windows=20, minimum_net_improvement_pct=0.0):
    if not verify_registration(challenger["registration"]):
        raise ValueError("challenger registration invalid")
    if not isinstance(incumbent, dict) or challenger["registration"]["candidate_id"] == incumbent.get("candidate_id"):
        raise ValueError("distinct incumbent required")
    if challenger["registration"]["market"] != incumbent.get("market"):
        raise ValueError("must challenge within same market")
    if challenger["registration"]["parent_id"] != incumbent.get("candidate_id"):
        raise ValueError("parent must match frozen incumbent")
    if type(min_windows) is not int or min_windows < 1:
        raise ValueError("invalid minimum windows")
    if not isinstance(prospective_windows, int) or isinstance(prospective_windows, bool) or prospective_windows < 0:
        raise ValueError("invalid prospective count")
    for row in (challenger, incumbent):
        if row.get("status") != "COMPLETE_DESCRIPTIVE":
            # A sealed challenger registration can be supplied separately; a scoring
            # row must be merged only after external evidence audit.
            return {"decision": "REJECT_INCOMPLETE", "paper_promotion_authorized": False,
                    "live_promotion_authorized": False}
    def finite_number(v):
        return type(v) in (int, float) and math.isfinite(v)
    c, i = challenger.get("net_return_pct"), incumbent.get("net_return_pct")
    if not finite_number(c) or not finite_number(i):
        raise ValueError("invalid returns")
    gates = {
        "independent_audit": independent_audit_passed is True,
        "untouched_holdout": holdout_untouched is True,
        "multiple_testing": multiple_testing_control_passed is True,
        "risk_limits": risk_limits_passed is True,
        "minimum_prospective_windows": prospective_windows >= min_windows,
        "net_improvement": c > i + minimum_net_improvement_pct,
    }
    return {"decision": "RECOMMEND_NEXT_PAPER_SEASON" if all(gates.values()) else "DO_NOT_PROMOTE",
            "gates": gates, "paper_promotion_authorized": False,
            "live_promotion_authorized": False,
            "warning": "Recommendation is not authorization. Scores must come from independently verified matching prospective windows."}
