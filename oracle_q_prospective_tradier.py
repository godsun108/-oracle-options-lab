"""Prospective Oracle-Q + Tradier observation CLI. Research only."""
from datetime import date, timedelta
import os, json
from oracle_q.forward import evaluate_latest
from oracle_q.options_provider import TradierOptionsProvider
from oracle_q.prospective_options import observe, to_json
from oracle_q.underlying_provider import StooqDailyProvider

if __name__=="__main__":
    frame,source=StooqDailyProvider().history("SPY")
    signal=evaluate_latest(frame)
    if source["data_cutoff"] != signal.data_cutoff:
        raise SystemExit("underlying provenance cutoff mismatch")
    provider=TradierOptionsProvider(token=os.getenv("TRADIER_PRODUCTION_TOKEN"),sandbox=False)
    minimum=date.fromisoformat(signal.signal_date)+timedelta(days=1)
    result=observe(provider,"SPY",signal.signal_date,signal.signal,signal.close,minimum)
    print("ORACLE UNDERLYING",json.dumps(source,sort_keys=True))
    print("ORACLE PROSPECTIVE",to_json(result))
