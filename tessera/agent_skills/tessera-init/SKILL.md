---
name: tessera-init
description: Initialize or update a TESSERA project or named store with explicit corpus selection and a reviewable mutation plan.
metadata:
  tessera-package: tessera-agent-memory
  tessera-minimum-version: "0.0.3"
  tessera-bundle-version: "1"
---

## Prerequisites and compatibility
Use an installed TESSERA exposing `tessera init --help` with `--dry-run`,
`--json`, `--sources` and `--non-interactive`. Check `tessera --version`, but
feature detection wins over the version string. Confirm the user's project,
generated-memory destination and selected readable sources. Never silently
substitute a global store or scan unrelated home directories.

## Plan, apply and verify
For the explicitly selected project and a memory-only corpus:

```bash
tessera init --project "$PROJECT" --store memories --sources memory-only --non-interactive --dry-run --json
```

Read `plan`, `applied` and any `error`. Dry-run must report no changes. If the
user asked for existing project sources, use `--sources custom --source PATH`
with each approved project-relative path; do not expand that selection to the
whole project. Show material existing-configuration changes before applying.
The apply command is the same command without `--dry-run`, only after the user
has authorized its plan. Add `--update-existing` only for an approved material
update, never to suppress a conflict.

```bash
tessera config show --project "$PROJECT" --json
```

Success requires `applied: true` and the intended resolved store/source/index
boundaries. Configuration saved with indexing failure is partial success;
report exactly what persisted and what needs repair. Cancellation is not success.
Global-store setup requires its own explicit name/path and uses `--global NAME`;
never replace a project corpus with it accidentally.

## Safety and failure handling
Source files remain authoritative and must not be rewritten. Config creation,
index creation and generated-memory storage are distinct effects. Keep provider
credentials and model installation outside this skill. On denied paths, parse
errors or unsupported flags, stop the dependent mutation and report the exact
problem; do not bypass exclusions, repeat an unchanged failure or force setup.
