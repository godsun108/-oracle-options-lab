"""SPX record-close trigger for SPY put research. No broker orders.

A signal is not a trade: actual option quotes, DTE, costs and forward marks
are required before any options P&L can be calculated.
"""
from datetime import date

def signal(spx_bars, spy_contracts, *, as_of, min_dte=30, max_dte=60, prior_lookback=None):
    """Bars: chronological dicts with date and close; contracts: dicts with
    symbol, type, expiration, strike, bid, ask. No look-ahead allowed.
    A fresh record closing high strictly exceeds every prior supplied close.
    """
    if not isinstance(as_of,str):
        raise ValueError("as_of required")
    day=date.fromisoformat(as_of)
    if not (0<min_dte<=max_dte):
        raise ValueError("invalid DTE window")
    bars=[b for b in spx_bars if date.fromisoformat(b["date"])<=day]
    if len(bars)<252 or bars[-1]["date"]!=as_of:
        return {"status":"INSUFFICIENT_HISTORY","orders_enabled":False,"candidates":[]}
    if prior_lookback is not None:
        raise ValueError("all-time-high requires full available history, not a rolling lookback")
    history=bars[:-1]
    peak=max(float(b["close"]) for b in history)
    close=float(bars[-1]["close"])
    ath=close>peak
    candidates=[]
    if ath:
        for c in spy_contracts:
            try:
                expiry=date.fromisoformat(c["expiration"])
                dte=(expiry-day).days
                bid=float(c["bid"])
                ask=float(c["ask"])
                if c["type"].lower()=="put" and min_dte<=dte<=max_dte and 0<=bid<=ask and ask>0:
                    candidates.append({"symbol":c["symbol"],"expiration":c["expiration"],"strike":float(c["strike"]),
                                       "dte":dte,"bid":bid,"ask":ask,"spread":ask-bid})
            except (KeyError,ValueError,TypeError):
                continue
    return {"status":"CANDIDATES_REQUIRE_HISTORICAL_OPTION_QUOTES" if ath else "NO_SIGNAL",
            "spx_record_close":ath,"spx_close":close,"previous_max_close":peak,
            "history_bars":len(bars),"trigger_date":as_of,
            "candidates":candidates,"orders_enabled":False,"paper_orders_enabled":False,
            "performance_established":False,
            "note":"Candidates are research only; no entry, fill, exit, or P&L inferred."}
