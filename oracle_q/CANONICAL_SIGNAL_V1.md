# Oracle Canonical Signal Specification — v1

Status: FROZEN RESEARCH SPECIFICATION

## Purpose
This document defines the single reproducible underlying signal used for forward validation. It replaces the unverified historical 107/55/18 count fingerprint as a provenance target. The old 180-signal fingerprint remains historical metadata only.

## Data
Underlying: daily SPY series used by the frozen Stage-9 workflow.
Rows are ordered by trading date. Calculations use only observations available through the signal day's close.

## Signal
For trading session t, emit a signal when BOTH are true:

1. Six-session close return <= -1%:
   close[t] / close[t-6] - 1 <= -0.01
2. Close is above the contemporaneous 200-session simple moving average:
   close[t] > SMA200(close)[t]

There is no volume filter.

Equivalent implementation:
    signal = (close.pct_change(6) <= -0.01) & (close > close.rolling(200).mean())

## Timing
T0: signal is known only after the T0 daily close.
T+1: earliest modeled option entry is the next trading session EOD.
T+2: frozen Stage-9 modeled exit is the following trading session EOD.

No T0 execution is permitted in the frozen research test.

## Frozen option execution
Stage-9 remains authoritative:
- calls only;
- entry at T+1 EOD ask;
- exit at T+2 EOD bid;
- ATM strike selection uses unadjusted SPY spot;
- delta variants use their declared target delta;
- only valid positive bid/ask quotes with ask >= bid;
- deterministic OI, spread, contract-id tie breaks.

## Reproducibility contract
A canonical implementation must:
- produce identical signal dates for identical input rows;
- be invariant to future rows appended after the evaluated cutoff;
- never use option outcomes to create the underlying signal;
- expose the data cutoff and specification version with every forward signal.

Any change to lookback, threshold, MA definition, filters, timing, or execution rules creates a NEW specification version and must not overwrite v1.

## Forward-validation rule
v1 is frozen before forward evaluation. Forward results may reject v1, but may not rewrite it. New hypotheses belong to a separately versioned experiment.

## Historical fingerprint
The previously cited 107/55/18 = 180 signal fingerprint has not been reproduced by the Stage 2-6 forensic grids and has no recovered original code/signal-date artifact. It is therefore not ground truth and must not be used as a tuning objective.
