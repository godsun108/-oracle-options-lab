"""Offline, reproducible multi-strategy paper research on supplied OHLC bars.

Not a forward paper brokerage; only evaluates pre-registered plans against
historical bars. Every result is recorded, including NO_TRADE.
"""
import argparse
import json
from research.paper_ledger import append_record, evaluate

def run(manifest, ledger):
    if manifest.get("mode") != "HISTORICAL_SIMULATION_ONLY":
        raise ValueError("historical simulation mode required")
    results=[]
    for candidate in manifest.get("candidates", []):
        if "strategy_id" not in candidate or "dataset_id" not in candidate:
            raise ValueError("strategy_id and dataset_id required")
        spec={"mode":"HISTORICAL_SIMULATION_ONLY",
              "plan":candidate["plan"],"bars":candidate["bars"],
              "capital":candidate.get("capital",2000),
              "fee_per_share":candidate.get("fee_per_share",0),
              "slippage_per_share":candidate.get("slippage_per_share",0.01),
              "data_provenance":candidate["dataset_id"]}
        record=evaluate(spec)
        record["strategy_id"]=candidate["strategy_id"]
        record["dataset_id"]=candidate["dataset_id"]
        receipt=append_record(ledger,record)
        results.append({"strategy_id":candidate["strategy_id"],
                        "symbol":candidate["plan"]["symbol"],
                        "result":record["result"],"receipt":receipt})
    return {"mode":"HISTORICAL_SIMULATION_ONLY","orders_enabled":False,
            "evaluated":len(results),"results":results}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True)
    parser.add_argument("--ledger",default="paper_records/paper_ledger.jsonl")
    parser.add_argument("--report",default="paper_research_report.json")
    args=parser.parse_args()
    with open(args.manifest,encoding="utf-8") as stream:
        manifest=json.load(stream)
    output=run(manifest,args.ledger)
    with open(args.report,"w",encoding="utf-8") as stream:
        json.dump(output,stream,indent=2,sort_keys=True)
        stream.write("\n")
    print("Historical candidates evaluated:",output["evaluated"])

if __name__=="__main__":
    main()
