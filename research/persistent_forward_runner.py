"""Single-writer durable forward paper runner; no brokerage orders.

Inputs: registered plan JSON, completed-bar batch JSON, local state path.
Replays only strictly newer bars, writes state atomically, and reports events.
A scheduler and trusted incremental data feed are still required.
"""
import argparse
import json
import os
from pathlib import Path
from research.conditional_paper import Plan
from research.forward_paper import initial_state, step

def run(plan_dict, bars, state_path, initial_cash=2000.0):
    plan=Plan(**plan_dict)
    plan.check()
    if not plan.validated:
        raise ValueError("strategy must be validated before running")
    path=Path(state_path)
    if path.exists():
        envelope=json.loads(path.read_text(encoding="utf-8"))
        if envelope["plan"]!=plan_dict:
            raise ValueError("registered plan changed; refuse to reuse state")
        state=envelope["state"]
    else:
        state=initial_state(initial_cash)
    previous=state["last_bar"]
    accepted=0
    for bar in bars:
        if previous is not None and bar["time"]<=previous:
            continue
        state=step(state,plan,bar)
        previous=state["last_bar"]
        accepted+=1
    if accepted:
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(path.suffix+".tmp")
        with tmp.open("w",encoding="utf-8") as f:
            json.dump({"plan":plan_dict,"state":state},f,indent=2,sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,path)
    return {"accepted_bars":accepted,"last_bar":state["last_bar"],
            "cash":state["cash"],"open_position":state["position"],
            "event_count":len(state["events"]),"orders_enabled":False,
            "mode":"FORWARD_PAPER_ONLY"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--plan",required=True)
    p.add_argument("--bars",required=True)
    p.add_argument("--state",default="paper_state/forward.json")
    p.add_argument("--report",default="paper_state/report.json")
    args=p.parse_args()
    plan=json.loads(Path(args.plan).read_text(encoding="utf-8"))
    bars=json.loads(Path(args.bars).read_text(encoding="utf-8"))
    report=run(plan,bars,args.state)
    output=Path(args.report)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
