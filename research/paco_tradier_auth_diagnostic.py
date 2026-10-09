"""Non-secret Tradier read-only API authentication diagnostics.

Compare the *same* token and production host against underlying and options
endpoints. Never print tokens, request headers, or response bodies.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime,timezone

BASE="https://api.tradier.com/v1"
PATHS={
    "underlying_quotes":"/markets/quotes?symbols=SPY",
    "options_expirations":"/markets/options/expirations?symbol=SPY",
}

def probe(token, *, opener=urllib.request.urlopen):
    if not token:raise ValueError("TRADIER_TOKEN missing")
    results={}
    for label,path in PATHS.items():
        req=urllib.request.Request(BASE+path,headers={
            "Authorization":"Bearer "+token,"Accept":"application/json",
            "User-Agent":"oracle-paco-readonly-auth-diagnostic/1"})
        try:
            with opener(req,timeout=15) as response:
                results[label]={"http_status":response.status,"accessible":response.status==200}
        except urllib.error.HTTPError as exc:
            results[label]={"http_status":exc.code,"accessible":False}
        except (urllib.error.URLError,TimeoutError) as exc:
            results[label]={"http_status":None,"accessible":False,
                            "error_type":type(exc).__name__}
    underlying=results["underlying_quotes"]["http_status"]
    options=results["options_expirations"]["http_status"]
    if underlying==200 and options==401:
        diagnosis="OPTIONS_ENDPOINT_REJECTS_TOKEN_WHILE_UNDERLYING_WORKS"
    elif underlying==401 and options==401:
        diagnosis="TOKEN_INVALID_FOR_PRODUCTION_OR_EXPIRED"
    elif underlying==200 and options==200:
        diagnosis="BOTH_READ_ONLY_ENDPOINTS_ACCESSIBLE"
    else:
        diagnosis="MIXED_OR_INCONCLUSIVE"
    return {"schema":"paco-tradier-auth-diagnostic-v1",
            "host":"api.tradier.com","timestamp":datetime.now(timezone.utc).isoformat(),
            "results":results,"diagnosis":diagnosis,
            "orders_enabled":False,"token_logged":False,
            "note":"401 can indicate invalid token or production/sandbox mismatch; no cause assumed."}

def main():
    from pathlib import Path
    result=probe(os.getenv("TRADIER_TOKEN",""))
    path=Path(os.getenv("PACO_AUTH_REPORT","paco_auth_diagnostic.json"))
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PACO Tradier auth diagnosis:",result["diagnosis"])
    for key,val in result["results"].items():
        print(key,"HTTP",val["http_status"])
if __name__=="__main__":main()
