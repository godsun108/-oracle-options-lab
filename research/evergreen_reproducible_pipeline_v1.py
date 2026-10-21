"""Deterministic research-only pipeline for integrity -> risk -> stress.

Accepts an observation packet, snapshot, proposal and stress export. Explicitly
never upgrades self-reported flags to independent authentication.
"""
from evergreen_observation_integrity_v1 import verify as check_observations
from evergreen_unified_paper_gate_v1 import assess as assess_risk

def evaluate(observations, snapshot, proposal, mandate, stress_export, scenarios, *, now=None):
    integrity=check_observations(observations,now=now)
    # Portfolio assessment is descriptive only; caller-supplied verification
    # flags must never confer authority or turn integrity into source proof.
    risk=assess_risk(snapshot,proposal,mandate,stress_export,scenarios)
    reasons=list(integrity["reasons"])+list(risk["reasons"])
    return {"schema":"oracle.evergreen-reproducible-pipeline.v1",
            "mode":"RESEARCH_ONLY","observationIntegrity":integrity,
            "unifiedRisk":risk,
            "structuralIntegrityPassed":integrity["structuralIntegrityPassed"],
            "hypotheticalRiskWithinLimits":risk["hypotheticalRiskWithinLimits"],
            "independentSourceVerified":False,"brokerLedgerVerified":False,
            "paperCandidateEligible":False,"liveOrderAuthorized":False,
            "ordersEnabled":False,"reasons":list(dict.fromkeys(reasons)),
            "warning":"Deterministic analysis only: no independent source authentication, broker reconciliation, paper fills, or order authorization."}
