"""Emit human-readable checkpoint evidence into the GitHub Actions run summary."""
import argparse
import json
from pathlib import Path
from research.cash_observation_ledger import digest, SCHEMA

def summarize(ledger):
    if ledger.get("schema")!=SCHEMA or ledger.get("orders_enabled") is not False:
        raise ValueError("invalid ledger metadata")
    entries=ledger.get("entries")
    if not isinstance(entries,list) or not entries:
        raise ValueError("missing checkpoints")
    previous=""
    for entry in entries:
        if entry.get("previous_hash")!=previous or digest({k:v for k,v in entry.items() if k!="entry_hash"})!=entry.get("entry_hash"):
            raise ValueError("invalid checkpoint hash chain")
        if entry.get("trades")!=0 or entry.get("cash")!=ledger.get("initial_cash"):
            raise ValueError("unexpected trade or cash change")
        previous=entry["entry_hash"]
    last=entries[-1]
    return ("### Oracle-Q cash observation checkpoints\n\n"
            f"- Checkpoints: **{len(entries)}**\n"
            f"- Latest completed observation: **{last['as_of']}**\n"
            f"- Latest source digest: \`{last['source_sha256']}\`\n"
            f"- Ledger head digest: \`{last['entry_hash']}\`\n"
            "- Trades: **0**; broker orders: **disabled**\n\n"
            "This is a no-trade cash reference, **not evidence of trading profitability**.\n")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",required=True)
    p.add_argument("--summary",required=True)
    args=p.parse_args()
    text=summarize(json.loads(Path(args.ledger).read_text()))
    with open(args.summary,"a",encoding="utf-8") as out:
        out.write(text)
    print(text)
if __name__=="__main__":
    main()
