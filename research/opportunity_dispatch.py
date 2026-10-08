"""Fail-closed opportunity notification and approval lifecycle (no network/orders).

All times are UTC-aware ISO 8601 strings. Approval creates a REQUEST only;
it is never an instruction to submit an order.
"""
from datetime import datetime, timezone

STATES={"WATCH","READY","EXPIRED","APPROVAL_REQUESTED","REJECTED"}

def parse_time(value):
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)

def transition(opportunity, action, now, quote_fresh=False, risk_passed=False):
    record=dict(opportunity)
    state=record.get("state")
    if state not in STATES:
        raise ValueError("unknown state")
    now_dt=parse_time(now)
    expiry=parse_time(record["expires_at"])
    if not record.get("id") or not record.get("symbol"):
        raise ValueError("id and symbol required")
    if state in ("EXPIRED","REJECTED","APPROVAL_REQUESTED"):
        return {"opportunity":record,"event":"UNCHANGED","orders_enabled":False}
    if now_dt >= expiry:
        record["state"]="EXPIRED"
        return {"opportunity":record,"event":"MISSED_OR_EXPIRED","orders_enabled":False}
    if action=="trigger" and state=="WATCH":
        record["state"]="READY"
        return {"opportunity":record,"event":"ACTION_REQUIRED","orders_enabled":False}
    if action=="approve" and state=="READY":
        if not (quote_fresh and risk_passed):
            return {"opportunity":record,"event":"APPROVAL_BLOCKED_RECHECK","orders_enabled":False}
        record["state"]="APPROVAL_REQUESTED"
        record["approval_requested_at"]=now_dt.isoformat()
        return {"opportunity":record,"event":"APPROVAL_REQUESTED_NOT_EXECUTED","orders_enabled":False}
    if action=="reject" and state=="READY":
        record["state"]="REJECTED"
        return {"opportunity":record,"event":"REJECTED","orders_enabled":False}
    return {"opportunity":record,"event":"UNCHANGED","orders_enabled":False}

def notification(result):
    event=result["event"]
    if event not in ("ACTION_REQUIRED","MISSED_OR_EXPIRED"):
        return None
    p=result["opportunity"]
    return {"id":p["id"],"symbol":p["symbol"],"event":event,
            "expires_at":p["expires_at"],"message":(
                "Setup ready: review before expiry; no order placed."
                if event=="ACTION_REQUIRED" else
                "Setup expired or missed; do not chase. No order placed."),
            "delivery_status":"NOT_SENT"}
