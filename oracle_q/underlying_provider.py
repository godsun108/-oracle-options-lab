"""Read-only underlying market-data providers for prospective Oracle research."""
from __future__ import annotations
import io, hashlib, json, requests, pandas as pd

class StooqDailyProvider:
    """Public daily-bars adapter. Market data only; no brokerage/account surface."""
    def __init__(self,session=None):
        self.session=session or requests.Session()
        self.url="https://stooq.com/q/d/l/"

    def history(self,symbol:str)->tuple[pd.DataFrame,dict]:
        params={"s":f"{symbol.lower()}.us","d1":"20000101","i":"d"}
        r=self.session.get(self.url,params=params,timeout=60)
        r.raise_for_status()
        raw=r.text
        x=pd.read_csv(io.StringIO(raw))
        need={"Date","Close"}
        if not need.issubset(x.columns): raise ValueError(f"unexpected Stooq schema: {list(x.columns)}")
        out=x[["Date","Close"]].rename(columns={"Date":"date","Close":"close"})
        out["date"]=pd.to_datetime(out.date,errors="raise")
        out["close"]=pd.to_numeric(out.close,errors="raise")
        out=out.dropna().sort_values("date").drop_duplicates("date",keep="last").reset_index(drop=True)
        meta={"provider":"stooq","symbol":symbol.upper(),"raw_sha256":hashlib.sha256(raw.encode()).hexdigest(),
              "rows":len(out),"data_cutoff":out.iloc[-1].date.date().isoformat()}
        return out,meta
