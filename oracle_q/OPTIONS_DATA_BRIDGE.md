# Prospective Options Data Bridge

Status: RESEARCH / PAPER-FORWARD ONLY

Oracle may ingest current option-chain observations through a read-only provider adapter. The first adapter is Tradier.

## Required provenance
Every normalized quote records provider, environment, underlying, OCC symbol, expiration, option type, strike, bid, ask, open interest, volume, observation timestamp, provider trade timestamp when supplied, and a SHA-256 hash of the raw contract payload.

## Environments
- `sandbox-delayed`: intended for paper-forward research. Tradier documents sandbox equity/options market data as delayed.
- `brokerage-realtime`: may be supported for market-data observation, but this repository does not expose order placement.

## Secret
Set `TRADIER_TOKEN` in the execution environment / GitHub Actions secrets. Never commit the token.

## Scientific boundary
The adapter does not alter Canonical Signal v1, historical results, Seldon models, or execution specifications. A contract-selection rule must be frozen separately before a prospective signal is scored. Historical outcomes through 2025 remain burned for promotion.
