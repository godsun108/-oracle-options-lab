"""Oracle Q hypothesis-batch QUBO scheduler.

This module schedules research candidates. It never consumes realized P&L.
"""
from __future__ import annotations
import itertools, json
import numpy as np
from oracle_q.qubo import utility

def similarity(a,b):
    keys=("option_structure","signal_family","regime","target","contract_features")
    return sum(a.get(k)==b.get(k) for k in keys)/len(keys)

def matrices(candidates):
    n=len(candidates)
    info=np.array([float(c["information_value"]) for c in candidates])
    complexity=np.array([float(c["complexity"]) for c in candidates])
    R=np.zeros((n,n))
    for i in range(n):
        for j in range(i+1,n):
            R[i,j]=R[j,i]=similarity(candidates[i],candidates[j])
    return info,R,complexity

def exact_schedule(candidates,batch_size=8,redundancy_lambda=.35,complexity_gamma=.15):
    """Exact fixed-cardinality scheduler for small candidate menus."""
    n=len(candidates)
    if n>30: raise ValueError("Use annealing/QAOA path for >30 candidates")
    info,R,complexity=matrices(candidates)
    best=None; best_u=-np.inf
    # enumerate combinations, not 2^n bitstrings
    for idx in itertools.combinations(range(n),batch_size):
        x=np.zeros(n); x[list(idx)]=1
        u=float(info@x-redundancy_lambda*(x@R@x)/2-complexity_gamma*(complexity@x))
        if u>best_u: best_u=u; best=idx
    return [candidates[i] for i in best],best_u


def anneal_schedule(candidates,batch_size=8,redundancy_lambda=.35,complexity_gamma=.15,
                    steps=25000,seed=108):
    """Deterministic simulated annealing for larger fixed-cardinality menus."""
    rng=np.random.default_rng(seed); n=len(candidates)
    info,R,complexity=matrices(candidates)
    def score(idx):
        x=np.zeros(n); x[list(idx)]=1
        return float(info@x-redundancy_lambda*(x@R@x)/2-complexity_gamma*(complexity@x))
    cur=set(rng.choice(n,size=batch_size,replace=False).tolist()); cur_u=score(cur)
    best=set(cur); best_u=cur_u
    for k in range(steps):
        inside=int(rng.choice(list(cur))); outside=int(rng.choice([i for i in range(n) if i not in cur]))
        nxt=set(cur); nxt.remove(inside); nxt.add(outside); nxt_u=score(nxt)
        temp=max(.002,1.0-k/steps)
        if nxt_u>=cur_u or rng.random()<np.exp((nxt_u-cur_u)/temp):
            cur,cur_u=nxt,nxt_u
            if cur_u>best_u: best,best_u=set(cur),cur_u
    return [candidates[i] for i in sorted(best)],best_u

def qubo_for_scheduler(candidates,redundancy_lambda=.35,complexity_gamma=.15):
    info,R,complexity=matrices(candidates)
    Q=(redundancy_lambda/2)*R
    Q[np.diag_indices_from(Q)]+=-info+complexity_gamma*complexity
    return Q

if __name__=="__main__":
    # synthetic smoke test only; no market outcomes
    c=[{"id":f"H{i}","option_structure":f"O{i%6+1}","signal_family":f"S{i%3}",
        "regime":"macro" if i%2 else "trend","target":"ev" if i%3 else "win",
        "contract_features":bool(i%2),"information_value":1.0+(i%4)*.05,"complexity":1+(i%3)}
       for i in range(12)]
    chosen,u=exact_schedule(c,batch_size=4)
    print(json.dumps({"selected":[x["id"] for x in chosen],"utility":u},indent=2))
