from datetime import datetime, timezone
import pandas as pd
from oracle_q.forward import evaluate_latest

def frame(n=210):
    return pd.DataFrame({"date":pd.date_range("2026-01-01",periods=n,freq="D"),
                         "close":[100+i*.1 for i in range(n)]})

def test_forward_record_is_versioned_and_hashed():
    x=frame(); r=evaluate_latest(x,datetime(2026,9,25,tzinfo=timezone.utc))
    assert r.spec_version=="oracle-signal-v1"
    assert len(r.input_hash)==64
    assert r.signal_date==x.date.iloc[-1].date().isoformat()
    assert r.data_cutoff==r.signal_date

def test_hash_changes_when_input_changes():
    x=frame(); a=evaluate_latest(x).input_hash
    x.loc[0,"close"]+=1
    b=evaluate_latest(x).input_hash
    assert a!=b
