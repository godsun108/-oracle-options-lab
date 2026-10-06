# Prospective Oracle-Q Evidence Records

Append-only evidence generated from current Tradier production market data after the US market close.

Each date-named JSON envelope contains:
- provenance for the underlying SPY daily-history payload, including raw SHA-256 and data cutoff;
- the frozen Canonical Signal v1 evaluation and its complete input-history hash;
- the frozen prospective-options observation state and, only when a signal exists, option-chain provenance and deterministic contract selection;
- explicit research-only and orders-disabled flags.

A pre-existing date record is never silently overwritten. Differences are printed by CI but the original record remains intact.

These records are research/paper-forward evidence. They do not authorize orders, positions, brokerage actions, or money movement.
