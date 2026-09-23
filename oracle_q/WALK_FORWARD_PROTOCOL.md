# Walk-forward baseline protocol

Oracle AI and Oracle Q do not get to compete against a straw man.

The first probability benchmark is a regularized logistic model trained walk-forward. For every prediction, all training rows must have dates strictly earlier than the prediction date. Feature standardization is recalculated from that historical training window only.

It is compared with an even simpler baseline: the historical unconditional success rate available at that date. Primary probability diagnostics are Brier score and calibration. Trading utility remains a separate downstream test using identical candidate contracts, costs, and risk constraints.

Any AI-derived model, regime classifier, QUBO allocation, or QAOA emulator must demonstrate incremental out-of-sample value over these baselines. Complexity without incremental evidence is rejected.
