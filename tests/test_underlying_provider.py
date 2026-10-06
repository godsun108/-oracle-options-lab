from datetime import date
from oracle_q.underlying_provider import TradierDailyProvider

class R:
    def raise_for_status(self): pass
    def json(self): return {"history":{"day":[
      {"date":"2026-10-02","close":1.5},{"date":"2026-10-05","close":2.5}]}}
class S:
    def get(self,url,params,headers,timeout):
        assert url.endswith("/markets/history")
        assert headers["Authorization"]=="Bearer test"
        assert params["interval"]=="daily"
        return R()

def test_tradier_daily_normalizes_and_hashes():
    x,m=TradierDailyProvider("test",S()).history("SPY",date(2026,1,1),date(2026,10,6))
    assert list(x.columns)==["date","close"]
    assert x.iloc[-1].close==2.5 and m["data_cutoff"]=="2026-10-05"
    assert m["provider"]=="tradier" and m["environment"]=="brokerage-realtime"
    assert len(m["raw_sha256"])==64

from datetime import datetime
from zoneinfo import ZoneInfo

def test_tradier_drops_current_partial_daily_bar_before_close():
    s=FakeSession({"history":{"day":[{"date":"2026-10-05","close":"780"},{"date":"2026-10-06","close":"781"}]}})
    p=TradierDailyProvider("x",session=s,now=datetime(2026,10,6,11,0,tzinfo=ZoneInfo("America/New_York")))
    frame,meta=p.history("SPY",start=date(2026,10,5),end=date(2026,10,6))
    assert frame.iloc[-1]["date"].date().isoformat()=="2026-10-05"
    assert meta["partial_current_session_removed"] is True

def test_tradier_keeps_current_daily_bar_after_close():
    s=FakeSession({"history":{"day":[{"date":"2026-10-05","close":"780"},{"date":"2026-10-06","close":"781"}]}})
    p=TradierDailyProvider("x",session=s,now=datetime(2026,10,6,16,30,tzinfo=ZoneInfo("America/New_York")))
    frame,meta=p.history("SPY",start=date(2026,10,5),end=date(2026,10,6))
    assert frame.iloc[-1]["date"].date().isoformat()=="2026-10-06"
    assert meta["partial_current_session_removed"] is False
