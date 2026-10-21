"""Research-only multi-asset brokerage gate. No broker API calls or live orders."""
from datetime import datetime, timezone
MARKETS = {"FX","CRYPTO","US_EQUITY","US_OPTIONS","FUTURES"}
def assess(intent):
    if not isinstance(intent,dict): raise ValueError("invalid intent")
    market=intent.get("market")
    if market not in MARKETS: raise ValueError("unsupported market")
    ts=intent.get("asOf")
    try: moment=datetime.fromisoformat(ts.replace("Z","+00:00"))
    except (AttributeError,ValueError): raise ValueError("invalid timestamp") from None
    if moment.tzinfo is None: raise ValueError("timestamp must include timezone")
    if intent.get("ordersEnabled") is not False or intent.get("mode")!="RESEARCH_ONLY":
        raise ValueError("live execution prohibited")
    # A venue's verified session is mandatory for even a paper-order candidate.
    session=intent.get("verifiedVenueSession") is True
    quote=intent.get("verifiedQuote") is True
    allowed=session and quote and intent.get("riskApproved") is True
    return {"schema":"oracle.multi-asset-paper-gate.v1","market":market,
        "asOf":moment.astimezone(timezone.utc).isoformat(),
        "paperCandidateEligible":allowed,"liveOrderAuthorized":False,
        "ordersEnabled":False,"brokerFillsVerified":False,
        "reasons":[] if allowed else [name for name,ok in (
            ("venue_session_unverified",session),("quote_unverified",quote),
            ("risk_not_approved",intent.get("riskApproved") is True)) if not ok],
        "warning":"Research-only paper eligibility, never a live order. No assumed 24/7 venue hours."}
