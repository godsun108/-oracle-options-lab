# Oracle-Q public test relay — pilot protocol

**Scope:** synthetic-only public CI smoke tests. This repository must not receive private Oracle-Q strategy code, account data, provider credentials, paper ledgers, source reports, or proprietary trading parameters.

## Verified baseline
- Public Actions run: https://github.com/godsun108/-oracle-options-lab/actions/runs/39518020810
- Workflow commit: `7e1da2670db661ec967c5d930342626c6e5c21be`
- GitHub conclusion: `success`
- Workflow job: `synthetic-smoke`, step: `Run public synthetic relay smoke tests`
- Test source Git blob SHA: `e2b8005d88b5ffaadabb0546356e7e3d33e5dfa9`

## Evidence boundary
A green public run establishes that the public synthetic test package executed on GitHub-hosted infrastructure. It does **not** establish that private Oracle-Q code, private data, forward trading observations, paper ledger integrity, or broker fills were tested.

## Private acceptance checklist
1. Verify public run conclusion and exact commit via GitHub API.
2. Verify the expected workflow name, job name, and completed test step.
3. Review every file before it is copied into the public repository.
4. Record source commit and test-package fingerprint for any future independently reviewed public package.
5. Do not automatically promote challengers, change live trading permissions, or modify private deployment based on public test success.

No secrets, credentials, private artifacts, or private source should be exported by this pilot.
