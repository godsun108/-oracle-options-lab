"""Oracle x Seldon Fusion 002 — preregistered economic-value test."""
from pathlib import Path
import json, math
import numpy as np, pandas as pd

SPEC="O4_ATM_7_10DTE"
START_YEAR=2022
TOP_FRACTION=.25

def metrics(g):
    r=pd.to_numeric(g["option_return"],errors="coerce").dropna()
    pnl=pd.to_numeric(g.loc[r.index,"one_contract_pnl"],errors="coerce")
    if r.empty:return {"trades":0}
    gp=float(r[r>0].sum()); gl=float(-r[r<0].sum())
    eq=peak=1.0; dd=0.0
    for x in r:
        eq*=1+float(x); peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
    return {"trades":int(len(r)),"mean_option_return":float(r.mean()),
      "mean_one_contract_pnl":float(pnl.mean()),"total_one_contract_pnl":float(pnl.sum()),
      "win_rate":float((r>0).mean()),"profit_factor":gp/gl if gl else None,
      "max_compounded_drawdown":float(dd)}

def main():
    pred=pd.read_csv("fusion001/oracle_seldon_fusion_001_predictions.csv")
    tr=pd.read_csv("oracle/oracle_stage9_options_trades.csv")
    pred["signal_date"]=pd.to_datetime(pred.signal_date).dt.normalize()
    tr=tr[(tr.status=="ok")&(tr.spec==SPEC)].copy()
    tr["signal_date"]=pd.to_datetime(tr.signal_date).dt.normalize()
    z=pred.merge(tr[["signal_date","option_return","one_contract_pnl"]],on="signal_date",how="inner")
    z=z[z.signal_date.dt.year>=START_YEAR].copy()
    n_select=int(np.ceil(len(z)*TOP_FRACTION))
    base=z.sort_values(["p_model_base","signal_date"],ascending=[False,True]).head(n_select)
    fused=z.sort_values(["p_model_fused","signal_date"],ascending=[False,True]).head(n_select)
    overlap=len(set(base.signal_date)&set(fused.signal_date))
    bm, fm, um=metrics(base),metrics(fused),metrics(z)
    result={"schema":"oracle.seldon.fusion.002.v1","status":"RESEARCH_ONLY",
      "preregistered":{"spec":SPEC,"period":"2022-2025","selection":"top quartile by frozen model probability","top_fraction":TOP_FRACTION,
      "primary":"fused minus base mean one-contract option return","no_threshold_search":True},
      "eligible_trades":int(len(z)),"selected_each":n_select,"selection_overlap":int(overlap),
      "unconditional":um,"base_top_quartile":bm,"fused_top_quartile":fm,
      "primary_delta_fused_minus_base_mean_option_return":fm["mean_option_return"]-bm["mean_option_return"],
      "interpretation_boundary":"Historical economic-value test only; no live trading authorization."}
    Path("out").mkdir(exist_ok=True)
    Path("out/oracle_seldon_fusion_002.json").write_text(json.dumps(result,indent=2)+"\n")
    pd.DataFrame([{"group":"unconditional",**um},{"group":"base_top_quartile",**bm},{"group":"fused_top_quartile",**fm}]).to_csv("out/oracle_seldon_fusion_002_summary.csv",index=False)
    pd.concat([base.assign(selection="base"),fused.assign(selection="fused")]).to_csv("out/oracle_seldon_fusion_002_selected.csv",index=False)
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
