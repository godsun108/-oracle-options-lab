# oracle-options-lab (Oracle-Q)

Prospective, research-only options intelligence. No live orders — every
envelope carries `orders_enabled:false, research_only:true` and the code
asserts data-cutoff provenance between underlying and options providers.

- `oracle_q/` — signal evaluation, forward observation, providers (Tradier)
- `proof_of_edge.py` + `test_proof_bridge.py` — prospective edge evidence and
  its bridge to the Seldon sidecar
- `PROOF_OF_EDGE.md`, `SELDON_RESEARCH_CONTRACT.md` — method and contract docs
- `arena/`, `experiments/`, `forward_records/`, `prospective_records/` —
  accumulated prospective history (the only accepted evidence class)

Run tests: `python -m pytest -q`
