"""Read-only options market-data providers for prospective Oracle research."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib, json, os
import requests

@dataclass(frozen=True)
class OptionQuote:
    provider: str
    environment: str
    underlying: str
    symbol: str
    expiration: str
    option_type: str
    strike: float
    bid: float
    ask: float
    open_interest: int
    volume: int
    quote_observed_at_utc: str
    source_trade_date: int | None
    raw_hash: str

class TradierOptionsProvider:
    """Market-data only. This adapter intentionally contains no order methods."""
    def __init__(self, token: str | None=None, sandbox: bool=True, session=None):
        self.token=token or os.getenv("TRADIER_TOKEN")
        if not self.token:
            raise ValueError("TRADIER_TOKEN is required")
        self.sandbox=sandbox
        self.base="https://sandbox.tradier.com/v1" if sandbox else "https://api.tradier.com/v1"
        self.session=session or requests.Session()

    def _get(self,path,params):
        r=self.session.get(self.base+path,params=params,headers={
            "Authorization":f"Bearer {self.token}","Accept":"application/json"},timeout=30)
        r.raise_for_status()
        return r.json()

    def expirations(self, symbol: str) -> list[str]:
        data=self._get("/markets/options/expirations",{"symbol":symbol,"includeAllRoots":"false"})
        dates=((data.get("expirations") or {}).get("date") or [])
        return [str(x) for x in (dates if isinstance(dates,list) else [dates])]

    def chain(self, symbol: str, expiration: str, observed_at: datetime | None=None) -> list[OptionQuote]:
        data=self._get("/markets/options/chains",{"symbol":symbol,"expiration":expiration,"greeks":"false"})
        rows=((data.get("options") or {}).get("option") or [])
        if isinstance(rows,dict): rows=[rows]
        now=(observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
        out=[]
        for x in rows:
            raw=json.dumps(x,sort_keys=True,separators=(",",":"))
            out.append(OptionQuote(
                provider="tradier", environment="sandbox-delayed" if self.sandbox else "brokerage-realtime",
                underlying=symbol, symbol=str(x["symbol"]), expiration=str(x["expiration_date"]),
                option_type=str(x["option_type"]), strike=float(x["strike"]),
                bid=float(x.get("bid") or 0), ask=float(x.get("ask") or 0),
                open_interest=int(x.get("open_interest") or 0), volume=int(x.get("volume") or 0),
                quote_observed_at_utc=now, source_trade_date=x.get("trade_date"),
                raw_hash=hashlib.sha256(raw.encode()).hexdigest()))
        return out

def quote_dict(q: OptionQuote) -> dict:
    return asdict(q)
