"""Oracle Q Batch 003 structural option execution map.

Implements the frozen Batch-003 preregistration. No model fitting or threshold search.
"""
from __future__ import annotations
import io,json,requests
from pathlib import Path
import numpy as np,pandas as pd

U="https://raw.githubusercontent.com/OStochastic/Daily-SPY-data-from-2000-2025/main/spy_data.csv"
BASE="https://raw.githubusercontent.com/anahatsingh-ui/options-dataset-hist/main/spy/options_{}.parquet"
UP="https://raw.githubusercontent.com/anahatsingh-ui/options-dataset-hist/main/spy/underlying_prices.parquet"
SPEC={
"O1_ATM_2_3DTE":("atm",2,3),"O2_D40_2_3DTE":(.40,2,3),"O3_D25_2_3DTE":(.25,2,3),
"O4_ATM_7_10DTE":("atm",7,10),"O5_D40_7_10DTE":(.40,7,10),"O6_D25_7_10DTE":(.25,7,10)}
EXIT={"H1_T2":2,"H2_T3":3,"H4_T5":5}

def underlying():
 r=requests.get(U,timeout=90);r.raise_for_status()
 u=pd.read_csv(io.StringIO(r.text),skiprows=[1,2]);u.columns=["date","close","high","low","open","volume"]
 u.date=pd.to_datetime(u.date);u=u.sort_values("date").reset_index(drop=True)
 for c in ["close","volume"]:u[c]=pd.to_numeric(u[c],errors="raise")
 u["ma200"]=u.close.rolling(200).mean()
 ret=u.close.pct_change()
 u["rv20"]=ret.rolling(20).std()*np.sqrt(252);u["rv60"]=ret.rolling(60).std()*np.sqrt(252)
 u["volume_ratio20"]=u.volume/u.volume.shift(1).rolling(20).mean()
 u["E1_DIP6"]=(u.close.pct_change(6)<=-.01)&(u.close>u.ma200)
 u["E2_SHOCK1"]=(u.close.pct_change(1)<=-.01)&(u.close>u.ma200)
 u["E3_DIP3"]=(u.close.pct_change(3)<=-.01)&(u.close>u.ma200)
 u["E4_DIP10"]=(u.close.pct_change(10)<=-.02)&(u.close>u.ma200)
 u["E5_HIGHVOL_DIP"]=u.E1_DIP6&(u.rv20>u.rv60)
 u["E6_LOWVOL_DIP"]=u.E1_DIP6&(u.rv20<=u.rv60)
 u["E7_VOLUME_DIP"]=u.E1_DIP6&(u.volume_ratio20>1.0)
 return u

def spotmap():
 r=requests.get(UP,timeout=180);r.raise_for_status();s=pd.read_parquet(io.BytesIO(r.content));s.columns=[str(c).lower() for c in s]
 s.date=pd.to_datetime(s.date)
 if "symbol" in s:s=s[s.symbol.astype(str).str.upper()=="SPY"]
 cc=next(c for c in ["close","underlying_close","price","last"] if c in s)
 return s.drop_duplicates("date").set_index("date")[cc]

def load_chains(years,wanted):
 chunks=[]
 for y in sorted(years):
  r=requests.get(BASE.format(y),timeout=240);r.raise_for_status();d=pd.read_parquet(io.BytesIO(r.content))
  d.date=pd.to_datetime(d.date);d.expiration=pd.to_datetime(d.expiration)
  chunks.append(d[d.date.isin(wanted)].copy())
 return pd.concat(chunks,ignore_index=True)

def choose(ent,spec,spot):
 target,lo,hi=SPEC[spec];q=ent.copy();q["dte"]=(q.expiration-q.date).dt.days
 q=q[(q.dte>=lo)&(q.dte<=hi)&(q.bid>0)&(q.ask>0)&(q.ask>=q.bid)]
 if target!="atm":q=q[q.delta.notna()]
 if q.empty:return None,"no_valid_entry_contract"
 if target=="atm":
  if not np.isfinite(spot):return None,"missing_unadjusted_spot"
  q["dist"]=(q.strike-spot).abs()
 else:q["dist"]=(q.delta-float(target)).abs()
 q["oi_sort"]=pd.to_numeric(q.open_interest,errors="coerce").fillna(-1);q["spread"]=q.ask-q.bid;q["cid_sort"]=q.contract_id.astype(str)
 return q.sort_values(["dist","oi_sort","spread","cid_sort"],ascending=[True,False,True,True]).iloc[0],None

def stats(g):
 if g.empty:return {"n":0}
 p=g.one_contract_pnl.astype(float);r=g.option_return.astype(float);gp=float(p[p>0].sum());gl=float(-p[p<0].sum())
 cum=p.cumsum();peak=np.maximum.accumulate(np.r_[0.,cum.to_numpy()]);dd=cum.to_numpy()-peak[1:]
 return {"n":len(g),"mean_dollar_pnl":float(p.mean()),"total_dollar_pnl":float(p.sum()),"win_rate":float((p>0).mean()),
 "mean_option_return":float(r.mean()),"dollar_profit_factor":gp/gl if gl else None,"max_drawdown_dollars":float(dd.min()) if len(dd) else None}

def main():
 man=json.loads(Path("manifest/oracle_q_batch_003_manifest.json").read_text());u=underlying();sm=spotmap()
 schedules=[];wanted=set()
 for c in man["selected"]:
  idx=np.flatnonzero(u[c["event_family"]].fillna(False).to_numpy())
  for i in idx:
   xo=EXIT[c["exit_horizon"]]
   if i+xo>=len(u):continue
   entry=u.loc[i+1,"date"];exitd=u.loc[i+xo,"date"]
   if entry.year<2008 or entry>pd.Timestamp("2025-08-29") or exitd>pd.Timestamp("2025-08-29"):continue
   schedules.append({"candidate_id":c["id"],"event_family":c["event_family"],"spec":c["option_structure"],"exit_horizon":c["exit_horizon"],
    "signal_date":u.loc[i,"date"],"entry_date":entry,"exit_date":exitd})
   wanted|={entry,exitd}
 sch=pd.DataFrame(schedules);chains=load_chains(set(pd.to_datetime(list(wanted)).year),wanted)
 rows=[]
 for z in sch.itertuples(index=False):
  ent=chains[(chains.date==z.entry_date)&(chains.type.astype(str).str.lower()=="call")]
  e,reason=choose(ent,z.spec,float(sm.get(z.entry_date,np.nan)))
  base=z._asdict()
  if reason:rows.append({**base,"status":reason});continue
  # Explicit expiry guard for exact contract at requested exit.
  if pd.Timestamp(e.expiration)<z.exit_date:
   rows.append({**base,"status":"contract_expired_before_exit","contract_id":e.contract_id});continue
  ex=chains[(chains.date==z.exit_date)&(chains.contract_id==e.contract_id)].copy()
  ex=ex[(ex.bid>0)&(ex.ask>0)&(ex.ask>=ex.bid)]
  if ex.empty:rows.append({**base,"status":"no_valid_exact_contract_exit","contract_id":e.contract_id});continue
  x=ex.sort_values("contract_id").iloc[0];entry=float(e.ask);exitp=float(x.bid)
  rows.append({**base,"status":"ok","contract_id":e.contract_id,"expiration":e.expiration,"dte":int(e.dte),"strike":float(e.strike),
   "entry_delta":float(e.delta) if pd.notna(e.delta) else None,"entry_bid":float(e.bid),"entry_ask":entry,"exit_bid":exitp,"exit_ask":float(x.ask),
   "one_contract_pnl":(exitp-entry)*100.,"option_return":(exitp-entry)/entry})
 res=pd.DataFrame(rows);Path("out").mkdir(exist_ok=True);res.to_csv("out/oracle_q_batch_003_trades.csv",index=False)
 summary=[]
 ok=res[res.status=="ok"].copy();ok["year"]=pd.to_datetime(ok.entry_date).dt.year
 for c in man["selected"]:
  g=ok[ok.candidate_id==c["id"]]
  for period,mask in [("2017-2021",(g.year>=2017)&(g.year<=2021)),("2022-2025",g.year>=2022),("FULL",pd.Series(True,index=g.index))]:
   summary.append({"candidate_id":c["id"],"event_family":c["event_family"],"spec":c["option_structure"],"exit_horizon":c["exit_horizon"],"period":period,**stats(g[mask])})
 pd.DataFrame(summary).to_csv("out/oracle_q_batch_003_summary.csv",index=False)
 missing=res[res.status!="ok"].groupby(["candidate_id","status"]).size().rename("n").reset_index();missing.to_csv("out/oracle_q_batch_003_missing.csv",index=False)
 payload={"schema":"oracle.q.batch003.structural_map.v1","status":"BURNED_HISTORY_DISCOVERY_ONLY","selected_candidates":len(man["selected"]),
 "attempts":len(res),"valid_executions":len(ok),"summary":summary,"promotion_boundary":"Historical structural map only; no result establishes a live edge."}
 Path("out/oracle_q_batch_003.json").write_text(json.dumps(payload,indent=2)+chr(10));print(json.dumps(payload,indent=2))
if __name__=="__main__":main()
