from oracle_q.underlying_provider import StooqDailyProvider
class R:
    text="Date,Open,High,Low,Close,Volume\n2026-10-02,1,2,1,1.5,10\n2026-10-05,2,3,2,2.5,20\n"
    def raise_for_status(self): pass
class S:
    def get(self,url,params,timeout): return R()
def test_stooq_daily_normalizes_and_hashes():
    x,m=StooqDailyProvider(S()).history("SPY")
    assert list(x.columns)==["date","close"]
    assert x.iloc[-1].close==2.5 and m["data_cutoff"]=="2026-10-05"
    assert m["provider"]=="stooq" and len(m["raw_sha256"])==64
