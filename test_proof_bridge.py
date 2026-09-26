import pandas as pd
from oracle_q.proof_bridge import build_signal_returns, provenance

def test_bridge_uses_next_bar_return():
    n=205
    close=[100.0]*n
    close[-2]=98.0
    close[-1]=107.8
    f=pd.DataFrame({"date":pd.date_range("2020-01-01",periods=n),"close":close})
    out=build_signal_returns(f)
    # Every emitted return must be the following close divided by current close.
    expected=f["close"].shift(-1)/f["close"]-1
    for i,row in out.iterrows():
        assert abs(row["return"]-expected.iloc[i])<1e-12

def test_provenance_never_calls_underlying_test_options_pnl():
    p=provenance()
    assert p["signal_spec"]=="oracle-signal-v1"
    assert p["options_pnl"] is False
