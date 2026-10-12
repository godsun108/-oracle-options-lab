"""Fail-closed recovery of the latest successful production paper ledger.

Uses existing read-only GitHub Actions credentials through gh. Never falls back
to an older artifact or starts genesis when established evidence is unavailable.
Artifact digests provide transfer integrity, not independent source attestation.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

from research.edge_forward_integrity_audit import audit

PRODUCTION_EVENTS = {"push", "schedule", "workflow_dispatch"}
WORKFLOW_PATH = ".github/workflows/edge-lab.yml"


def select_previous(runs, current):
    candidates = [r for r in runs
                  if r["id"] != current["id"]
                  and r["run_number"] < current["run_number"]
                  and r["workflow_id"] == current["workflow_id"]
                  and r["path"] == WORKFLOW_PATH
                  and r["head_branch"] == "main"
                  and r["event"] in PRODUCTION_EVENTS
                  and r["status"] == "completed"
                  and r["conclusion"] == "success"]
    if not candidates:
        raise ValueError("CONTINUITY_BLOCKED: no prior successful production run")
    return max(candidates, key=lambda r: r["run_number"])


def select_artifact(artifacts, run):
    matches = [a for a in artifacts if a["name"] == f"oracle-edge-lab-{run['id']}"]
    if len(matches) != 1 or matches[0].get("expired") is not False:
        raise ValueError("CONTINUITY_BLOCKED: latest production artifact missing, duplicate or expired")
    artifact = matches[0]
    origin = artifact.get("workflow_run", {})
    if any(origin.get(k) != run[k] for k in ("id", "head_sha", "head_branch")):
        raise ValueError("CONTINUITY_BLOCKED: artifact run provenance mismatch")
    if not str(artifact.get("digest", "")).startswith("sha256:"):
        raise ValueError("CONTINUITY_BLOCKED: missing artifact digest")
    return artifact


def decode_ledger(archive, artifact):
    if "sha256:" + hashlib.sha256(archive).hexdigest() != artifact["digest"]:
        raise ValueError("CONTINUITY_BLOCKED: artifact digest mismatch")
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        if bundle.namelist().count("edge_forward_ledger.json") != 1:
            raise ValueError("CONTINUITY_BLOCKED: ledger missing or duplicate in artifact")
        ledger = json.loads(bundle.read("edge_forward_ledger.json"))
    audit(ledger)
    if not ledger["events"]:
        raise ValueError("CONTINUITY_BLOCKED: established ledger cannot be empty")
    return ledger


def verify_extension(previous, current):
    audit(previous)
    audit(current)
    count = previous["events_recorded"]
    if current["events"][:count] != previous["events"]:
        raise ValueError("CONTINUITY_BLOCKED: prior event prefix changed or truncated")
    return {"status": "PRIOR_EVENT_PREFIX_PRESERVED", "prior_head_sha256": previous["head_sha256"],
            "current_head_sha256": current["head_sha256"], "prior_events": count,
            "current_events": current["events_recorded"], "orders_enabled": False,
            "fill_verified": False, "edge_proven": False}


def gh_bytes(endpoint):
    # Never log credentials or HTTP response bodies on failure.
    result = subprocess.run(["gh", "api", endpoint], capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError("CONTINUITY_BLOCKED: GitHub evidence request failed")
    return result.stdout


def gh_json(endpoint):
    return json.loads(gh_bytes(endpoint))


def restore(repository, run_id, destination):
    root = f"repos/{repository}/actions"
    current = gh_json(f"{root}/runs/{run_id}")
    if (current["path"] != WORKFLOW_PATH or current["head_branch"] != "main"
            or current["event"] not in PRODUCTION_EVENTS):
        raise ValueError("CONTINUITY_BLOCKED: restoration is production-only")
    previous = None
    # GitHub lists runs newest first. Bound lookup; exhausting history fails closed.
    for page in range(1, 21):
        runs = gh_json(f"{root}/workflows/{current['workflow_id']}/runs?branch=main&status=success&per_page=100&page={page}")["workflow_runs"]
        try:
            previous = select_previous(runs, current)
            break
        except ValueError:
            if len(runs) < 100:
                break
    if previous is None:
        raise ValueError("CONTINUITY_BLOCKED: prior production evidence not found; no automatic genesis")
    listing = gh_json(f"{root}/runs/{previous['id']}/artifacts?per_page=100")
    if listing["total_count"] > 100:
        raise ValueError("CONTINUITY_BLOCKED: artifact listing exceeds bound")
    artifact = select_artifact(listing["artifacts"], previous)
    archive = gh_bytes(f"{root}/artifacts/{artifact['id']}/zip")
    ledger = decode_ledger(archive, artifact)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "oracle-q-evidence-restore-v1", "repository": repository,
                "current_run_id": run_id, "previous_run_id": previous["id"],
                "previous_head_sha": previous["head_sha"], "artifact_id": artifact["id"],
                "artifact_digest": artifact["digest"], "prior_head_sha256": ledger["head_sha256"],
                "prior_events": ledger["events_recorded"], "orders_enabled": False}
    (destination / "edge_forward_ledger.json").write_text(json.dumps(ledger, sort_keys=True) + "\n")
    (destination / "edge_restore_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified restoration from run {previous['id']}: {ledger['events_recorded']} events; head {ledger['head_sha256']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="edge-restore")
    parser.add_argument("--prior")
    parser.add_argument("--current")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.current:
        if not args.prior or not args.output:
            parser.error("extension verification requires --prior and --output")
        result = verify_extension(json.loads(Path(args.prior).read_text()),
                                  json.loads(Path(args.current).read_text()))
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
        print("Forward continuity:", result["status"], result["prior_events"], "->", result["current_events"])
    else:
        restore(os.environ["GITHUB_REPOSITORY"], int(os.environ["GITHUB_RUN_ID"]), args.directory)


if __name__ == "__main__":
    main()
