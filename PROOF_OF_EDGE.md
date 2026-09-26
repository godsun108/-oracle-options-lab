# ORACLE — Proof of Edge

## Mission

Oracle does not exist to predict every candle. It exists to reject weak trades and surface only setups that have earned the right to be tested with capital.

**DATA → REGIME → SIGNAL → EXPECTED VALUE → STRUCTURE → RISK → TRADE / NO TRADE → RESULT → LEARN**

## Promotion ladder

1. **Hypothesis** — define the setup before inspecting its outcome.
2. **Historical test** — include losing periods and realistic costs.
3. **Walk-forward** — chronological out-of-sample evaluation; never random shuffle market time.
4. **Robustness** — positive expectancy must not depend on one lucky fold, symbol, or tiny parameter choice.
5. **Paper-forward** — freeze the rule and collect genuinely unseen signals.
6. **Small live validation** — only after paper evidence; risk is capped.
7. **Scale review** — increase exposure only if live behavior remains inside validated assumptions.

## Default gate

The included `proof_of_edge.py` returns **NO_TRADE** unless the out-of-sample sample has:

- at least 30 trades,
- positive expectancy after configured costs,
- profit factor >= 1.10,
- max drawdown <= 20%, and
- positive expectancy in >= 60% of walk-forward folds.

Passing produces **TRADE_CANDIDATE**, not “guaranteed profit.” A candidate advances to paper-forward validation.

## Required option realism

Underlying direction alone is not an options backtest. Before Oracle promotes an options structure, the test must account for:

- actual entry/exit option prices where available,
- bid/ask spread and slippage,
- commissions/fees,
- implied volatility and volatility crush,
- theta/time-to-expiration,
- strike/moneyness,
- liquidity/open interest,
- assignment/exercise behavior when relevant.

If historical option-chain data is unavailable, label results as an **underlying signal test**, not an options P&L test.

## Anti-overfitting rules

- Never tune on the final holdout.
- Preserve chronology.
- Record every strategy version and parameter set tested.
- Compare against simple baselines.
- Report failed experiments.
- Do not select a setup solely because it was the best of many searches.
- Treat regime-specific performance as conditional evidence, not universal truth.

## Risk boundary

Oracle may recommend **NO TRADE**. That is a successful output.

Risk sizing is a separate layer from edge estimation. A positive-expectancy strategy can still experience severe losing streaks; proof of edge never implies safety or certainty.
