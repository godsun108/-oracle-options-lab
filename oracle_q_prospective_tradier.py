"""Prospective Oracle-Q + Tradier observation CLI. Research only."""
from datetime import date, timedelta
import os
from oracle_q.observe import load_source
from oracle_q.forward import evaluate_latest
from oracle_q.options_provider import TradierOptionsProvider
from oracle_q.prospective_options import observe, to_json

if __name__=="__main__":
    frame=load_source()
    signal=evaluate_latest(frame)
    minimum=date.fromisoformat(signal.signal_date)+timedelta(days=1)
    provider=TradierOptionsProvider(token=os.getenv("TRADIER_PRODUCTION_TOKEN"),sandbox=False)
    print(to_json(observe(provider,"SPY",signal.signal_date,signal.signal,signal.close,minimum)))
