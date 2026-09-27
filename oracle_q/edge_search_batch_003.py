"""Outcome-blind structural scheduler for Oracle Q Batch 003."""
from __future__ import annotations
import json
from pathlib import Path
from oracle_q.hypothesis_qubo import anneal_schedule
EVENTS=["E1_DIP6","E2_SHOCK1","E3_DIP3","E4_DIP10","E5_HIGHVOL_DIP","E6_LOWVOL_DIP","E7_VOLUME_DIP"]
SPECS={"O1_ATM_2_3DTE":3,"O2_D40_2_3DTE":3,"O3_D25_2_3DTE":3,"O4_ATM_7_10DTE":10,"O5_D40_7_10DTE":10,"O6_D25_7_10DTE":10}
H={"H1_T2":1,"H2_T3":2,"H4_T5":4}
def main():
 c=[];n=0
 for e in EVENTS:
  for s,maxdte in SPECS.items():
   for h,days_after_entry in H.items():
    n+=1
    feasible=maxdte>=days_after_entry+1
    if not feasible:continue
    # Map scheduler fields onto structural dimensions for existing diversity objective.
    c.append({"id":f"Q3H{n:03d}","event_family":e,"option_structure":s,"exit_horizon":h,
      "signal_family":e,"regime":h,"target":"structural_dollar_pnl","contract_features":s,
      "information_value":1.0+(.05 if h!="H1_T2" else 0)+(.03 if e!="E1_DIP6" else 0),
      "complexity":1.0+(.15 if h=="H4_T5" else 0)})
 sel,u=anneal_schedule(c,batch_size=18,redundancy_lambda=.34,complexity_gamma=.08,steps=90000,seed=308)
 out={"schema":"oracle.q.edge_search.batch003.v1","batch_id":"Q-BATCH-003","selection_firewall":"DESIGN_METADATA_AND_DTE_FEASIBILITY_ONLY_NO_OUTCOMES",
 "feasible_candidate_count":len(c),"selected_count":len(sel),"scheduler":"deterministic simulated annealing over QUBO diversity objective","scheduler_utility":u,"selected":sel,
 "promotion_boundary":"Burned-history structural map only; future paper-forward required."}
 Path("out").mkdir(exist_ok=True);Path("out/oracle_q_batch_003_manifest.json").write_text(json.dumps(out,indent=2)+chr(10));print(json.dumps(out,indent=2))
if __name__=="__main__":main()
