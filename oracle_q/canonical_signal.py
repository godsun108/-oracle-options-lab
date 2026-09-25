"""Frozen Oracle canonical underlying signal specifications."""
import pandas as pd

SPEC_VERSION="oracle-signal-v1"

def canonical_signal_v1(frame: pd.DataFrame) -> pd.Series:
    """Return the frozen v1 signal using only date/close history through each row."""
    if "close" not in frame.columns:
        raise ValueError("frame must contain close")
    close=pd.to_numeric(frame["close"],errors="raise")
    ret6=close.pct_change(6)
    ma200=close.rolling(200).mean()
    return ((ret6<=-0.01)&(close>ma200)).fillna(False)
