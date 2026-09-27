"""Generate and freeze Oracle Q batch-001 candidate manifest.

No realized return/P&L fields are read. Candidate utility is design-only.
"""
from __future__ import annotations
import json
from pathlib import Path
from oracle_q.hypothesis_qubo import anneal_schedule

STRUCTURES=["O1_ATM_2_3DTE","O2_D40_2_3DTE","O3_D25_2_3DTE","O4_ATM_7_10DTE","O5_D40_7_10DTE","O6_D25_7_10DTE"]
REGIMES=["trend","trend+seldon12m"]
TARGETS=["win_probability","expected_return"]
CONTRACT=[False,True]

def make_candidates():
    out=[]; n=0
    for s in STRUCTURES:
      for r in REGIMES:
       for t in TARGETS:
        for c in CONTRACT:
         n+=1
         # Design-only score: prioritize orthogonal information and parsimonious models.
         info=1.0
         if t=="expected_return": info+=.08
         if c: info+=.06
         if r!="trend": info+=.04
         complexity=1+(r!="trend")+(t=="expected_return")+(c)
         out.append({"id":f"QH{n:03d}","option_structure":s,"signal_family":"canonical_drawdown",
          "regime":r,"target":t,"contract_features":c,
          "information_value":info,"complexity":complexity})
    return out

def main():
    c=make_candidates()
    selected,u=anneal_schedule(c,batch_size=8,redundancy_lambda=.35,complexity_gamma=.15,steps=25000,seed=108)
    result={"schema":"oracle.q.edge_search.batch.v1","batch_id":"Q-BATCH-001",
      "selection_firewall":"DESIGN_METADATA_ONLY_NO_REALIZED_OUTCOMES",
      "candidate_count":len(c),"selected_count":len(selected),
      "scheduler":"deterministic simulated annealing over fixed-cardinality QUBO objective",
      "scheduler_utility":u,"selected":selected,
      "promotion_boundary":"Historical scoring is discovery only; no historical winner is an edge."}
    Path("out").mkdir(exist_ok=True)
    Path("out/oracle_q_batch_001_manifest.json").write_text(json.dumps(result,indent=2)+chr(10))
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
