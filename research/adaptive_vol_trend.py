"""Adaptive volatility-targeted trend challenger 001.

Pure, deterministic daily-open research simulator. No network, broker, or order
interface. All features for session t use opens strictly before t; the target
weight is applied at open t and held to open t+1.
"""
from __future__ import annotations

import math
import statistics

from research.edge_lab import SYMBOLS

CANDIDATE_ID = "adaptive_vol_trend_001"
LOOKBACK_TREND = 200
LOOKBACK_MOMENTUM = 63
LOOKBACK_VOL_RETURNS = 20
TARGET_ANNUAL_VOL = 0.10
MAX_EXPOSURE = 1.0
DEFAULT_COST_BPS_PER_FULL_TURNOVER = 10.0
TRADING_DAYS = 252


def _validate_bars(bars):
    if not isinstance(bars, list):
        raise ValueError("bars must be a list")
    clean = []
    previous = None
    for row in bars:
        if not isinstance(row, dict):
            raise ValueError("bar must be an object")
        stamp = row.get("time")
        price = row.get("open")
        if not isinstance(stamp, str) or not stamp:
            raise ValueError("bar timestamp required")
        if previous is not None and stamp <= previous:
            raise ValueError("bar timestamps must be strictly increasing")
        if type(price) not in (int, float) or not math.isfinite(price) or price <= 0:
            raise ValueError("open must be finite and positive")
        clean.append({"time": stamp, "open": float(price)})
        previous = stamp
    return clean


def target_weight(prior_opens):
    """Return (weight, reason, features) using only prior completed opens."""
    if len(prior_opens) < LOOKBACK_TREND + 1:
        return 0.0, "NO_TRADE_DATA", None

    latest = prior_opens[-1]
    momentum_reference = prior_opens[-(LOOKBACK_MOMENTUM + 1)]
    trend_window = prior_opens[-LOOKBACK_TREND:]
    returns_window = prior_opens[-(LOOKBACK_VOL_RETURNS + 1):]
    log_returns = [
        math.log(returns_window[i] / returns_window[i - 1])
        for i in range(1, len(returns_window))
    ]
    if len(log_returns) != LOOKBACK_VOL_RETURNS:
        return 0.0, "NO_TRADE_DATA", None

    annualized_vol = statistics.stdev(log_returns) * math.sqrt(TRADING_DAYS)
    momentum = latest / momentum_reference - 1.0
    trend_average = statistics.fmean(trend_window)
    above_trend = latest > trend_average

    features = {
        "momentum_63": momentum,
        "trend_distance_200": latest / trend_average - 1.0,
        "annualized_volatility_20": annualized_vol,
    }
    if not math.isfinite(annualized_vol) or annualized_vol <= 0:
        return 0.0, "NO_TRADE_DATA", features
    if momentum <= 0 or not above_trend:
        return 0.0, "TREND_FILTER_OFF", features

    weight = min(MAX_EXPOSURE, TARGET_ANNUAL_VOL / annualized_vol)
    if not math.isfinite(weight) or weight <= 0:
        return 0.0, "NO_TRADE_DATA", features
    return weight, "INVESTED", features


def evaluate(bars, *, symbol, initial_capital=2000.0,
             cost_bps_per_full_turnover=DEFAULT_COST_BPS_PER_FULL_TURNOVER):
    """Evaluate the fixed rule with daily open-to-open returns and turnover costs.

    Cost is charged as cost_bps/10,000 * abs(change in exposure weight).
    Initial entry and final liquidation are charged. This is hypothetical
    friction, not measured spread, slippage, or broker execution.
    """
    if symbol not in SYMBOLS:
        raise ValueError("unregistered market")
    if type(initial_capital) not in (int, float) or not math.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("initial capital must be finite and positive")
    if (type(cost_bps_per_full_turnover) not in (int, float)
            or not math.isfinite(cost_bps_per_full_turnover)
            or not 0 <= cost_bps_per_full_turnover <= 1000):
        raise ValueError("invalid turnover cost")
    data = _validate_bars(bars)
    minimum = LOOKBACK_TREND + 2
    if len(data) < minimum:
        return {
            "schema": "oracle-q-adaptive-vol-trend-result-v1",
            "candidate_id": CANDIDATE_ID, "symbol": symbol,
            "status": "INSUFFICIENT_DATA", "observations": 0,
            "net_return_pct": None, "gross_return_pct": None,
            "max_drawdown_pct": None, "orders_enabled": False,
            "broker_fills_verified": False, "edge_proven": False,
            "eligible_for_live_trading": False, "sessions": [],
        }

    equity = float(initial_capital)
    peak = equity
    max_drawdown = 0.0
    previous_weight = 0.0
    total_turnover = 0.0
    total_cost = 0.0
    gross_equity = float(initial_capital)
    sessions = []

    # At open[i], features stop at open[i-1]. Hold target exposure to open[i+1].
    for i in range(LOOKBACK_TREND + 1, len(data) - 1):
        prior_opens = [row["open"] for row in data[:i]]
        weight, reason, features = target_weight(prior_opens)
        turnover = abs(weight - previous_weight)
        cost_fraction = (cost_bps_per_full_turnover / 10000.0) * turnover
        period_return = data[i + 1]["open"] / data[i]["open"] - 1.0
        if not math.isfinite(period_return) or period_return <= -1:
            raise ValueError("invalid open-to-open return")

        cost = equity * cost_fraction
        total_cost += cost
        total_turnover += turnover
        equity -= cost
        equity *= 1.0 + weight * period_return
        gross_equity *= 1.0 + weight * period_return
        if not math.isfinite(equity) or equity <= 0:
            raise ValueError("invalid simulated equity")
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak)
        sessions.append({
            "signal_as_of": data[i - 1]["time"],
            "entry_session": data[i]["time"],
            "exit_session": data[i + 1]["time"],
            "target_weight": weight,
            "reason": reason,
            "features": features,
            "open_to_open_return_pct": 100.0 * period_return,
            "turnover": turnover,
            "assumed_cost": cost,
            "equity": equity,
        })
        previous_weight = weight

    # Close the simulated position at the final observation boundary.
    final_turnover = abs(previous_weight)
    final_cost = equity * (cost_bps_per_full_turnover / 10000.0) * final_turnover
    total_cost += final_cost
    total_turnover += final_turnover
    equity -= final_cost
    peak = max(peak, equity)
    max_drawdown = max(max_drawdown, (peak - equity) / peak)

    return {
        "schema": "oracle-q-adaptive-vol-trend-result-v1",
        "candidate_id": CANDIDATE_ID, "symbol": symbol,
        "status": "HYPOTHETICAL_RESEARCH_ONLY",
        "observations": len(sessions),
        "initial_capital": float(initial_capital),
        "ending_equity": round(equity, 8),
        "net_pnl": round(equity - initial_capital, 8),
        "net_return_pct": round(100.0 * (equity / initial_capital - 1.0), 8),
        "gross_return_pct": round(100.0 * (gross_equity / initial_capital - 1.0), 8),
        "max_drawdown_pct": round(100.0 * max_drawdown, 8),
        "total_assumed_cost": round(total_cost, 8),
        "total_turnover_full_weight_units": round(total_turnover, 8),
        "average_exposure": round(statistics.fmean(s["target_weight"] for s in sessions), 8),
        "cost_bps_per_full_turnover": float(cost_bps_per_full_turnover),
        "orders_enabled": False, "broker_fills_verified": False,
        "edge_proven": False, "eligible_for_live_trading": False,
        "limitations": [
            "Unadjusted daily-open proxy simulation; not options performance.",
            "Costs are fixed assumptions, not measured spreads, slippage, or fills.",
            "No dividends, financing, taxes, or cash yield are modeled.",
            "A historical result is exploratory and cannot certify a prospective edge.",
            "No live order or broker interface exists in this module.",
        ],
        "sessions": sessions,
    }
