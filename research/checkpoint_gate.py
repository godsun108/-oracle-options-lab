"""Consistency gate between a recovered paper snapshot and its report."""
from research.paper_state_snapshot import read_snapshot

def validate_checkpoint(snapshot_path, plan, report):
    state = read_snapshot(snapshot_path, plan)
    if not isinstance(report, dict):
        raise ValueError("invalid checkpoint report")
    last = report.get("last_bar")
    if not isinstance(last, str) or not last.startswith("fixture-"):
        raise ValueError("invalid checkpoint bar")
    if state.get("last_bar") != last:
        raise ValueError("recovered account/report checkpoint mismatch")
    if report.get("mode") != "FORWARD_PAPER_ONLY" or report.get("orders_enabled") is not False:
        raise ValueError("unsafe checkpoint report")
    return state
