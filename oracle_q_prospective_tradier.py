"""Prospective Oracle-Q + Tradier observation CLI. Research only."""
from datetime import date, timedelta
import os, json
from pathlib import Path
from oracle_q.seldon_sidecar import attach_if_eligible, unavailable
from oracle_q.forward import evaluate_latest
from oracle_q.options_provider import TradierOptionsProvider
from oracle_q.prospective_options import observe, to_json
from oracle_q.underlying_provider import TradierDailyProvider

if __name__=="__main__":
    frame,source=TradierDailyProvider(token=os.getenv("TRADIER_PRODUCTION_TOKEN")).history("SPY")
    signal=evaluate_latest(frame)
    if source["data_cutoff"] != signal.data_cutoff:
        raise SystemExit("underlying provenance cutoff mismatch")
    provider=TradierOptionsProvider(token=os.getenv("TRADIER_PRODUCTION_TOKEN"),sandbox=False)
    minimum=date.fromisoformat(signal.signal_date)+timedelta(days=1)
    result=observe(provider,"SPY",signal.signal_date,signal.signal,signal.close,minimum)
    sidecar_path=Path("seldon_artifact/seldon_prospective_macro_12m.json")
    sidecar=attach_if_eligible(json.loads(sidecar_path.read_text()),signal.signal_date) if sidecar_path.exists() else unavailable()
    envelope={"schema_version":"oracle-q-forward-evidence-v1","underlying_source":source,"seldon_sidecar":sidecar,
              "canonical_signal":signal.__dict__,"prospective_options":result.__dict__,
              "orders_enabled":False,"research_only":True}
    print("ORACLE FORWARD EVIDENCE",json.dumps(envelope,sort_keys=True,separators=(",",":")))
