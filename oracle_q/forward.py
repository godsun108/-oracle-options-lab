"""Append-only forward signal records for Oracle canonical specifications."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib, json
import pandas as pd
from .canonical_signal import SPEC_VERSION, canonical_signal_v1

@dataclass(frozen=True)
class ForwardRecord:
    spec_version: str
    signal_date: str
    data_cutoff: str
    signal: bool
    close: float
    ret6: float
    ma200: float
    input_hash: str
    recorded_at_utc: str

def evaluate_latest(frame: pd.DataFrame, recorded_at: datetime | None=None) -> ForwardRecord:
    if len(frame)<200: raise ValueError("need at least 200 observations")
    x=frame.copy()
    x["date"]=pd.to_datetime(x["date"])
    x=x.sort_values("date").reset_index(drop=True)
    close=pd.to_numeric(x["close"],errors="raise")
    sig=canonical_signal_v1(x)
    i=len(x)-1
    cutoff=x.loc[i,"date"].date().isoformat()
    payload=x.loc[:i,["date","close"]].copy()
    payload["date"]=payload.date.dt.strftime("%Y-%m-%d")
    digest=hashlib.sha256(payload.to_csv(index=False).encode()).hexdigest()
    now=recorded_at or datetime.now(timezone.utc)
    if now.tzinfo is None: now=now.replace(tzinfo=timezone.utc)
    return ForwardRecord(SPEC_VERSION,cutoff,cutoff,bool(sig.iloc[i]),float(close.iloc[i]),
        float(close.iloc[i]/close.iloc[i-6]-1),float(close.iloc[i-199:i+1].mean()),digest,
        now.astimezone(timezone.utc).isoformat())

def to_json(record: ForwardRecord) -> str:
    return json.dumps(asdict(record),sort_keys=True,separators=(",",":"))
