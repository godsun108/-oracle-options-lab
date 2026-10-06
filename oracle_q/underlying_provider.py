"""Read-only underlying market-data providers for prospective Oracle research."""
from __future__ import annotations
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import hashlib, json, os, requests, pandas as pd

class TradierDailyProvider:
    """Tradier daily-history adapter. Current-session partial bars are excluded before 16:15 ET."""
    def __init__(self,token:str|None=None,session=None,now=None):
        self.token=token or os.getenv("TRADIER_PRODUCTION_TOKEN") or os.getenv("TRADIER_TOKEN")
        if not self.token: raise ValueError("Tradier market-data token is required")
        self.session=session or requests.Session(); self.now=now
        self.url="https://api.tradier.com/v1/markets/history"

    def history(self,symbol:str,start:date|None=None,end:date|None=None)->tuple[pd.DataFrame,dict]:
        now_et=self.now or datetime.now(ZoneInfo("America/New_York"))
        if now_et.tzinfo is None: now_et=now_et.replace(tzinfo=ZoneInfo("America/New_York"))
        end=end or now_et.date(); start=start or end-timedelta(days=730)
        params={"symbol":symbol.upper(),"interval":"daily","start":start.isoformat(),"end":end.isoformat()}
        r=self.session.get(self.url,params=params,headers={"Authorization":f"Bearer {self.token}","Accept":"application/json"},timeout=30)
        r.raise_for_status(); payload=r.json(); rows=((payload.get("history") or {}).get("day") or [])
        if isinstance(rows,dict): rows=[rows]
        if not rows: raise ValueError("Tradier returned no daily history rows")
        raw=json.dumps(payload,sort_keys=True,separators=(",",":")); x=pd.DataFrame(rows)
        if not {"date","close"}.issubset(x.columns): raise ValueError(f"unexpected Tradier history schema: {list(x.columns)}")
        out=x[["date","close"]].copy(); out["date"]=pd.to_datetime(out.date,errors="raise"); out["close"]=pd.to_numeric(out.close,errors="raise")
        out=out.dropna().sort_values("date").drop_duplicates("date",keep="last").reset_index(drop=True)
        partial_removed=False
        if end>=now_et.date() and now_et.timetz().replace(tzinfo=None)<time(16,15):
            before=len(out); out=out[out.date.dt.date<now_et.date()].reset_index(drop=True); partial_removed=len(out)<before
        if out.empty: raise ValueError("no completed Tradier daily bars")
        meta={"provider":"tradier","environment":"brokerage-realtime","symbol":symbol.upper(),"raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),
              "rows":len(out),"data_cutoff":out.iloc[-1].date.date().isoformat(),"session_policy":"exclude_current_date_before_16:15_ET",
              "partial_current_session_removed":partial_removed}
        return out,meta
