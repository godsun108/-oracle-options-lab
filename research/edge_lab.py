"""Read-only, pre-registered multi-market ETF proxy backtests; no orders or fills."""
import argparse
import hashlib
import json
import math
import os
import time
import urllib.error
from pathlib import Path
from research.multi_market_observer import SYMBOLS, request_history
from datetime import date, datetime, timezone, timedelta
from research.edge_session_calendar import eligible_cutoff, is_session, validate_sequence, CALENDAR_SHA256

WARMUP = 200
COST_PER_SIDE = 0.001  # conservative 10 basis points on each position transition
INITIAL_CASH = 2000.0
IDS = ("tsmom_63", "trend_200", "reversal_5")

def forward_start(cutoff):
    """Exactly 200 scheduled sessions, chosen before fetching any prices."""
    day=cutoff; count=0
    while True:
        if is_session(day):
            count+=1
            if count==WARMUP:
                return day.isoformat()
        day-=timedelta(days=1)


def evaluate_forward(symbol, raw, registry, *, now=None):
    if symbol not in SYMBOLS or symbol not in registry["proxy_symbols"]:
        raise ValueError("unregistered market proxy")
    cutoff=eligible_cutoff(now); start=forward_start(cutoff)
    if not isinstance(raw,list) or any(not isinstance(r,dict) or not start<=str(r.get("date",""))[:10]<=cutoff.isoformat() for r in raw):
        raise ValueError("forward source outside predeclared request window")
    bars=validate_open_bars(raw,now=now)
    if len(bars)!=WARMUP or bars[0]["time"]!=start:
        raise ValueError("incomplete forward lookback")
    validate_sequence([b["time"] for b in bars],now=now,require_fresh=True)
    return {"symbol":symbol,"status":"FORWARD_OPEN_INPUTS_ONLY",
            "bars":len(bars),"first_date":start,"last_completed_date":bars[-1]["time"],
            "price_field":"open_only","recent_opens":bars[-25:],
            "open_series_sha256":hashlib.sha256(json.dumps(bars,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
            "strategies":[{"strategy_id":sid,"next_session_paper_signal":signal(sid,[b["open"] for b in bars]),
                           "next_session_fill_verified":False,"edge_proven":False} for sid in IDS],
            "historical_backtest_status":"NOT_RUN_IN_FORWARD_COLLECTION",
            "orders_enabled":False,"edge_proven":False,"forward_paper_verified":False,
            "warnings":["Exactly 200 sessions requested independently of source validity; no missing rows dropped or repaired.",
                        "This is not a historical performance report or proof of executable fills.",
                        "Older historical source defects remain unresolved; publication time is not attested."]}

def fetch_with_transport_retries(fetch, args, attempts, *, sleep=time.sleep):
    """At most three reads; never retry prices, parsing, auth or permissions.

    Trace contains only allowlisted metadata, never exception messages/headers.
    Successful responses are evaluated once, outside this transport wrapper.
    """
    for number in range(1, 4):
        attempt = {"attempt":number, "started_at":datetime.now(timezone.utc).isoformat()}
        try:
            rows = fetch(*args)
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, ValueError, TypeError, KeyError) as exc:
            status = exc.code if isinstance(exc, urllib.error.HTTPError) else None
            retryable = (status in (502,503,504) if status is not None else
                         isinstance(exc,(TimeoutError,ConnectionResetError)) or
                         isinstance(getattr(exc,"reason",None),(TimeoutError,ConnectionResetError)))
            attempt.update({"finished_at":datetime.now(timezone.utc).isoformat(),
                            "status":"FETCH_FAILED", "error_type":type(exc).__name__,
                            "http_status":status,"retry_scheduled":retryable and number<3})
            attempts.append(attempt)
            if not retryable or number==3:
                raise
            sleep(number)  # fixed 1s, 2s; never retry until a dataset passes
        else:
            attempt.update({"finished_at":datetime.now(timezone.utc).isoformat(),
                            "status":"RESPONSE_RECEIVED","retry_scheduled":False})
            attempts.append(attempt)
            return rows

def signal(strategy, closes):
    if len(closes) < WARMUP:
        raise ValueError("insufficient prior completed closes")
    if strategy == "tsmom_63":
        return int(closes[-1] > closes[-64])
    if strategy == "trend_200":
        return int(closes[-1] > sum(closes[-200:]) / 200)
    if strategy == "reversal_5":
        return int(closes[-1] < closes[-6])
    raise ValueError("unregistered strategy")

def segment(bars, strategy, start, stop, *, benchmark=False):
    """Signal from open[i-1] or earlier; hypothetical entry at open[i]."""
    cash = INITIAL_CASH
    peak = cash
    worst = 0.0
    position = 0
    transitions = 0
    invested_days = 0
    for i in range(start, stop):
        wanted = 1 if benchmark else signal(strategy, [b["open"] for b in bars[:i]])
        # Charge on the open where a position is changed, not on the signal bar.
        if wanted != position:
            cash *= (1 - COST_PER_SIDE)
            transitions += 1
        position = wanted
        invested_days += position
        cash *= 1 + position * (bars[i+1]["open"] / bars[i]["open"] - 1)
        if not math.isfinite(cash) or cash <= 0:
            raise ValueError("invalid simulated equity")
        peak = max(peak, cash)
        worst = min(worst, cash / peak - 1)
    if position:
        cash *= (1 - COST_PER_SIDE)
        transitions += 1
    return {"observations":stop-start,"net_return_pct":round(100*(cash/INITIAL_CASH-1),4),
            "max_drawdown_pct":round(100*worst,4),"position_changes":transitions,
            "invested_days":invested_days,"capital_reference_usd":INITIAL_CASH,
            "fill_verified":False,"cost_per_position_transition_bps":10}

def validate_open_bars(rows, *, now=None):
    """Validate only opens used by the model; never repair adjusted-close anomalies."""
    if not isinstance(rows,list):
        raise ValueError("opening-price observations must be a list")
    cutoff=eligible_cutoff(now)
    found={}
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("invalid open observation")
        try:
            day=date.fromisoformat(str(row["date"])[:10])
            if day>cutoff:
                continue
            if not is_session(day) or day.isoformat() in found:
                raise ValueError("weekend or duplicate open observation")
            price=float(row["open"])
            if not math.isfinite(price) or price<=0:
                raise ValueError("invalid opening price")
            found[day.isoformat()]=price
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            raise ValueError("invalid open observation") from exc
    if found:
        validate_sequence(sorted(found))
    return [{"time":day,"open":price} for day,price in sorted(found.items())]

def evaluate(symbol, raw, registry, *, now=None):
    if symbol not in SYMBOLS or symbol not in registry["proxy_symbols"]:
        raise ValueError("unregistered market proxy")
    bars = validate_open_bars(raw, now=now)
    source_ohlc_diagnostic=diagnose_raw_bars(raw,now=now)
    if len(bars) < 320:
        return {"symbol":symbol,"status":"INSUFFICIENT_COMPLETED_BARS",
                "bars":len(bars),"orders_enabled":False,"edge_proven":False}
    validate_sequence([b["time"] for b in bars], now=now, require_fresh=True)
    # The last bar is only used for a *future* signal; no next-open price is available.
    first = WARMUP
    stop = len(bars)-1
    split = first + int((stop-first)*0.7)
    if split-first < 30 or stop-split < 30:
        raise ValueError("chronological train/test split too small")
    payload_hash = hashlib.sha256(json.dumps(bars,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    rows = []
    for strategy in IDS:
        rows.append({"strategy_id":strategy,
                     "train":segment(bars,strategy,first,split),
                     "holdout":segment(bars,strategy,split,stop),
                     "holdout_buy_hold":segment(bars,strategy,split,stop,benchmark=True),
                     "next_session_paper_signal":signal(strategy,[b["open"] for b in bars]),
                     "next_session_fill_verified":False,"edge_proven":False})
    return {"symbol":symbol,"status":"HISTORICAL_OPEN_PROXY_BACKTEST_ONLY",
            "bars":len(bars),"first_date":bars[0]["time"],"last_completed_date":bars[-1]["time"],
            "train_start":bars[first]["time"],"holdout_start":bars[split]["time"],
            "holdout_end":bars[stop]["time"],"open_series_sha256":payload_hash,"price_field":"open_only",
            "source_ohlc_diagnostic":source_ohlc_diagnostic,
            "recent_opens":bars[-25:],
            "close_ohlc_validation":"NOT_USED_IN_OPEN_ONLY_MODEL",
            "strategies":rows,"orders_enabled":False,"forward_paper_verified":False,
            "edge_proven":False,"warnings":["Open-only signals lag completed opening prices and do not replicate close-based published strategies.",
              "ETF proxies are not exact replications of cited academic strategies.",
              "Chronological holdout is historical, not independently forward paper-traded.",
              "Corporate actions, financing, borrow, taxes, and data adjustments are not independently verified.",
              "No actual fills, live orders, or statistical edge established."]}

def diagnose_raw_bars(rows, *, now=None):
    """Explain blocked input without silently discarding bad market observations."""
    if not isinstance(rows,list):
        return {"reason":"NOT_A_LIST"}
    cutoff=eligible_cutoff(now)
    seen=set()
    for row in rows:
        if not isinstance(row,dict):
            return {"reason":"NON_OBJECT_BAR"}
        day=str(row.get("date",""))[:10]
        try:
            from datetime import date
            parsed=date.fromisoformat(day)
            if parsed>cutoff:
                continue
            if parsed.weekday()>=5:
                return {"reason":"WEEKEND_BAR","date":day}
            if day in seen:
                return {"reason":"DUPLICATE_BAR","date":day}
            seen.add(day)
            o,h,l,c=[float(row[k]) for k in ("open","high","low","close")]
            if not all(math.isfinite(x) and x>0 for x in (o,h,l,c)):
                return {"reason":"NONFINITE_OR_NONPOSITIVE_OHLC","date":day}
            if not l<=min(o,c)<=max(o,c)<=h:
                return {"reason":"INCONSISTENT_OHLC","date":day}
        except (KeyError,TypeError,ValueError,OverflowError):
            return {"reason":"MALFORMED_OHLC","date":day}
    return {"reason":"DOWNSTREAM_VALIDATION_FAILURE"}

def run(registry, token, *, fetch=request_history, now=None, mode="historical"):
    if mode not in ("historical","forward"):
        raise ValueError("unknown collection mode")
    if registry.get("schema") != "oracle-q-edge-registry-v1" or registry.get("enabled_for_execution") is not False:
        raise ValueError("invalid research-only edge registry")
    if {c["id"] for c in registry["candidates"] if c.get("testable_with_current_etf_data")} != set(IDS):
        raise ValueError("registered backtest strategies do not match implementation")
    if not token:
        raise ValueError("missing read-only data credential")
    now = now or datetime.now(timezone.utc)
    cutoff=eligible_cutoff(now)
    start=forward_start(cutoff) if mode=="forward" else (cutoff-timedelta(days=850)).isoformat()
    reports=[]
    for symbol in registry["proxy_symbols"]:
        raw=None
        source_fields={"fetch_attempts":[]}
        try:
            request_started_at=datetime.now(timezone.utc).isoformat()
            raw=fetch_with_transport_retries(fetch,(symbol,token,start,cutoff.isoformat()),source_fields["fetch_attempts"])
            received_at=datetime.now(timezone.utc).isoformat()
            source_fields["source_received_at"]=received_at
            source_fields["source_payload_sha256"]=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            source_fields["source_evidence"]={
                "schema":"oracle-q-parsed-history-evidence-v1",
                "symbol":symbol,"provider":"tradier",
                "request_start_date":start,"request_end_date":cutoff.isoformat(),
                "request_started_at":request_started_at,"received_at":received_at,
                "publication_at":None,"publication_time_verified":False,
                "representation":"parsed history rows, not raw HTTP bytes",
                "rows":raw}
            evaluator=evaluate_forward if mode=="forward" else evaluate
            evaluated=evaluator(symbol,raw,registry,now=now)
            evaluated.update(source_fields)
            reports.append(evaluated)
        except (ValueError,KeyError,TypeError,TimeoutError,OSError) as exc:
            if raw is not None and "source_evidence" not in source_fields:
                # Preserve nonstandard parsed values as text, never corrected rows.
                rejected=json.dumps(raw,sort_keys=True,separators=(",",":"),allow_nan=True)
                source_fields["rejected_parsed_payload_text"]=rejected
                source_fields["rejected_parsed_payload_text_sha256"]=hashlib.sha256(rejected.encode()).hexdigest()
                source_fields["rejected_payload_format"]="Python JSON text; may contain NaN/Infinity; not eligible source evidence"
            detail=diagnose_raw_bars(raw,now=now) if raw is not None else {"reason":"FETCH_UNAVAILABLE"}
            reports.append({"symbol":symbol,"status":"DATA_OR_VALIDATION_FAILURE",
                            **source_fields,"error_type":type(exc).__name__,"diagnostic":detail,
                            "orders_enabled":False,"edge_proven":False})
    return {"schema":"oracle-q-edge-lab-v1","status":"FORWARD_INPUT_RESEARCH_ONLY" if mode=="forward" else "HISTORICAL_RESEARCH_ONLY",
            "collection_mode":mode,
            "observed_at":datetime.now(timezone.utc).isoformat(),
            "evaluation_cutoff_at":now.isoformat(),
            "calendar_sha256":CALENDAR_SHA256,
            "cutoff":cutoff.isoformat(),"provider":"tradier","orders_enabled":False,
            "forward_paper_verified":False,"edge_proven":False,
            "cost_model":"10 bps per entry or exit, open-to-next-open, unlevered long/cash",
            "signal_source":"prior completed opens only; no closes used",
            "reports":reports}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registry",default="research/edge_registry.json")
    p.add_argument("--output",default="edge_lab_report.json")
    p.add_argument("--mode",choices=("historical","forward"),default="historical")
    a=p.parse_args()
    registry=json.loads(Path(a.registry).read_text())
    report=run(registry,os.getenv("TRADIER_TOKEN",""),mode=a.mode)
    Path(a.output).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("Edge lab:",[(r["symbol"],r["status"]) for r in report["reports"]])
    expected="FORWARD_OPEN_INPUTS_ONLY" if a.mode=="forward" else "HISTORICAL_OPEN_PROXY_BACKTEST_ONLY"
    if any(r["status"]!=expected for r in report["reports"]):
        raise SystemExit(1)

if __name__=="__main__":
    main()
