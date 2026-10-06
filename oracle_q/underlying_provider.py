"""Read-only underlying market-data providers for prospective Oracle research."""
from __future__ import annotations
from datetime import date, timedelta
import hashlib, json, os, requests, pandas as pd

class TradierDailyProvider:
    """Tradier production daily-history adapter. Market data only; no order/account surface."""
    def __init__(self,token:str|None=None,session=None):
        self.token=token or os.getenv("TRADIER_PRODUCTION_TOKEN") or os.getenv("TRADIER_TOKEN")
        if not self.token: raise ValueError("Tradier market-data token is required")
        self.session=session or requests.Session()
        self.url="https://api.tradier.com/v1/markets/history"

    def history(self,symbol:str,start:date|None=None,end:date|None=None)->tuple[pd.DataFrame,dict]:
        end=end or date.today()
        start=start or end-timedelta(days=730)
        params={"symbol":symbol.upper(),"interval":"daily","start":start.isoformat(),"end":end.isoformat()}
        r=self.session.get(self.url,params=params,headers={
            "Authorization":f"Bearer {self.token}","Accept":"application/json"},timeout=30)
        r.raise_for_status()
        payload=r.json()
        rows=((payload.get("history") or {}).get("day") or [])
        if isinstance(rows,dict): rows=[rows]
        if not rows: raise ValueError("Tradier returned no daily history rows")
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"))
        x=pd.DataFrame(rows)
        if not {"date","close"}.issubset(x.columns): raise ValueError(f"unexpected Tradier history schema: {list(x.columns)}")
        out=x[["date","close"]].copy()
        out["date"]=pd.to_datetime(out.date,errors="raise")
        out["close"]=pd.to_numeric(out.close,errors="raise")
        out=out.dropna().sort_values("date").drop_duplicates("date",keep="last").reset_index(drop=True)
        meta={"provider":"tradier","environment":"brokerage-realtime","symbol":symbol.upper(),
              "raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),"rows":len(out),
              "data_cutoff":out.iloc[-1].date.date().isoformat()}
        return out,meta
