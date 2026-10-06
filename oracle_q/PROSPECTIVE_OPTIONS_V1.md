# Oracle-Q Prospective Options Observation — v1

Status: FROZEN RESEARCH / PAPER-FORWARD SPECIFICATION

This specification connects a genuinely prospective Oracle signal to a read-only Tradier option-chain observation. It does not authorize trading.

## Timing and selection

- A contract observation is attempted only when the already-frozen Oracle Canonical Signal v1 is true.
- The observation uses information available at observation time only.
- Expiration is the earliest available expiration on or after the caller's frozen minimum-expiration date.
- Calls only.
- Quotes must have bid > 0, ask > 0, and ask >= bid.
- Selection is deterministic: nearest strike to contemporaneous spot, then higher open interest, then narrower absolute spread, then OCC symbol.
- Every normalized quote already bears a raw-payload SHA-256 hash. The complete observed chain is additionally represented by a deterministic SHA-256 hash over the sorted contract hashes.

The minimum-expiration rule must be chosen by the prospective caller before outcomes are known. Changing it creates a new experiment/specification rather than silently changing v1.

## Evidence boundary

An observation records the signal date/state, selected expiration and contract, normalized quote fields, chain row count, chain hash, and UTC recording time. NO_SIGNAL, NO_EXPIRATION, and NO_VALID_CONTRACT are valid evidence states and must not be silently discarded.

This layer contains no order methods, position sizing, brokerage account actions, or money movement. A market-data observation is not a recommendation or authorization to trade.
