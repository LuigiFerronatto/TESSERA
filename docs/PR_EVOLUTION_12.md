# Issue #12 delivery scope

The incremental indexing delivery includes a small set of repository contract
alignments that are required for the installed-artifact gates to remain
deterministic:

- `LAO_MEM_DIR` compatibility is intentionally removed in favor of
  `TESSERA_STORAGE_DIR`, as requested for the current public configuration.
- Release validation receives the resolved tag explicitly.
- Clean-room fixtures assert the canonical writable-store MCP composition.
- Automatic update checks remain advisory and are disabled in the explicitly
  network-isolated clean-room environment.

These changes were deliberately ratified as part of this delivery because the
indexing lifecycle is validated through the same installed-artifact and
clean-room contracts. They are listed in `CHANGELOG.md` and in the PR summary
so the audit scope is explicit.
