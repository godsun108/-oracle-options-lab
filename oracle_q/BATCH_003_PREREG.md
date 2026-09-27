# Oracle Q Search-Space Reset — Batch 003 Preregistration

Status: FROZEN BEFORE OPTION OUTCOME SCORING

## Why
Batches 001-002 varied models/features inside Canonical Signal v1 and failed to establish positive dollar economics. Batch 003 changes deeper structural assumptions rather than continuing feature tuning.

## Event families
Each event uses only information known at T0 close. All require close > contemporaneous SMA200.

E1 DIP6: 6-session return <= -1.0% (Canonical Signal v1)
E2 SHOCK1: 1-session return <= -1.0%
E3 DIP3: 3-session return <= -1.0%
E4 DIP10: 10-session return <= -2.0%
E5 HIGHVOL_DIP: 6-session return <= -1.0% AND rv20 > rv60
E6 LOWVOL_DIP: 6-session return <= -1.0% AND rv20 <= rv60
E7 VOLUME_DIP: 6-session return <= -1.0% AND volume_ratio20 > 1.0

These thresholds are preregistered structural hypotheses, not selected from Batch-003 option outcomes.

## Execution horizons
Signal T0 close. Enter T+1 EOD ask.
Exit the SAME contract at:
- H1: T+2 EOD bid
- H2: T+3 EOD bid
- H4: T+5 EOD bid
provided a valid quote exists and the contract has not expired.

## Option structures
Use the six existing Stage-9 selection structures:
O1 ATM 2-3 DTE
O2 40-delta 2-3 DTE
O3 25-delta 2-3 DTE
O4 ATM 7-10 DTE
O5 40-delta 7-10 DTE
O6 25-delta 7-10 DTE

Candidates incompatible with an exit beyond expiration are invalid rather than silently substituted.

## Candidate universe and quantum scheduler
Candidate = event family x option structure x exit horizon.
7 x 6 x 3 = 126 design candidates before feasibility filtering.

The scheduler receives ONLY design metadata and a feasibility flag derived from declared DTE versus exit horizon. It receives no realized returns/P&L.

Select 18 diverse feasible candidates.

## Scoring
Rebuild historical execution directly from the same raw SPY option-chain source used by Stage 9.
Entry contract chosen once at T+1 using frozen selection/tie-break logic.
Exit follows exact contract_id at declared exit session bid.
Strict positive valid bid/ask quotes.
Report missing reasons.

Primary economic diagnostic: one-contract dollar P&L.
Report 2017-2021 and 2022-2025 separately, plus full.
No model or threshold optimization in Batch 003; this is a structural event/payoff map.

## Multiplicity / promotion
All historical data through 2025 are burned discovery evidence. Batch 003 maps where historical economics existed; it cannot establish a tradable edge. Any resulting hypothesis must be frozen for genuinely future paper-forward evidence before promotion.
