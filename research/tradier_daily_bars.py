"""Validate completed Tradier daily OHLC bars for read-only paper research.

No order placement, strategy selection, or live execution.
"""
import datetime as dt
import math
from research.multi_market_observer import eligible_cutoff

def validate_daily_bars(rows, now=None):
    cutoff=eligible_cutoff(now)
    if not isinstance(rows,list):
        raise ValueError("bars must be a list")
    clean=[]
    seen=set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("invalid bar")
        try:
            day=dt.date.fromisoformat(str(row["date"]))
            if day>cutoff:
                continue
            if day.weekday()>=5 or day.isoformat() in seen:
                raise ValueError("weekend or duplicate daily bar")
            prices=[float(row[k]) for k in ("open","high","low","close")]
            if not all(math.isfinite(v) and v>0 for v in prices):
                raise ValueError("non-finite or nonpositive price")
            o,h,l,c=prices
            if not l<=min(o,c)<=max(o,c)<=h:
                raise ValueError("inconsistent OHLC")
            seen.add(day.isoformat())
            clean.append({"time":day.isoformat(),"open":o,"high":h,"low":l,"close":c})
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError("invalid Tradier daily bar") from exc
    clean.sort(key=lambda x:x["time"])
    return clean
