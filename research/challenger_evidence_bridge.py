"""Read-only bridge from existing audited forward ledger to descriptive shadow scores.

Existing fixed strategy signals are *not* retroactively registered as new challengers.
This is an observational baseline adapter, not a promotion mechanism.
"""
from research.edge_forward_integrity_audit import audit
from research.edge_forward_paper import parse_utc_timestamp
from research.challenger_score import score_shadow_league
from research.challenger_registry import register_candidate
from research.edge_lab import IDS
from research.multi_market_observer import SYMBOLS

def baseline_shadow_score(ledger, *, windows, registration_template):
    """Score fixed incumbent observations only, after independent ledger semantic audit.

    windows: ordered (entry_date, exit_date) pairs. No missing-window interpolation.
    registration_template: prospective metadata supplied by caller. Registration dates
    must precede evaluation dates; existing outcomes cannot be retroactively admitted.
    """
    audit(ledger)
    if not windows or len(set(map(tuple, windows))) != len(windows):
        raise ValueError("unique windows required")
    symbols = set(SYMBOLS)
    strategies = set(IDS)
    opens = {}
    signals = {}
    outcomes = []
    for event in ledger["events"]:
        if event["type"] == "SOURCE_OPEN_CHECKPOINT":
            opens[event["symbol"], event["open_date"]] = event["open_price"]
        elif event["type"] == "SIGNAL_REGISTERED":
            signals[event["symbol"], event["strategy_id"], event["signal_date"]] = event
        elif event["type"] == "PAPER_OUTCOME_OBSERVED":
            outcomes.append(event)
    regs = []
    for symbol in sorted(symbols):
        for strategy in sorted(strategies):
            record = dict(registration_template)
            record.update(candidate_id=symbol+"::"+strategy, market=symbol,
                          parent_id=None, hypothesis="Frozen incumbent observational baseline: "+strategy)
            regs.append(register_candidate(record))
    observed = []
    for event in outcomes:
        symbol, strategy = event["symbol"], event["strategy_id"]
        window = (event["entry_date"], event["exit_date"])
        if symbol not in symbols or strategy not in strategies or window not in windows:
            continue
        signal = signals[symbol, strategy, event["signal_date"]]
        # Never treat outcomes observed before a candidate's registration as forward evidence.
        if parse_utc_timestamp(signal["registered_at"]) <= parse_utc_timestamp(registration_template["registered_at"]):
            continue
        entry = opens[symbol, window[0]]
        exit_price = opens[symbol, window[1]]
        gross = exit_price / entry - 1
        # Existing paper league uses 25 bps per side. Do not reuse ledger's
        # 20-bps round-trip return field as though it were the league's costs.
        net = signal["signal"] * (gross - 0.005)
        observed.append({"candidate_id": symbol+"::"+strategy,
                         "window": "|".join(window), "net_return": net,
                         "evidence_sha256": ledger["head_sha256"]})
    result = score_shadow_league(regs, observed,
        required_windows=["|".join(w) for w in windows])
    result["evidence_kind"] = "AUDITED_PAPER_OBSERVATIONAL_BASELINE"
    result["warning"] = "A ledger hash proves consistency, not provider authenticity. Fixed strategy baselines are not independently autonomous agents."
    return result
