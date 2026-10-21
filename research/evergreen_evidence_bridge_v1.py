"""Fail-closed adapter from independently certified forward evidence to Evergreen.

This module cannot certify a ledger. It accepts only explicit audit attestations
from separate verifiers and never infers their truth from strategy metrics.
"""
from evergreen_learning_gate_v1 import evaluate

def evaluate_evidence(packet):
    if not isinstance(packet,dict) or packet.get("schema")!="oracle.evergreen-forward-evidence.v1":
        raise ValueError("unsupported evidence packet")
    if packet.get("mode")!="RESEARCH_ONLY" or packet.get("ordersEnabled") is not False:
        raise ValueError("unsafe evidence packet")
    identity=("candidateId","baselineId","evidenceHash")
    if any(not isinstance(packet.get(k),str) or not packet[k].strip() for k in identity):
        raise ValueError("missing identity")
    attestations=packet.get("attestations")
    if not isinstance(attestations,dict):
        attestations={}
    # Attestation booleans alone are insufficient: an independent verifier
    # must supply a distinct nonempty audit digest for every claimed check.
    checks={
        "independentLineageVerified":"lineage",
        "forwardOnlyVerified":"forward",
        "allCostsVerified":"costs",
        "benchmarkVerified":"benchmark",
    }
    candidate=dict(packet)
    for flag,key in checks.items():
        item=attestations.get(key)
        candidate[flag]=(isinstance(item,dict) and
            item.get("passed") is True and
            isinstance(item.get("auditSha256"),str) and
            len(item["auditSha256"])==64 and
            all(c in "0123456789abcdef" for c in item["auditSha256"]))
    result=evaluate(candidate)
    result["schema"]="oracle.evergreen-evidence-bridge.v1"
    result["attestationsAccepted"]={key:candidate[flag] for flag,key in checks.items()}
    result["sourceEvidenceVerified"]=False
    result["warning"]="Self-reported attestations are NOT independent verification. Requires trusted audit digest resolution and human review; never authorizes promotion or orders."
    # A submitted digest is not proof it was issued by a trusted verifier.
    result["reviewEligible"]=False
    result["reasons"]=list(dict.fromkeys(result["reasons"]+["trusted_attestation_resolution_missing"]))
    return result
