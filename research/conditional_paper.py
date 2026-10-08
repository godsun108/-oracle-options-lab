"""Deterministic, offline conditional paper-order simulator.

No network or brokerage interface. Strategy plans are explicit inputs and
never generated from attention scores. One bar per timestamp; conservative
stop-first ordering for bars crossing both stop and target.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Plan:
    symbol: str
    direction: str
    trigger: float
    stop: float
    target: float
    max_bars: int = 5
    risk_fraction: float = 0.01
    validated: bool = False

    def check(self):
        if self.direction not in ("long", "short"):
            raise ValueError("invalid direction")
        if min(self.trigger, self.stop, self.target) <= 0:
            raise ValueError("prices must be positive")
        if not (0 < self.risk_fraction <= 0.02) or self.max_bars < 1:
            raise ValueError("invalid risk")
        if self.direction == "long" and not (self.stop < self.trigger < self.target):
            raise ValueError("invalid long levels")
        if self.direction == "short" and not (self.target < self.trigger < self.stop):
            raise ValueError("invalid short levels")

def simulate(plan: Plan, bars, capital=2000.0, fee_per_share=0.0, slippage_per_share=0.01):
    plan.check()
    if not plan.validated:
        return {"status": "NO_TRADE", "reason": "STRATEGY_NOT_VALIDATED"}
    if capital <= 0 or fee_per_share < 0 or slippage_per_share < 0:
        raise ValueError("invalid account/costs")
    if not bars:
        return {"status": "NO_TRADE", "reason": "NO_BARS"}
    seen = set()
    previous = None
    for bar in bars:
        t = bar["time"]
        if t in seen or (previous is not None and t <= previous):
            raise ValueError("bars must have strictly increasing unique timestamps")
        seen.add(t)
        previous = t
        if not (0 < bar["low"] <= bar["open"] <= bar["high"] and
                bar["low"] <= bar["close"] <= bar["high"]):
            raise ValueError("invalid OHLC")
    # Trigger detected from the close of a completed bar, fill next bar's open.
    for i in range(len(bars) - 1):
        bar = bars[i]
        triggered = bar["close"] >= plan.trigger if plan.direction == "long" else bar["close"] <= plan.trigger
        if not triggered:
            continue
        nxt = bars[i + 1]
        side = 1 if plan.direction == "long" else -1
        entry = nxt["open"] + side * slippage_per_share
        risk_per_share = abs(entry - plan.stop) + 2 * (slippage_per_share + fee_per_share)
        if (side == 1 and entry <= plan.stop) or (side == -1 and entry >= plan.stop):
            return {"status": "NO_TRADE", "reason": "ENTRY_INVALIDATED"}
        size = int(min((capital * plan.risk_fraction) // risk_per_share,
                       capital // (entry + fee_per_share)))  # cash-funded; no margin
        if size < 1:
            return {"status": "NO_TRADE", "reason": "INSUFFICIENT_CAPITAL"}
        for j in range(i + 1, min(i + 1 + plan.max_bars, len(bars))):
            candle = bars[j]
            stop_hit = candle["low"] <= plan.stop if side == 1 else candle["high"] >= plan.stop
            target_hit = candle["high"] >= plan.target if side == 1 else candle["low"] <= plan.target
            if stop_hit:
                raw_exit = min(candle["open"], plan.stop) if side == 1 else max(candle["open"], plan.stop)
                reason = "STOP"
            elif target_hit:
                raw_exit = plan.target
                reason = "TARGET"
            elif j == min(i + plan.max_bars, len(bars) - 1):
                raw_exit = candle["close"]
                reason = "TIME_OR_DATA_END"
            else:
                continue
            exit_price = raw_exit - side * slippage_per_share
            pnl = size * (exit_price - entry) * side - 2 * size * fee_per_share
            return {"status": "CLOSED", "symbol": plan.symbol, "direction": plan.direction,
                    "signal_time": bar["time"], "entry_time": nxt["time"],
                    "exit_time": candle["time"], "entry": round(entry, 4),
                    "exit": round(exit_price, 4), "shares": size,
                    "pnl": round(pnl, 2), "exit_reason": reason,
                    "mode": "HISTORICAL_SIMULATION_ONLY"}
    return {"status": "NO_TRADE", "reason": "NO_TRIGGER_OR_NEXT_BAR"}
