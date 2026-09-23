# Oracle bounded self-repair

Oracle may eventually repair **infrastructure**, not rewrite science.

Allowed automatic repair classes: transient download retry, artifact/path recovery, recognized source-schema parsing, dependency/cache retry, and rerunning a deterministic failed job.

Forbidden automatic changes: trading signal definitions, thresholds, targets/labels, feature meaning, train/test boundaries, future-data access, fill/execution assumptions, optimizer objective, risk limits, or performance results.

Every repair must preserve an audit trail containing the failure signature, proposed patch, files changed, before/after commit, and rerun result. Unknown failures halt for review. A successful rerun is not evidence of trading validity; it only establishes software execution.

The self-repair agent should use an allowlist of repair templates rather than unrestricted code generation. Semantic changes require human approval and a new experiment identifier.
