"""Read-only Tradier production market-data smoke test. No order endpoints exist here."""
from oracle_q.options_provider import TradierOptionsProvider
import json, os, sys

token=os.getenv("TRADIER_PRODUCTION_TOKEN")
if not token:
    raise SystemExit("TRADIER_PRODUCTION_TOKEN secret is required")
p=TradierOptionsProvider(token=token,sandbox=False)
symbol=(os.getenv("TRADIER_SMOKE_SYMBOL") or "SPY").upper()
exp=p.expirations(symbol)
if not exp:
    raise SystemExit("No expirations returned")
chain=p.chain(symbol,exp[0])
if not chain:
    raise SystemExit("No option chain rows returned")
sample=chain[0]
assert sample.provider=="tradier"
assert sample.environment=="brokerage-realtime"
assert len(sample.raw_hash)==64
print("TRADIER READ-ONLY PRODUCTION MARKET-DATA PASS",json.dumps({
 "symbol":symbol,"expiration":exp[0],"expirations":len(exp),"chain_rows":len(chain),
 "sample_contract":sample.symbol,"environment":sample.environment,
 "sample_raw_hash":sample.raw_hash,"orders_enabled":False
},sort_keys=True))
