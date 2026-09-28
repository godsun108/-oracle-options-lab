from datetime import datetime, timezone
from oracle_q.options_provider import TradierOptionsProvider

class Response:
    def __init__(self,payload): self.payload=payload
    def raise_for_status(self): pass
    def json(self): return self.payload
class Session:
    def get(self,url,params,headers,timeout):
        if url.endswith("/expirations"): return Response({"expirations":{"date":["2026-10-02"]}})
        return Response({"options":{"option":[{"symbol":"SPY261002C00800000","expiration_date":"2026-10-02",
          "option_type":"call","strike":800,"bid":1.2,"ask":1.25,"open_interest":123,"volume":45,"trade_date":1}]}})

def test_tradier_adapter_is_read_only_and_provenance_bearing():
    p=TradierOptionsProvider("test",sandbox=True,session=Session())
    assert p.expirations("SPY")==["2026-10-02"]
    q=p.chain("SPY","2026-10-02",datetime(2026,9,28,tzinfo=timezone.utc))[0]
    assert q.provider=="tradier" and q.environment=="sandbox-delayed"
    assert q.bid==1.2 and q.ask==1.25 and q.open_interest==123
    assert len(q.raw_hash)==64
    assert not hasattr(p,"place_order")
