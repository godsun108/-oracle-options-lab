import pandas as pd
from oracle_q.canonical_signal import canonical_signal_v1

def _frame(n=260):
    d=pd.date_range("2020-01-01", periods=n, freq="D")
    close=pd.Series([100+i*.1 for i in range(n)],dtype=float)
    close.iloc[-1]=close.iloc[-7]*0.98
    return pd.DataFrame({"date":d,"close":close})

def test_rule_matches_declared_formula():
    x=_frame()
    got=canonical_signal_v1(x)
    expected=(x.close.pct_change(6)<=-0.01)&(x.close>x.close.rolling(200).mean())
    pd.testing.assert_series_equal(got.reset_index(drop=True),expected.fillna(False).reset_index(drop=True),check_names=False)

def test_future_append_does_not_change_past():
    x=_frame()
    before=canonical_signal_v1(x)
    future=pd.DataFrame({"date":pd.date_range(x.date.iloc[-1]+pd.Timedelta(days=1),periods=20,freq="D"),"close":[130.0]*20})
    after=canonical_signal_v1(pd.concat([x,future],ignore_index=True)).iloc[:len(x)]
    pd.testing.assert_series_equal(before.reset_index(drop=True),after.reset_index(drop=True),check_names=False)
