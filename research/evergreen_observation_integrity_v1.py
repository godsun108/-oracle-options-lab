"""Independent, fail-closed structural integrity check for paper observations.

Checks canonical SHA-256 and chronology. A digest proves byte consistency, NOT
the authenticity of the original quote or its venue/source.
"""
import hashlib,json,math
from datetime import datetime,timezone

def canonical(observations):
    return json.dumps(observations,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def verify(packet, *, now=None):
    if not isinstance(packet,dict) or packet.get("schema")!="oracle.forward-observations.v1":
        raise ValueError("invalid observation packet")
    if packet.get("mode")!="RESEARCH_ONLY" or packet.get("ordersEnabled") is not False:
        raise ValueError("unsafe execution flags")
    records=packet.get("observations")
    if not isinstance(records,list) or not records:
        raise ValueError("missing observations")
    digest=hashlib.sha256(canonical(records)).hexdigest()
    reasons=[]
    if packet.get("sha256")!=digest: reasons.append("digest_mismatch")
    current=now or datetime.now(timezone.utc)
    if current.tzinfo is None: raise ValueError("naive verification clock")
    previous=None
    ids=set()
    for record in records:
        if not isinstance(record,dict):
            reasons.append("invalid_record");continue
        rid=record.get("id");ts=record.get("observedAt");price=record.get("mid")
        if not isinstance(rid,str) or not rid or rid in ids:
            reasons.append("duplicate_or_missing_id")
        else: ids.add(rid)
        if isinstance(price,bool) or not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0:
            reasons.append("invalid_price")
        try:
            dt=datetime.fromisoformat(ts.replace("Z","+00:00"))
            if dt.tzinfo is None or dt>current or (previous is not None and dt<=previous):
                reasons.append("invalid_chronology")
            previous=dt
        except (AttributeError,ValueError):
            reasons.append("invalid_timestamp")
    return {"schema":"oracle.observation-integrity-result.v1","mode":"RESEARCH_ONLY",
        "recordCount":len(records),"computedSha256":digest,
        "structuralIntegrityPassed":not reasons,
        "sourceAuthenticityVerified":False,"paperCandidateEligible":False,
        "liveOrderAuthorized":False,"ordersEnabled":False,
        "reasons":list(dict.fromkeys(reasons+["independent_source_authentication_missing"])),
        "warning":"Canonical hash and timestamps are structural checks, not authenticated venue data or fill verification."}
