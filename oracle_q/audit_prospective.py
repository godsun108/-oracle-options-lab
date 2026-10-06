"""Audit append-only Oracle-Q prospective evidence. Research only."""
from __future__ import annotations
import hashlib,json
from datetime import date
from pathlib import Path

def audit_record(p:Path):
    x=json.loads(p.read_text()); errors=[]
    if x.get("schema_version")!="oracle-q-forward-evidence-v1": errors.append("schema")
    if x.get("orders_enabled") is not False: errors.append("orders_enabled")
    if x.get("research_only") is not True: errors.append("research_only")
    sig=x.get("canonical_signal",{}); opt=x.get("prospective_options",{}); src=x.get("underlying_source",{})
    if sig.get("signal_date")!=src.get("data_cutoff"): errors.append("source_cutoff")
    if sig.get("signal_date")!=opt.get("signal_date"): errors.append("option_signal_date")
    side=x.get("seldon_sidecar")
    if side:
        if side.get("can_modify_oracle_signal") is not False: errors.append("seldon_authority")
        if side.get("research_only") is not True: errors.append("seldon_research_only")
        payload=side.get("payload")
        if side.get("state")=="ATTACHED":
            if not payload or payload.get("vintage_safe") is not True or payload.get("status")!="RESEARCH_FEATURE_ONLY": errors.append("seldon_contract")
            elif date.fromisoformat(payload["as_of"])>date.fromisoformat(sig["signal_date"]): errors.append("seldon_future")
            else:
                raw=json.dumps(payload,sort_keys=True,separators=(",",":"))
                if hashlib.sha256(raw.encode()).hexdigest()!=side.get("payload_sha256"): errors.append("seldon_hash")
    return {"file":p.name,"signal_date":sig.get("signal_date"),"signal":sig.get("signal"),
            "option_status":opt.get("status"),"seldon_state":side.get("state") if side else "LEGACY_NONE",
            "ok":not errors,"errors":errors}

def main():
    rows=[audit_record(p) for p in sorted(Path("prospective_records").glob("*.json"))]
    out={"schema":"oracle-q-prospective-audit-v1","records":len(rows),"passed":sum(r["ok"] for r in rows),
         "failed":sum(not r["ok"] for r in rows),"rows":rows}
    Path("out").mkdir(exist_ok=True);Path("out/prospective_audit.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True))
    if out["failed"]: raise SystemExit("prospective evidence audit failed")
if __name__=="__main__":main()
