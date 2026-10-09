"""Unify PACO SPX trigger, quote anomaly screening, and exit review.

This orchestrates *research observations*, not fills, trades, or broker actions.
No synthetic performance is reported from a signal or a quote alone.
"""
from datetime import datetime
from research.spx_ath_spy_puts import signal
from research.options_discount_scanner import screen
from research.paco_terminator import evaluate

def observe(*, spx_bars, spy_contracts, option_quotes, positions, now_iso,
            regime=None):
    now=datetime.fromisoformat(now_iso)
    if now.tzinfo is None:
        raise ValueError("timezone-aware now_iso required")
    as_of=now.date().isoformat()
    put_signal=signal(spx_bars,spy_contracts,as_of=as_of)
    # HIGH only after record-close signal, not simply because market rose.
    inferred="HIGH" if put_signal.get("spx_record_close") else "NEUTRAL"
    if regime is not None and regime not in ("HIGH","LOW","NEUTRAL"):
        raise ValueError("invalid market regime")
    effective_regime=regime if regime is not None else inferred
    findings=screen(option_quotes,market_regime=effective_regime)
    review=evaluate(positions,{q["symbol"]:q for q in option_quotes
                              if "symbol" in q and "age_seconds" in q and "bid_size" in q},
                    now_iso=now_iso)
    return {"schema":"oracle-paco-research-observation-v1",
            "timestamp":now_iso,"market_regime":effective_regime,
            "put_signal":put_signal,"bargain_candidates":findings,
            "position_review":review,"paper_fills":[],"executed_trades":[],
            "strategy_performance_available":False,"orders_enabled":False,
            "note":"Observations only. Quote references are unverified; no fills, positions or returns inferred."}
