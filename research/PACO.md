# PACO — Strategy & System

**PACO** is Oracle-Q's research-only, two-direction options opportunity system.

- **High regime:** prioritize discounted SPY **puts**, with approximately 30–60 days to expiration.
- **Low regime:** prioritize discounted SPY **calls**, with at least 30 days to expiration.
- **Always scan both sides.** Regime changes priority, not visibility.
- **Bargain scanner:** inspect ask price versus reference, quote freshness, spread, size, and immediately executable bid-exit economics. A discount to a midpoint is **not** a guaranteed profit.
- **Directional timing:** evaluate end-of-day entries and next-market-open exits separately from longer holding-period experiments. These are hypotheses, not proven edges.
- **Execution:** research and paper simulation only; no broker orders, no automatic purchasing, no performance claim.

PACO is the unified name for both the strategy and the system. Initial quote-screening implementation: `research/options_discount_scanner.py`.
