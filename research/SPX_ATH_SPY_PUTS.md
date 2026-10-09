# SPX all-time-high -> SPY put research (experimental)

**Hypothesis:** A new SPX record closing high may precede a SPY pullback large enough to profit on a long put bought with 30–60 calendar days to expiry. This is **not established**.

- Signal: SPX close strictly exceeds all preceding SPX closes in the supplied, point-in-time history. A complete historical SPX series is needed to call this a true all-time high; a truncated feed can only show a *sample high*. This first module requires 252 bars for basic sanity but does **not** certify full historical coverage.
- Instrument: SPY put (not SPX put); DTE between 30 and 60 inclusive. Test ATM and 2–5% OTM variants separately, not optimized on the evaluation set.
- Entries: use a quote observed **after** the SPX close signal, not a same-day earlier quote. Pay ask plus fees; sell at bid less fees. Do not infer fill from OHLC.
- Exits to compare: 7, 14, 21 trading-day holds; profit target, stop-loss, and exit at 7 DTE. Include zero-bid losses and option multiplier 100.
- Compare against: random entry dates, every SPX positive day, and new 52-week highs; report sample size, total return, drawdown, expectancy, win rate, median holding period, and transaction costs.
- Guardrails: no live orders; no automatic paper fills; require historical point-in-time option chain, bid/ask, contract identity and subsequent marks before computing P&L. Survivorship and selection bias must be tested.
- **Do not use current SPY quotes to pretend to price historical options.**

Research module: `research/spx_ath_spy_puts.py`. It emits signal/candidates only, never broker orders.
