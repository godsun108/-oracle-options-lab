"""Paired same-session evaluation for adaptive volatility trend challenger 001.

All strategies use identical validated opening-price sessions, entry/exit
boundaries, capital, and turnover-cost assumptions. Historical output is
exploratory only; no data fetching, broker, or order interface is provided.
"""
from __future__ import annotations

import math
import statistics

from research.adaptive_vol_trend import (
    CANDIDATE_ID, DEFAULT_COST_BPS_PER_FULL_TURNOVER,
    LOOKBACK_TREND, _validate_bars, target_weight,
)
from research.edge_lab import signal as incumbent_signal
from research.edge_lab import SYMBOLS

CONTROL_IDS = ("tsmom_63", "trend_200")
COMPARATOR_IDS = ("buy_hold", "zero_yield_cash")


def _metrics(weights, period_returns, initial_capital, cost_bps):
    equity = float(initial_capital)
    peak = equity
    max_drawdown = 0.0
    total_cost = 0.0
    total_turnover = 0.0
    previous_weight = 0.0
    gross_equity = float(initial_capital)
    net_returns = []
    worst_session = None
    for weight, market_return in zip(weights, period_returns):
        turnover = abs(weight - previous_weight)
        cost_fraction = cost_bps / 10000.0 * turnover
        cost = equity * cost_fraction
        total_cost += cost
        total_turnover += turnover
        equity = (equity - cost) * (1.0 + weight * market_return)
        gross_equity *= 1.0 + weight * market_return
        net_period_return = (1.0 - cost_fraction) * (1.0 + weight * market_return) - 1.0
        net_returns.append(net_period_return)
        if worst_session is None or net_period_return < worst_session:
            worst_session = net_period_return
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak)
        previous_weight = weight
    final_turnover = abs(previous_weight)
    final_cost = equity * cost_bps / 10000.0 * final_turnover
    total_cost += final_cost
    total_turnover += final_turnover
    equity -= final_cost
    if final_cost:
        final_return = equity / (equity + final_cost) - 1.0
        worst_session = min(worst_session, final_return) if worst_session is not None else final_return
    peak = max(peak, equity)
    max_drawdown = max(max_drawdown, (peak - equity) / peak)
    annualized_vol = (
        statistics.stdev(net_returns) * math.sqrt(252) * 100.0
        if len(net_returns) > 1 else None
    )
    return {
        "observations": len(weights),
        "initial_capital": float(initial_capital),
        "ending_equity": round(equity, 8),
        "net_pnl": round(equity - initial_capital, 8),
        "net_return_pct": round(100.0 * (equity / initial_capital - 1.0), 8),
        "gross_return_pct": round(100.0 * (gross_equity / initial_capital - 1.0), 8),
        "max_drawdown_pct": round(100.0 * max_drawdown, 8),
        "annualized_net_volatility_pct": round(annualized_vol, 8) if annualized_vol is not None else None,
        "worst_session_net_return_pct": round(100.0 * worst_session, 8) if worst_session is not None else None,
        "total_assumed_cost": round(total_cost, 8),
        "total_turnover_full_weight_units": round(total_turnover, 8),
        "rebalance_count_including_final_liquidation": sum(
            abs(weights[i] - (weights[i - 1] if i else 0.0)) > 0 for i in range(len(weights))
        ) + int(bool(weights and weights[-1])),
        "average_exposure": round(statistics.fmean(weights), 8) if weights else None,
        "time_in_cash_fraction": round(sum(w == 0 for w in weights) / len(weights), 8) if weights else None,
        "cost_bps_per_full_turnover": float(cost_bps),
    }


def compare_market(bars, *, symbol, initial_capital=2000.0,
                   cost_bps_per_full_turnover=DEFAULT_COST_BPS_PER_FULL_TURNOVER):
    """Return candidate and controls on one strictly paired daily-open window."""
    if symbol not in SYMBOLS:
        raise ValueError("unregistered market")
    if type(initial_capital) not in (int, float) or not math.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("initial capital must be finite and positive")
    if (type(cost_bps_per_full_turnover) not in (int, float)
            or not math.isfinite(cost_bps_per_full_turnover)
            or not 0 <= cost_bps_per_full_turnover <= 1000):
        raise ValueError("invalid turnover cost")
    data = _validate_bars(bars)
    if len(data) < LOOKBACK_TREND + 3:
        return {
            "schema": "oracle-q-adaptive-vol-trend-comparison-v1",
            "symbol": symbol, "status": "INSUFFICIENT_DATA",
            "paired_sessions": 0, "strategies": {},
            "orders_enabled": False, "broker_fills_verified": False,
            "edge_proven": False, "eligible_for_live_trading": False,
        }

    entries = list(range(LOOKBACK_TREND + 1, len(data) - 1))
    period_returns = [data[i + 1]["open"] / data[i]["open"] - 1.0 for i in entries]
    weights = {key: [] for key in (CANDIDATE_ID, *CONTROL_IDS, *COMPARATOR_IDS)}
    for i in entries:
        prior = [row["open"] for row in data[:i]]
        candidate_weight, _, _ = target_weight(prior)
        weights[CANDIDATE_ID].append(candidate_weight)
        for strategy_id in CONTROL_IDS:
            weights[strategy_id].append(float(incumbent_signal(strategy_id, prior)))
        weights["buy_hold"].append(1.0)
        weights["zero_yield_cash"].append(0.0)

    summaries = {
        strategy_id: _metrics(strategy_weights, period_returns, initial_capital,
                               cost_bps_per_full_turnover)
        for strategy_id, strategy_weights in weights.items()
    }
    incumbent = max(summaries[sid]["net_return_pct"] for sid in CONTROL_IDS)
    summaries[CANDIDATE_ID]["excess_vs_better_trend_control_pct"] = round(
        summaries[CANDIDATE_ID]["net_return_pct"] - incumbent, 8
    )
    summaries[CANDIDATE_ID]["excess_vs_buy_hold_pct"] = round(
        summaries[CANDIDATE_ID]["net_return_pct"] - summaries["buy_hold"]["net_return_pct"], 8
    )
    return {
        "schema": "oracle-q-adaptive-vol-trend-comparison-v1",
        "candidate_id": CANDIDATE_ID, "symbol": symbol,
        "status": "HISTORICAL_PAIRED_EXPLORATORY_ONLY",
        "paired_sessions": len(entries),
        "first_entry_session": data[entries[0]]["time"],
        "last_exit_session": data[entries[-1] + 1]["time"],
        "cost_convention": "bps_per_full_turnover_on_absolute_weight_change; initial entry and final liquidation charged",
        "strategies": summaries,
        "paired_dates_identical": True,
        "orders_enabled": False, "broker_fills_verified": False,
        "edge_proven": False, "eligible_for_live_trading": False,
        "limitations": [
            "All results are hypothetical daily-open proxy simulations, not broker fills.",
            "Historical data is exploratory and cannot count as prospective evidence.",
            "Unadjusted opens omit dividends, financing, taxes, cash yield, and verified corporate-action handling.",
            "Fixed turnover costs are assumptions, not measured spreads, slippage, or commissions.",
            "Six ETF markets are correlated and must not be treated as six independent trials.",
            "Options performance is not modeled or implied.",
        ],
    }
