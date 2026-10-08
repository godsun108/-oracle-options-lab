# Oracle-Q Multi-Market Paper Research Plan

Status: proposal / research only. Do not enable orders.

## Thesis
Test distinct market regimes and strategy families across multiple liquid instruments, with shared evidence and realistic execution modeling. More instruments do not imply diversification or positive expectancy.

## Research universe and phases
Phase 1: SPY, QQQ, IWM, SMH, TLT, GLD (daily bars, benchmark strategies, no live orders). Group highly correlated equity and semiconductor exposures rather than counting each ticker as independent.
Phase 2: paper options chains for the most promising, liquid underlyings; include expiration, strike, timestamped bid/ask, spreads, commissions, slippage, liquidity and assignment/expiry treatment.
Phase 3: BTC/ETH spot-paper testing only after a separate trustworthy 24/7 data source and fee/slippage model are verified.
Phase 4: consider futures/FX only after contract specs, rollover, session times, margin and risk constraints are modeled.

## Strategy families
Trend following, mean reversion, volatility regime, cross-asset relative strength and event-aware risk filters. Hypotheses must be preregistered; avoid unlimited parameter searching.

## Minimum evaluation
- Historical walk-forward with chronological train/validation/test splits and realistic market-hours data.
- Strict prospective observations timestamped before any hypothetical order; completed-session maturity and vintage-safe inputs.
- Paper trade ledger: signal time, decision time, contract, quote, intended size, hypothetical fill, fees, exits, P&L and explicit NO_TRADE reason.
- Compare against passive exposure and simple naive rules, net of fees/slippage.
- Per-market and portfolio: trade count, expectancy, Sharpe (with caveats), drawdown, exposure, concentration, correlation, turnover, tail loss.
- Block live trading by default. Do not claim proven edge until a sufficiently large out-of-sample paper sample survives changing market conditions.

## Operational gates
Discover actual existing workflows and entrypoints before changing production code. Keep Tradier tokens secret, honor provider rate limits, and ensure failures emit explicit alerts. Do not claim GitHub Actions passed without logs.
