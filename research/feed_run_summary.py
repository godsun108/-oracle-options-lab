"""Generate a truthful GitHub Actions summary from persisted feed evidence."""
import argparse
import json
from pathlib import Path

def summary(payload):
    status = payload.get("status")
    if status not in ("PASS", "FAIL"):
        status = "FAIL"
    problems = payload.get("problems")
    if not isinstance(problems, list):
        problems = ["EVIDENCE_INVALID"]
        status = "FAIL"
    lines = [
        "## Oracle-Q Tradier feed verification",
        "",
        f"**Evidence gate:** {status}",
        f"**Markets observed:** {payload.get('observed', 'unknown')} / {payload.get('expected', 6)}",
        f"**Cutoff:** {payload.get('cutoff', 'unknown')}",
        "**Execution:** read-only; no broker orders",
        "",
        "**This is not evidence of strategy profitability or live-paper performance.**",
    ]
    if problems:
        lines += ["", "**Problems:**"] + [f"- {str(p).replace(chr(10), ' ')}" for p in problems]
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("evidence must be an object")
    except (OSError, ValueError, TypeError):
        payload = {"status": "FAIL", "problems": ["EVIDENCE_MISSING_OR_INVALID"]}
    result = summary(payload)
    Path(args.summary).open("a", encoding="utf-8").write(result)
    print(result)

if __name__ == "__main__":
    main()
