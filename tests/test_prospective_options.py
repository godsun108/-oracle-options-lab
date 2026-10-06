from datetime import date, datetime, timezone
from oracle_q.options_provider import OptionQuote
from oracle_q.prospective_options import first_expiration_on_or_after, select_atm_call, observe

def q(symbol,strike,bid,ask,oi=1,typ="call"):
    return OptionQuote("tradier","brokerage-realtime","SPY",symbol,"2026-10-09",typ,strike,bid,ask,oi,0,
      "2026-10-06T20:00:00+00:00",None,symbol.ljust(64,"0")[:64])

def test_frozen_selection_is_deterministic_and_read_only():
    xs=[q("B",600,1,1.2,10),q("A",600,1,1.1,10),q("C",601,2,2.1,999),q("P",600,1,1.1,999,"put")]
    assert select_atm_call(xs,600).symbol=="A"
    assert first_expiration_on_or_after(["2026-10-06","2026-10-09"],date(2026,10,7))=="2026-10-09"

def test_no_signal_makes_no_provider_request():
    class P:
        def expirations(self,*a): raise AssertionError("provider should not be called")
    x=observe(P(),"SPY","2026-10-06",False,600,date(2026,10,7),datetime(2026,10,6,tzinfo=timezone.utc))
    assert x.status=="NO_SIGNAL" and x.chain_rows==0 and x.selected_contract is None

def test_observation_has_chain_provenance():
    class P:
        def expirations(self,s): return ["2026-10-09"]
        def chain(self,s,e,now): return [q("A",600,1,1.1,12)]
    x=observe(P(),"SPY","2026-10-06",True,600,date(2026,10,7),datetime(2026,10,6,tzinfo=timezone.utc))
    assert x.status=="OBSERVED" and x.selected_contract["symbol"]=="A" and len(x.chain_hash)==64
