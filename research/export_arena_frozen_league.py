"""Export audited frozen ETF standings to a separate reviewable artifact.

Never mutates the public Pages feed. Ledger must be supplied explicitly.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from research.arena_frozen_league import frozen_league_arena

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",required=True)
    p.add_argument("--output",default="out/arena-frozen-league-review.json")
    args=p.parse_args()
    result=frozen_league_arena(json.loads(Path(args.ledger).read_text()),
                               as_of=datetime.now(timezone.utc).isoformat())
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Reviewed frozen-league artifact:",len(result["rows"]),"teams, no live orders")

if __name__=="__main__":
    main()
