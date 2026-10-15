"""Candidate registration validation for future shadow leagues; never executes orders.

Separate from the frozen October 2026 ETF paper season.
"""
import hashlib
import json

REQUIRED = {"candidate_id", "market", "parent_id", "code_sha256",
            "data_sha256", "registered_at", "hypothesis", "evaluation_start",
            "evaluation_end", "cost_model", "risk_budget", "trial_family_size"}


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def register_candidate(record, existing_ids=()):
    if not isinstance(record, dict) or set(record) != REQUIRED:
        raise ValueError("candidate registration schema mismatch")
    if not all(isinstance(record[k], str) and record[k].strip()
               for k in ("candidate_id", "market", "code_sha256", "data_sha256",
                         "registered_at", "hypothesis", "evaluation_start",
                         "evaluation_end")):
        raise ValueError("missing candidate identity or evidence")
    if record["candidate_id"] in existing_ids:
        raise ValueError("duplicate candidate identity")
    if record["parent_id"] is not None and (not isinstance(record["parent_id"], str)
                                            or not record["parent_id"].strip()):
        raise ValueError("invalid parent")
    for field in ("code_sha256", "data_sha256"):
        if len(record[field]) != 64 or any(c not in "0123456789abcdef" for c in record[field]):
            raise ValueError("invalid evidence hash")
    from datetime import datetime
    def date(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone required")
        return parsed
    if not date(record["registered_at"]) < date(record["evaluation_start"]) < date(record["evaluation_end"]):
        raise ValueError("prospective evaluation must follow registration")
    if not isinstance(record["cost_model"], dict) or not record["cost_model"]:
        raise ValueError("cost model required")
    if not isinstance(record["risk_budget"], dict) or not record["risk_budget"]:
        raise ValueError("risk budget required")
    if type(record["trial_family_size"]) is not int or record["trial_family_size"] < 1:
        raise ValueError("trial family must be counted")
    sealed = dict(record)
    sealed["registration_sha256"] = canonical_digest(record)
    sealed["status"] = "RESEARCH_ONLY_UNVERIFIED"
    sealed["orders_enabled"] = False
    return sealed


def verify_registration(sealed):
    if not isinstance(sealed, dict) or sealed.get("status") != "RESEARCH_ONLY_UNVERIFIED" or sealed.get("orders_enabled") is not False:
        return False
    return canonical_digest({k: sealed[k] for k in REQUIRED}) == sealed.get("registration_sha256")
