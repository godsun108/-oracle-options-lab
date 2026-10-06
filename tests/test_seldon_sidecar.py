import pytest
from oracle_q.seldon_sidecar import attach,unavailable
def sample():
    return {"as_of":"2026-10-06","source_experiment":"seldon-prospective-macro-v1","target":"UNRATE higher 12m","horizon":"12m","probability":3/7,"baseline_probability":.35,"evidence":{"n_train":101},"vintage_safe":True,"status":"RESEARCH_FEATURE_ONLY"}
def test_attach_is_hashed_and_cannot_modify_oracle():
    x=attach(sample(),"2026-10-06")
    assert x["state"]=="ATTACHED" and len(x["payload_sha256"])==64
    assert x["research_only"] and x["can_modify_oracle_signal"] is False
def test_future_sidecar_fails_closed():
    p=sample();p["as_of"]="2026-10-07"
    with pytest.raises(ValueError): attach(p,"2026-10-06")
def test_missing_is_explicit():
    x=unavailable();assert x["state"]=="MISSING" and x["can_modify_oracle_signal"] is False
