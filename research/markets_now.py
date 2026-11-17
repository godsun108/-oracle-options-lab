"""Markets Now: read-only Tradier options scanner and snapshot publisher.

This produces research candidates, never orders. A screen score is a
transparent heuristic, not a probability of profit or a buy recommendation.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


BASE = "https://api.tradier.com/v1"
EASTERN = ZoneInfo("America/New_York")
WATCHLIST = (
    "SPY", "QQQ", "IWM", "DIA", "NVDA", "TSLA", "AMD", "AAPL", "META",
    "AMZN", "MSFT", "GOOGL", "PLTR", "MSTR", "MU", "SOFI", "SMH", "SOXX",
    "XLF", "XLK", "GLD", "SLV", "TLT", "IBIT", "USO", "GDX", "TQQQ",
    "SQQQ", "SOXL", "SOXS",
)
# Start with liquid, unleveraged underlyings. Leveraged ETFs remain visible
# in the watchlist but are deliberately excluded from the initial option scan.
SCAN_SYMBOLS = (
    "SPY", "QQQ", "IWM", "DIA", "NVDA", "TSLA", "AMD", "AAPL",
    "META", "PLTR", "MU", "SMH", "GLD", "TLT",
)
LEVERAGED = {"TQQQ", "SQQQ", "SOXL", "SOXS"}
SCHEMA = "markets-now-snapshot-v1"


def market_session(now: datetime) -> str:
    local = now.astimezone(EASTERN)
    if local.weekday() >= 5:
        return "CLOSED"
    minute = local.hour * 60 + local.minute
    if 570 <= minute < 960:
        return "OPEN"
    if 240 <= minute < 570:
        return "PREMARKET"
    if 960 <= minute < 1200:
        return "AFTERHOURS"
    return "CLOSED"


def _rows(payload: dict, parent: str, child: str) -> list[dict]:
    value = ((payload.get(parent) or {}).get(child) or [])
    if isinstance(value, dict):
        return [value]
    return value if isinstance(value, list) else []


def _get(session, token: str, path: str, params: dict, base: str = BASE) -> dict:
    response = session.get(
        base + path,
        params=params,
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected provider response")
    return payload


def _num(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _rsi(closes: list[float], period: int = 14):
    if len(closes) <= period:
        return None
    changes = [b - a for a, b in zip(closes[-period-1:-1], closes[-period:])]
    gains = sum(max(x, 0) for x in changes) / period
    losses = sum(max(-x, 0) for x in changes) / period
    if losses == 0:
        return 100.0 if gains else 50.0
    return 100 - (100 / (1 + gains / losses))


def _trend(closes: list[float]) -> dict:
    if len(closes) < 50:
        return {"trend": "UNKNOWN", "sma20": None, "sma50": None, "rsi14": None, "return5d_pct": None}
    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes[-50:]) / 50
    last = closes[-1]
    rsi = _rsi(closes)
    ret5 = (last / closes[-6] - 1) * 100 if closes[-6] else None
    if last > sma20 > sma50 and (rsi is None or rsi < 75):
        trend = "BULLISH"
    elif last < sma20 < sma50 and (rsi is None or rsi > 25):
        trend = "BEARISH"
    else:
        trend = "MIXED"
    return {
        "trend": trend, "sma20": round(sma20, 4), "sma50": round(sma50, 4),
        "rsi14": round(rsi, 2) if rsi is not None else None,
        "return5d_pct": round(ret5, 3) if ret5 is not None else None,
    }


def _expiration_for(expirations: list[str], today: date):
    eligible = []
    for item in expirations:
        try:
            d = date.fromisoformat(str(item))
            dte = (d - today).days
            if 30 <= dte <= 60:
                eligible.append((abs(dte - 45), d, dte))
        except ValueError:
            continue
    return min(eligible, default=None, key=lambda x: (x[0], x[1]))


def _quote_timestamp(row: dict):
    values = []
    for key in ("bid_date", "ask_date", "biddate", "askdate"):
        raw = row.get(key)
        if raw in (None, "", 0, "0"):
            continue
        try:
            stamp = float(raw)
            if stamp > 10**12:
                stamp /= 1000
            values.append(datetime.fromtimestamp(stamp, timezone.utc))
        except (ValueError, TypeError, OSError, OverflowError):
            continue
    return min(values) if len(values) == 2 else None


def score_contract(row: dict, trend: str, now: datetime, expiration: str) -> dict | None:
    bid, ask = _num(row.get("bid")), _num(row.get("ask"))
    strike = _num(row.get("strike"))
    if bid is None or ask is None or strike is None or bid <= 0 or ask < bid or ask <= 0:
        return None
    midpoint = (bid + ask) / 2
    if midpoint <= 0:
        return None
    spread_pct = (ask - bid) / midpoint * 100
    if spread_pct > 12:
        return None
    side = str(row.get("option_type") or "").lower()
    if side not in ("call", "put"):
        return None
    try:
        dte = (date.fromisoformat(expiration) - now.astimezone(EASTERN).date()).days
    except ValueError:
        return None
    if not 30 <= dte <= 60:
        return None
    oi = int(_num(row.get("open_interest")) or 0)
    volume = int(_num(row.get("volume")) or 0)
    bid_size = int(_num(row.get("bid_size")) or 0)
    ask_size = int(_num(row.get("ask_size")) or 0)
    if oi < 50 or (bid_size <= 0 and ask_size <= 0):
        return None

    greeks = row.get("greeks") if isinstance(row.get("greeks"), dict) else {}
    delta = _num(greeks.get("delta"))
    iv = _num(greeks.get("mid_iv") or greeks.get("smv_vol") or greeks.get("iv"))
    fit = "NEUTRAL"
    if trend == "BULLISH":
        fit = "ALIGNED" if side == "call" else "COUNTER_TREND"
    elif trend == "BEARISH":
        fit = "ALIGNED" if side == "put" else "COUNTER_TREND"

    # Transparent 100-point screening heuristic; never a win probability.
    liquidity = (10 if oi >= 1000 else 7 if oi >= 500 else 4 if oi >= 100 else 1)
    liquidity += (10 if volume >= 100 else 7 if volume >= 20 else 4 if volume >= 5 else 0)
    liquidity += 5 if bid_size >= 5 and ask_size >= 5 else 2 if bid_size > 0 and ask_size > 0 else 0
    spread_score = 25 if spread_pct <= 3 else 20 if spread_pct <= 5 else 14 if spread_pct <= 8 else 8
    delta_score = 15 if delta is not None and 0.35 <= abs(delta) <= 0.60 else 10 if delta is not None and 0.25 <= abs(delta) <= 0.70 else 0
    dte_score = 15 if 35 <= dte <= 50 else 12
    trend_score = 20 if fit == "ALIGNED" else 8 if fit == "NEUTRAL" else 0
    score = min(100, liquidity + spread_score + delta_score + dte_score + trend_score)
    reasons = [
        f"{oi:,} open interest",
        f"{volume:,} contracts volume",
        f"{spread_pct:.1f}% bid/ask spread",
        f"{dte} days to expiration",
        "Trend aligned" if fit == "ALIGNED" else "Trend mixed" if fit == "NEUTRAL" else "Counter-trend",
    ]
    quote_time = _quote_timestamp(row)
    quote_age = (now - quote_time).total_seconds() if quote_time else None
    timestamp_verified = quote_age is not None and 0 <= quote_age <= 120
    if quote_time and quote_age is not None and (quote_age < 0 or quote_age > 120):
        return None
    return {
        "contract": str(row.get("symbol") or ""),
        "underlying": str(row.get("underlying") or ""),
        "type": side.upper(), "expiration": expiration, "dte": dte,
        "strike": strike, "bid": bid, "ask": ask,
        "spread_pct": round(spread_pct, 2), "open_interest": oi,
        "volume": volume, "bid_size": bid_size, "ask_size": ask_size,
        "delta": round(delta, 4) if delta is not None else None,
        "iv": round(iv, 4) if iv is not None else None,
        "trend": trend, "directional_fit": fit, "screen_score": score,
        "score_label": "SCREENING HEURISTIC — NOT WIN PROBABILITY",
        "reasons": reasons,
        "quote_timestamp": quote_time.isoformat() if quote_time else None,
        "quote_timestamp_verified": timestamp_verified,
        "manual_quote_verification_required": True,
        "orders_enabled": False,
    }


def empty_snapshot(now: datetime, reason: str) -> dict:
    return {
        "schema": SCHEMA, "generated_at_utc": now.astimezone(timezone.utc).isoformat(),
        "market_session": market_session(now), "provider": "tradier",
        "provider_environment": "production-read-only", "feed_status": "UNAVAILABLE",
        "watchlist": [], "candidates": [], "best_candidate": None,
        "orders_enabled": False, "research_only": True, "edge_proven": False,
        "warning": reason,
    }


def collect(token: str | None = None, *, session=None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone-aware now is required")
    token = token or os.getenv("TRADIER_TOKEN")
    if not token:
        return empty_snapshot(now, "TRADIER_TOKEN is not configured in GitHub Actions secrets.")
    if session is None:
        try:
            import requests
        except ImportError:
            return empty_snapshot(now, "The requests dependency is not installed in the scanner environment.")
        session = requests.Session()
    try:
        quote_payload = _get(session, token, "/markets/quotes", {"symbols": ",".join(WATCHLIST), "greeks": "false"})
        quotes = _rows(quote_payload, "quotes", "quote")
    except Exception as exc:
        return empty_snapshot(now, "Underlying quote request failed: " + type(exc).__name__)

    quote_by_symbol = {str(q.get("symbol", "")).upper(): q for q in quotes}
    watchlist = []
    for symbol in WATCHLIST:
        q = quote_by_symbol.get(symbol, {})
        watchlist.append({
            "symbol": symbol, "last": _num(q.get("last")),
            "change_pct": _num(q.get("change_percentage")),
            "volume": int(_num(q.get("volume")) or 0),
            "previous_close": _num(q.get("prevclose")),
            "quote_available": bool(q),
            "leveraged": symbol in LEVERAGED,
            "scan_enabled": symbol in SCAN_SYMBOLS,
        })

    candidates = []
    symbol_status = []
    for symbol in SCAN_SYMBOLS:
        try:
            q = quote_by_symbol.get(symbol, {})
            spot = _num(q.get("last"))
            if spot is None or spot <= 0:
                symbol_status.append({"symbol": symbol, "status": "NO_UNDERLYING_QUOTE"})
                continue
            end = now.astimezone(EASTERN).date()
            start = end - timedelta(days=130)
            history_payload = _get(session, token, "/markets/history", {
                "symbol": symbol, "interval": "daily",
                "start": start.isoformat(), "end": end.isoformat(),
            })
            bars = _rows(history_payload, "history", "day")
            closes = []
            for bar in bars:
                value = _num(bar.get("close"))
                if value and value > 0:
                    closes.append(value)
            trend_info = _trend(closes)
            expiry_payload = _get(session, token, "/markets/options/expirations", {
                "symbol": symbol, "includeAllRoots": "false",
            })
            expirations = ((expiry_payload.get("expirations") or {}).get("date") or [])
            if isinstance(expirations, str):
                expirations = [expirations]
            chosen = _expiration_for(expirations, end)
            if not chosen:
                symbol_status.append({"symbol": symbol, "status": "NO_30_60_DTE_EXPIRATION", **trend_info})
                continue
            _, expiry_date, dte = chosen
            chain_payload = _get(session, token, "/markets/options/chains", {
                "symbol": symbol, "expiration": expiry_date.isoformat(), "greeks": "true",
            })
            chain = _rows(chain_payload, "options", "option")
            accepted = 0
            for raw in chain:
                normalized = dict(raw)
                normalized["underlying"] = symbol
                item = score_contract(normalized, trend_info["trend"], now, expiry_date.isoformat())
                if item:
                    item["underlying"] = symbol
                    item["underlying_last"] = spot
                    item["underlying_change_pct"] = _num(q.get("change_percentage"))
                    item["rsi14"] = trend_info["rsi14"]
                    item["sma20"] = trend_info["sma20"]
                    item["sma50"] = trend_info["sma50"]
                    item["return5d_pct"] = trend_info["return5d_pct"]
                    candidates.append(item)
                    accepted += 1
            symbol_status.append({
                "symbol": symbol, "status": "SCANNED", "expiration": expiry_date.isoformat(),
                "dte": dte, "contracts_reviewed": len(chain),
                "candidates": accepted, **trend_info,
            })
        except Exception as exc:
            symbol_status.append({"symbol": symbol, "status": "DATA_ERROR", "error_type": type(exc).__name__})

    candidates.sort(key=lambda x: (x["screen_score"], x["directional_fit"] == "ALIGNED",
                                   x["open_interest"], x["volume"]), reverse=True)
    # Publish a short, reviewable shortlist. No candidate is called a trade signal.
    top = candidates[:10]
    usable = [x for x in top if x["screen_score"] >= 65]
    return {
        "schema": SCHEMA,
        "generated_at_utc": now.astimezone(timezone.utc).isoformat(),
        "market_session": market_session(now),
        "provider": "tradier",
        "provider_environment": "production-read-only",
        "feed_status": "SNAPSHOT_AVAILABLE" if quotes else "NO_QUOTES_RETURNED",
        "watchlist": watchlist,
        "symbol_status": symbol_status,
        "candidates": top,
        "best_candidate": usable[0] if usable else None,
        "candidate_count": len(candidates),
        "qualified_candidate_count": len(usable),
        "screen_method": {
            "name": "Markets Now transparent contract screen v1",
            "components": {"liquidity": 25, "spread": 25, "delta": 15, "expiration": 15, "trend_alignment": 20},
            "minimum_score_to_surface_as_candidate": 65,
            "expiration_days": [30, 60],
            "excluded": ["0DTE", "leveraged ETFs", "unverified midpoint arbitrage"],
            "warning": "Heuristic ranking only; not a probability of profit or personalized investment advice.",
        },
        "orders_enabled": False, "research_only": True, "edge_proven": False,
        "warning": "Tradier snapshot; verify each contract and current bid/ask in your broker before considering any trade. No orders are placed. Quotes may change, and provider quote timestamps may be unavailable.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="markets-now.json")
    args = parser.parse_args()
    payload = collect()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Markets Now:", payload["feed_status"], "candidates:", payload.get("candidate_count", 0))
    # Missing credentials or provider data is a valid explicit unavailable state,
    # not a fabricated success or a failed research run.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
