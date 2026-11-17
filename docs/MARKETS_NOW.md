# Markets Now

Markets Now is the mobile-first, read-only market and options research dashboard published at:

https://godsun108.github.io/-oracle-options-lab/markets-now/

## What it does

- Publishes a Tradier production-endpoint snapshot on a 15-minute GitHub Actions schedule during the broad US market-day window, plus manual workflow dispatch.
- Tracks the user's 29-symbol research watchlist; initially scans options on SPY, QQQ, IWM, DIA, NVDA, TSLA, AMD, AAPL, META, PLTR, MU, SMH, GLD, and TLT.
- Excludes leveraged ETFs from the initial contract scan. They remain visible for context.
- Reviews contracts with 30–60 days to expiration and applies basic liquidity, spread, delta, and trend-alignment filters.
- Displays a ranked research shortlist and a transparent 0–100 screening heuristic.
- Includes an educational playbook, pre-trade checklist, and browser-local journal.

## Data and publishing pipeline

1. `.github/workflows/markets-now-live.yml` runs `research/markets_now.py`.
2. The scanner reads underlying quotes, daily history, option expirations, and option chains from Tradier using `TRADIER_TOKEN`.
3. It uploads `markets-now-snapshot` as a workflow artifact.
4. `.github/workflows/arena-pages.yml` retrieves the latest successful snapshot and deploys the Markets Now page beside the Oracle-Q Arena.

The dashboard refresh button reloads the latest published snapshot; it does not trigger a new market-data request. The scheduled workflow runs approximately every 15 minutes and GitHub Actions may delay or skip scheduled runs. The page calculates snapshot age and hides candidate rankings when the snapshot is stale.

## Configuration

Set the repository Actions secret `TRADIER_TOKEN` to a Tradier market-data token with access to the production market-data endpoints. Never place the token in source code, a workflow file, a public JSON snapshot, or the browser.

If the secret is absent or the provider request fails, the scanner publishes an explicit unavailable state rather than inventing prices or trades.

## Screening model

The v1 screen is intentionally transparent:

- Liquidity: open interest, volume, displayed bid/ask size (25 points)
- Spread: bid/ask width relative to midpoint (25 points)
- Delta: absolute delta band (15 points)
- Expiration: 30–60 DTE, with a preference for 35–50 DTE (15 points)
- Trend alignment: calls with bullish daily trend, puts with bearish daily trend (20 points)

The score is not a probability of profit, expected return, or proof of a trading edge. A score threshold only identifies contracts for additional manual review. Provider quote timestamps may not be present in every chain response; the dashboard flags this and requires brokerage-side verification.

## Safety boundary

- `orders_enabled` is always false.
- No broker order, cancellation, or account access methods are included.
- No 0DTE contracts are scanned.
- Leveraged ETFs are excluded from the initial contract scan.
- No candidate is a personalized recommendation.
- Check the current option chain, quote timestamps, spread, size, Greeks, IV, earnings/events, and maximum loss with the broker before making any decision.
- The journal uses browser `localStorage` on the current device only; entries are not synced or uploaded.

## Validation

`python -m pip install requests`

`python -m unittest tests.test_markets_now -v`

The dashboard is part of Oracle-Q's research-only environment. It does not establish or guarantee an options-trading edge.
