# Stage 14 — Forward Oracle Protocol

Canonical Signal v1 is now eligible for prospective observation.

Each observation must be created only after the source data through that session are available and must record:
- specification version;
- signal date and data cutoff;
- signal state;
- close, six-session return, and 200-session SMA;
- SHA-256 hash of the complete date/close input history used;
- UTC recording timestamp.

Forward records are evidence, not trading instructions. They are append-only: a later correction must create a new record explaining the correction rather than silently rewriting the original.

No realized T+1/T+2 option outcome may be added to a record before that outcome exists. Model changes require a new specification version. Canonical v1 remains frozen.

## Promotion gate
Oracle is not promoted to autonomous trading from a backtest. Forward observations must accumulate first, and any later execution layer requires separately frozen capital, liquidity, loss, and human-approval controls.
