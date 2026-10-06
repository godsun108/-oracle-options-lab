import json
from pathlib import Path
from oracle_q.audit_prospective import audit_record

def base():
 return {"schema_version":"oracle-q-forward-evidence-v1","orders_enabled":False,"research_only":True,
 "underlying_source":{"data_cutoff":"2026-10-06"},"canonical_signal":{"signal_date":"2026-10-06","signal":False},
 "prospective_options":{"signal_date":"2026-10-06","status":"NO_SIGNAL"}}

def test_clean_record(tmp_path):
 p=tmp_path/"x.json";p.write_text(json.dumps(base()))
 assert audit_record(p)["ok"]

def test_future_seldon_is_rejected(tmp_path):
 x=base();x["seldon_sidecar"]={"state":"ATTACHED","research_only":True,"can_modify_oracle_signal":False,
 "payload":{"as_of":"2026-10-07","vintage_safe":True,"status":"RESEARCH_FEATURE_ONLY"},"payload_sha256":"x"}
 p=tmp_path/"x.json";p.write_text(json.dumps(x))
 r=audit_record(p);assert not r["ok"] and "seldon_future" in r["errors"]

def test_order_authority_is_rejected(tmp_path):
 x=base();x["orders_enabled"]=True;p=tmp_path/"x.json";p.write_text(json.dumps(x))
 r=audit_record(p);assert not r["ok"] and "orders_enabled" in r["errors"]

def test_excluded_record_can_be_intact_but_inadmissible(tmp_path):
 p=tmp_path/"2026-10-06.json";p.write_text(json.dumps(base()))
 r=audit_record(p,{"2026-10-06.json":{"reason":"partial session"}})
 assert r["ok"] is True and r["admissible"] is False
 assert r["inadmissible_reason"]=="partial session"
