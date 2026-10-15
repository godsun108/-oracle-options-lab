"""Create a safe public Arena artifact from a reviewed shadow-league scorecard.

Fail closed: no scorecard means no competitor data; do not manufacture results.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from research.arena_feed import arena_feed

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--scorecard", required=True)
    p.add_argument("--out", default="arena/arena-feed.json")
    args=p.parse_args()
    result=arena_feed(json.loads(Path(args.scorecard).read_text()),
                      generated_at=datetime.now(timezone.utc).isoformat())
    path=Path(args.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("Arena published snapshot:",path,"competitors:",len(result["rows"]))

if __name__=="__main__":
    main()
