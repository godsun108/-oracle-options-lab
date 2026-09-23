"""Bounded self-repair policy for Oracle CI.

This module classifies known infrastructure failures and proposes only
pre-approved mechanical repairs. It NEVER changes signals, labels, features,
thresholds, execution assumptions, objectives, or research results.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Repair:
    kind: str
    safe: bool
    action: str
    reason: str

KNOWN={
 "StopIteration:": Repair("schema_parse",True,"inspect_source_schema",
   "Parser expected a field that source schema did not expose."),
 "FileNotFoundError:": Repair("missing_file",True,"verify_artifact_path",
   "Expected generated/input file was absent."),
 "KeyError:": Repair("schema_key",False,"halt_and_report",
   "Could be data/schema drift; automatic semantic repair is unsafe."),
}

def classify(log: str) -> Repair:
    for needle,r in KNOWN.items():
        if needle in log: return r
    return Repair("unknown",False,"halt_and_report",
                  "Unknown failures require human review.")

FORBIDDEN=("signal","threshold","target","label","future","execution","objective",
           "risk_lambda","cost_gamma")

def patch_is_mechanical(changed_text: str) -> bool:
    t=changed_text.lower()
    return not any(x in t for x in FORBIDDEN)
