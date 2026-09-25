"""CLI for prospective Oracle observations. Emits one JSON record to stdout."""
import io, requests, pandas as pd
from oracle_q.forward import evaluate_latest, to_json

SOURCE="https://raw.githubusercontent.com/OStochastic/Daily-SPY-data-from-2000-2025/main/spy_data.csv"

def load_source():
    r=requests.get(SOURCE,timeout=60); r.raise_for_status()
    x=pd.read_csv(io.StringIO(r.text),skiprows=[1,2])
    if x.shape[1]!=6: raise ValueError(f"unexpected SPY schema: {list(x.columns)}")
    x.columns=["date","close","high","low","open","volume"]
    x["date"]=pd.to_datetime(x.date,errors="raise")
    x["close"]=pd.to_numeric(x.close,errors="raise")
    return x[["date","close"]]

if __name__=="__main__":
    print(to_json(evaluate_latest(load_source())))
