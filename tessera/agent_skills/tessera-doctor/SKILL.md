---
name: tessera-doctor
description: Inspect TESSERA configuration, corpus metadata and derived-index health using read-only diagnostics.
metadata:
  tessera-package: tessera-agent-memory
  tessera-minimum-version: "0.0.3"
  tessera-bundle-version: "1"
---

## Prerequisites and compatibility
Resolve the requested existing store/project. Probe `tessera corpus doctor --help`
for `--json` and `--strict`. This skill diagnoses; a diagnosis does not authorize
rewriting sources, repairing indexes, changing exclusions or installing software.

## Inspect without mutation

```bash
tessera config show --store "$STORE" --json
tessera corpus doctor --store "$STORE" --json
```

For a project-configured corpus, use `--project "$PROJECT"` in both commands so
all explicitly selected source roots are inspected. Examine report schema/status,
counts and individual findings; preserve severity and exact source identity.
Do not equate a stale disposable index with a missing canonical source. Report
whether the finding is a parse error, duplicate identity, broken relation,
metadata concern or derived-state problem.

Exit codes: 0 means no errors under the selected policy, 1 indicates errors, and
`--strict` returns 2 for warnings. A nonzero result is diagnostic evidence, not
permission to delete files or weaken the checks.

## Failure handling and boundaries
The separate `tessera doctor` performs a write/read smoke round trip; it is not
a substitute for this read-only corpus command. Run it only when that mutation
is within the user's request. Likewise, index rebuild requires its own justified
step. Never remove canonical memories to make diagnostics green. A repair report
must distinguish source validity, index freshness and evidence sufficiency;
current doctor results do not implement semantic contradiction adjudication.
