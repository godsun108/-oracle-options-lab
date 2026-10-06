"""Frozen prospective option-chain observation helpers.

Research/paper-forward only. This module selects and records market-data
contracts; it has no order or money-movement capability.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib, json
from .options_provider import OptionQuote

SPEC_VERSION="oracle-q-prospective-options-v1"

@dataclass(frozen=True)
class ProspectiveOptionObservation:
    spec_version: str
    underlying: str
    signal_date: str
    signal: bool
    expiration: str | None
    selected_contract: dict | None
    chain_hash: str | None
    chain_rows: int
    recorded_at_utc: str
    status: str

def first_expiration_on_or_after(expirations:list[str], minimum:date)->str|None:
    valid=sorted(x for x in expirations if date.fromisoformat(x)>=minimum)
    return valid[0] if valid else None

def select_atm_call(quotes:list[OptionQuote], spot:float)->OptionQuote|None:
    q=[x for x in quotes if x.option_type=="call" and x.bid>0 and x.ask>=x.bid and x.ask>0]
    if not q:return None
    return min(q,key=lambda x:(abs(x.strike-spot),-x.open_interest,x.ask-x.bid,x.symbol))

def observe(provider,underlying:str,signal_date:str,signal:bool,spot:float,
            minimum_expiration:date,recorded_at:datetime|None=None)->ProspectiveOptionObservation:
    now=recorded_at or datetime.now(timezone.utc)
    if now.tzinfo is None:now=now.replace(tzinfo=timezone.utc)
    if not signal:
        return ProspectiveOptionObservation(SPEC_VERSION,underlying,signal_date,False,None,None,None,0,
          now.astimezone(timezone.utc).isoformat(),"NO_SIGNAL")
    expiration=first_expiration_on_or_after(provider.expirations(underlying),minimum_expiration)
    if not expiration:
        return ProspectiveOptionObservation(SPEC_VERSION,underlying,signal_date,True,None,None,None,0,
          now.astimezone(timezone.utc).isoformat(),"NO_EXPIRATION")
    chain=provider.chain(underlying,expiration,now)
    chain_hash=hashlib.sha256("".join(sorted(x.raw_hash for x in chain)).encode()).hexdigest()
    chosen=select_atm_call(chain,spot)
    return ProspectiveOptionObservation(SPEC_VERSION,underlying,signal_date,True,expiration,
      asdict(chosen) if chosen else None,chain_hash,len(chain),now.astimezone(timezone.utc).isoformat(),
      "OBSERVED" if chosen else "NO_VALID_CONTRACT")

def to_json(x:ProspectiveOptionObservation)->str:
    return json.dumps(asdict(x),sort_keys=True,separators=(",",":"))
