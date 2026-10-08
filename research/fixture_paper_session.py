"""Produce deterministic synthetic completed-bar fixture for CI smoke testing only.

This MUST NOT be treated as market data or as proof of a trading edge.
"""
import json
from pathlib import Path

def build():
    return [
        {"time":"fixture-001","open":99,"high":101,"low":98,"close":100},
        {"time":"fixture-002","open":101,"high":111,"low":99,"close":110},
    ]

def main():
    Path("paper_state").mkdir(exist_ok=True)
    Path("paper_state/fixture-bars.json").write_text(json.dumps(build(),indent=2)+"\n")
    Path("paper_state/fixture-plan.json").write_text(json.dumps({
        "symbol":"TEST_ONLY","direction":"long","trigger":100,"stop":95,
        "target":110,"validated":True
    },indent=2)+"\n")

if __name__=="__main__":
    main()
