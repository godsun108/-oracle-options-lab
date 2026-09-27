"""Outcome-blind candidate scheduler for Oracle Q Batch 002."""
from __future__ import annotations
import json
from pathlib import Path
from oracle_q.hypothesis_qubo import anneal_schedule
STRUCTURES=["O1_ATM_2_3DTE","O2_D40_2_3DTE","O3_D25_2_3DTE","O4_ATM_7_10DTE","O5_D40_7_10DTE","O6_D25_7_10DTE"]
FAMILIES={"TREND":5,"VOL":4,"VOLUME":1,"MIXED":10,"MACRO":6,"CONTRACT":11,"FULL":17}
TARGETS=["win_probability","dollar_ev"]
def main():
 c=[];n=0
 for s in STRUCTURES:
  for target in TARGETS:
   for fam,k in FAMILIES.items():
    n+=1
    # outcome-blind: uncertainty-reduction bonus for orthogonal families; complexity penalty handled separately
    info=1.0+(.06 if target=="dollar_ev" else 0)+(.05 if fam in ("VOL","VOLUME","MIXED") else 0)+(.03 if fam in ("MACRO","CONTRACT","FULL") else 0)
    c.append({"id":f"Q2H{n:03d}","option_structure":s,"signal_family":"canonical_signal_v1",
      "regime":fam,"target":target,"contract_features":fam in ("CONTRACT","FULL"),
      "information_value":info,"complexity":max(1,k/5)})
 selected,u=anneal_schedule(c,batch_size=12,redundancy_lambda=.40,complexity_gamma=.12,steps=60000,seed=208)
 out={"schema":"oracle.q.edge_search.batch002.v1","batch_id":"Q-BATCH-002","selection_firewall":"DESIGN_METADATA_ONLY_NO_REALIZED_OUTCOMES",
 "candidate_count":len(c),"selected_count":len(selected),"scheduler":"deterministic simulated annealing over QUBO objective","scheduler_utility":u,"selected":selected,
 "promotion_boundary":"Burned-history discovery only."}
 Path("out").mkdir(exist_ok=True);Path("out/oracle_q_batch_002_manifest.json").write_text(json.dumps(out,indent=2)+chr(10));print(json.dumps(out,indent=2))
if __name__=="__main__":main()
