"""Reproduce report signals from retained parsed provider rows before ledger writes."""
import argparse
import json
from datetime import timedelta
from pathlib import Path
from research.edge_forward_paper import digest, parse_utc_timestamp
from research.edge_lab import evaluate, evaluate_forward, forward_start
from research.edge_session_calendar import eligible_cutoff, CALENDAR_SHA256


def audit(report, registry, *, allow_partial=False):
    if report.get("schema") != "oracle-q-edge-lab-v1" or report.get("orders_enabled") is not False or report.get("edge_proven") is not False:
        raise ValueError("invalid research report")
    cutoff_at = parse_utc_timestamp(report.get("evaluation_cutoff_at"))
    observed = parse_utc_timestamp(report.get("observed_at"))
    cutoff = eligible_cutoff(cutoff_at)
    mode=report.get("collection_mode","historical")
    if mode not in ("historical","forward"):
        raise ValueError("unknown source collection mode")
    request_start=forward_start(cutoff) if mode=="forward" else (cutoff-timedelta(days=850)).isoformat()
    if report.get("cutoff") != cutoff.isoformat() or report.get("calendar_sha256") != CALENDAR_SHA256:
        raise ValueError("source calendar mismatch")
    if cutoff_at > observed:
        raise ValueError("source clock reversed")
    markets = report.get("reports", [])
    if sorted(r["symbol"] for r in markets) != sorted(registry["proxy_symbols"]):
        raise ValueError("source markets missing or duplicated")
    checked = []; blocked=[]
    for market in markets:
        if allow_partial and mode=="forward" and market.get("status")=="DATA_OR_VALIDATION_FAILURE":
            blocked.append(market["symbol"])
            continue  # Explicitly ineligible; cannot enter the ledger loop.
        evidence = market.get("source_evidence", {})
        if (evidence.get("schema") != "oracle-q-parsed-history-evidence-v1"
                or evidence.get("provider") != "tradier"
                or evidence.get("symbol") != market["symbol"]):
            raise ValueError("missing or mismatched source evidence")
        started = parse_utc_timestamp(evidence.get("request_started_at"))
        received = parse_utc_timestamp(evidence.get("received_at"))
        if not cutoff_at <= started <= received <= observed:
            raise ValueError("source receipt chronology invalid")
        if market.get("source_received_at") != evidence["received_at"]:
            raise ValueError("source receipt mismatch")
        if (evidence.get("publication_at") is not None
                or evidence.get("publication_time_verified") is not False):
            raise ValueError("unsupported publication-time assertion")
        if (evidence.get("request_end_date") != cutoff.isoformat()
                or evidence.get("request_start_date") != request_start):
            raise ValueError("source request range mismatch")
        rows = evidence.get("rows")
        if digest(rows) != market.get("source_payload_sha256"):
            raise ValueError("source payload hash mismatch")
        evaluator=evaluate_forward if mode=="forward" else evaluate
        reproduced = evaluator(market["symbol"], rows, registry, now=cutoff_at)
        expected="FORWARD_OPEN_INPUTS_ONLY" if mode=="forward" else "HISTORICAL_OPEN_PROXY_BACKTEST_ONLY"
        if reproduced["status"] != expected:
            raise ValueError("source insufficient for forward research")
        if any(market.get(key) != value for key, value in reproduced.items()):
            raise ValueError("source replay mismatch")
        checked.append({"symbol":market["symbol"], "source_payload_sha256":digest(rows),
                        "strategies_replayed":len(reproduced["strategies"])})
    if not checked:
        raise ValueError("no validated markets")
    return {"schema":"oracle-q-source-replay-v1", "status":"PARTIAL_SOURCE_REPLAY_MATCHED" if blocked else "SOURCE_REPLAY_MATCHED",
            "blocked_markets":blocked,
            "report_sha256":digest(report), "markets":checked,
            "publication_time_verified":False,"provider_authenticity_verified":False,
            "eligible_for_live_trading":False,
            "limitations":"Checks retained parsed rows and declared receipt clocks; not a provider signature, publication attestation, or fill."}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",required=True)
    parser.add_argument("--registry",default="research/edge_registry.json")
    parser.add_argument("--output",default="edge_source_replay.json")
    parser.add_argument("--allow-partial",action="store_true")
    args=parser.parse_args()
    result=audit(json.loads(Path(args.report).read_text()),json.loads(Path(args.registry).read_text()),allow_partial=args.allow_partial)
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Source replay:",result["status"],len(result["markets"]),"markets")


if __name__ == "__main__":
    main()
