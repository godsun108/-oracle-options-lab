"""Durable local notification outbox for future push/email transports.

No messages are sent by this module. A future delivery worker must atomically
claim messages and record provider acknowledgements. Time is UTC aware.
"""
import json
import os
from pathlib import Path
from research.opportunity_dispatch import parse_time

def queue_event(path, payload, created_at):
    created=parse_time(created_at)
    expiry=parse_time(payload["expires_at"])
    if payload.get("event") not in ("ACTION_REQUIRED","MISSED_OR_EXPIRED"):
        raise ValueError("unsupported event")
    if not payload.get("id") or not payload.get("symbol"):
        raise ValueError("missing opportunity identity")
    key=f'{payload["id"]}:{payload["event"]}'
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    events=[]
    if dest.exists():
        events=json.loads(dest.read_text(encoding="utf-8"))
    if any(x["key"]==key for x in events):
        return {"status":"DUPLICATE","key":key}
    # Expired action requests cannot be queued as actionable alerts.
    state="EXPIRED_BEFORE_QUEUE" if payload["event"]=="ACTION_REQUIRED" and created>=expiry else "PENDING"
    events.append({"key":key,"opportunity_id":payload["id"],"symbol":payload["symbol"],
                   "event":payload["event"],"created_at":created.isoformat(),
                   "expires_at":expiry.isoformat(),"status":state,
                   "delivery_attempts":0,"provider_message_id":None})
    temp=dest.with_suffix(dest.suffix+".tmp")
    with temp.open("w",encoding="utf-8") as stream:
        json.dump(events,stream,indent=2,sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp,dest)
    return {"status":state,"key":key}

def delivery_status(path, key, now):
    events=json.loads(Path(path).read_text(encoding="utf-8"))
    record=next(x for x in events if x["key"]==key)
    late=parse_time(now)>=parse_time(record["expires_at"])
    return {"key":key,"status":record["status"],
            "late":late,"actionable":record["event"]=="ACTION_REQUIRED" and
            record["status"]=="DELIVERED" and not late}
