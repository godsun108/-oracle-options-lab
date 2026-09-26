"""Bridge frozen Oracle signal v1 to the proof-of-edge engine.

Signal is formed at close[t]. Evaluation uses close[t+1]/close[t]-1,
so no same-bar future return is visible to the signal.
"""
from __future__ import annotations
import csv
from pathlib import Path
import pandas as pd
from oracle_q.canonical_signal import canonical_signal_v1, SPEC_VERSION

def build_signal_returns(frame: pd.DataFrame) -> pd.DataFrame:
    if "close" not in frame.columns:
        raise ValueError("frame must contain close")
    x=frame.copy()
    x["close"]=pd.to_numeric(x["close"],errors="raise")
    sig=canonical_signal_v1(x)
    x["signal"]=sig.astype(int)
    x["return"]=x["close"].shift(-1)/x["close"]-1
    if "date" in x.columns:
        x["timestamp"]=x["date"].astype(str)
    elif isinstance(x.index,pd.DatetimeIndex):
        x["timestamp"]=x.index.astype(str)
    else:
        x["timestamp"]=x.index.astype(str)
    return x.loc[x["return"].notna(),["timestamp","signal","return"]]

def write_signal_returns(frame: pd.DataFrame,path: str|Path) -> Path:
    out=Path(path)
    build_signal_returns(frame).to_csv(out,index=False)
    return out

def provenance() -> dict:
    return {
      "signal_spec":SPEC_VERSION,
      "execution_assumption":"signal at close[t], evaluate close[t] to close[t+1]",
      "instrument":"underlying",
      "options_pnl":False,
    }
