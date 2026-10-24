# Paper evidence integration

The dedicated `paper-evidence-integration.yml` workflow samples SPY chains during cash-market sessions. UTC triggers cover both Eastern offsets; the versioned calendar skips holidays, weekends and times outside the session, including early closes. Actions scheduling can be delayed. Each quote's measured age, not launch time, determines whether it is recent. This is periodic collection, not continuous streaming or guaranteed near-close execution.

The weekly/manual historical archive requests SPX from January 3, 1928 through the latest completed session in at most 35 five-year windows (20 for 2026). Each parsed response is preserved and hashed. Invalid or duplicate dates reject that entire chunk; empty and failed windows remain visible. This addresses large-response truncation but does not prove full session coverage or independent price authenticity. The archive does not automatically promote the existing all-time-high signal. The official source-history and independent-price gates remain in force.

## Broker sandbox

Required GitHub repository secrets for read-only preflight:

- `TRADIER_SANDBOX_TOKEN`: sandbox-specific token, separate from production market-data credentials.
- `TRADIER_SANDBOX_ACCOUNT_ID`: the matching sandbox account number.

Do not paste credentials in issues, code, artifacts, or chat. No account ID, balance, positions, or token is published by preflight. The workflow never submits orders. A successful preflight establishes account access only.

`research.tradier_sandbox_execution` supports explicit one-contract SPY long-call/long-put limit orders (buy to open, sell to close) with a maximum $2,000 premium. Sell-to-close requires a matching sandbox long position. The broker previews each intent; submission requires the explicit CLI switch below. Production URLs and redirects are unavailable. Sandbox uses simulated executions and delayed market data, not actual exchange fills.

An intent JSON contains `environment: sandbox`, stable unique `intent_id`, `option_symbol` (OCC contract), `quantity: 1`, `side` and numeric cent-denominated `limit_price`. It must represent a deliberately selected research trade. No strategy automatically supplies these intents yet. Do not invent an intent merely to make the verification indicator green.

```sh
python -m research.tradier_sandbox_execution --output sandbox_preflight.json
python -m research.tradier_sandbox_execution --intent intent.json --journal persistent/paper-orders.jsonl --submit-paper --output submission.json
python -m research.tradier_sandbox_execution --intent intent.json --order-id 123 --output reconciliation.json
```

Use a durable shared journal on a single host. The journal locks, fsyncs a claim before POST, and refuses repeats. Never delete it to retry an uncertain submission. If a POST times out, inspect sandbox orders for the recorded `oq-<intent_id>` tag and reconcile the existing broker order. Distributed/multi-host submission and automatic retries are unsupported. An acknowledgement is not a fill. Only an identity-matched filled response with the executed quantity, price and limit checks can set `broker_paper_fill_verified`; it cannot establish live fills, settled PnL or strategy profitability.

References: https://docs.tradier.com/brokerage-api/trading and https://docs.tradier.com/docs/orders .
