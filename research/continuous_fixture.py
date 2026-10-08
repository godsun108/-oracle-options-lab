"""Deterministic synthetic-only bars for cross-run continuation tests.

No market observations, no predictive claims, no live order routing.
"""
import argparse
import json
from pathlib import Path

def build(sequence):
    if not isinstance(sequence,int) or sequence < 0 or sequence > 100000:
        raise ValueError("invalid sequence")
    return [
        {"time":f"fixture-{sequence*2+1:08d}","open":99,"high":101,"low":98,"close":100},
        {"time":f"fixture-{sequence*2+2:08d}","open":101,"high":111,"low":99,"close":110},
    ]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--sequence",type=int,required=True)
    parser.add_argument("--output",default="paper_state/fixture-bars.json")
    args=parser.parse_args()
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(build(args.sequence),indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
