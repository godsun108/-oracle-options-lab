from oracle_q.prospective_maturity import classify

def sample(flag=False,state="NO_SIGNAL",item=None):
 return {"canonical_signal":{"signal_date":"2026-10-05","signal":flag},
 "prospective_options":{"status":state,"selected_contract":item}}

def test_no_signal():
 assert classify(sample(),[])["state"]=="NO_SIGNAL"

def test_waits_for_two_later_sessions():
 x=sample(True,"OBSERVED",{"symbol":"X"})
 assert classify(x,["2026-10-06"])["state"]=="PENDING"

def test_ready_after_two_later_sessions():
 x=sample(True,"OBSERVED",{"symbol":"X"})
 r=classify(x,["2026-10-06","2026-10-07"])
 assert r["state"]=="READY"
 assert r["evaluation_date"]=="2026-10-07"

def test_missing_observation():
 assert classify(sample(True,"NO_VALID_CONTRACT"),[])["state"]=="NO_OBSERVATION"
