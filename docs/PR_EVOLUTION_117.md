# PR Evolution Audit — Issue #117 configuration and discovery

Audited starting `main`: `b3be96f4aa842a81c135b6ac87d3311ed292d339`,
the actual fetched `origin/main` when branch
`test-card/117-config-init-discovery` was created. This is PR #133's canonical
#116 lifecycle merge. Issue #117 dependencies #94, #115 and #116 are
`VALIDATED`; implementation moved #117 from `READY` to `IN_PROGRESS` before
the canonical merge and this lifecycle synchronization moves it to
`VALIDATED`.

## Audit method and baseline reproduction

The audit inspected current source, history, GitHub merge state and focused
executable behavior. With no positional path and both storage environment
variables unset, current-main non-TTY `tessera init --plain` exited 0, selected
`<cwd>/memories`, and created that directory plus `.tessera_index/` files. It
did not create project configuration or a global registry and did not explain a
persistent store identity.

The implementation therefore does not claim discovery already existed. It
adds configuration above Engine without changing Engine's corpus boundary or
retrieval semantics.

## Relevant deliveries

| Delivery | Merge status and canonical SHA | Capability/contract | #117 use or change |
|---|---|---|---|
| Initial repository/package | merged, `9cc8c38c2618ba6029d64a31b76742b968574a2b` | root package and argparse CLI, including original init/doctor/quickstart behavior | audited baseline only; no second product capability counted |
| PR #98 / Issue #68 | merged, `fb23012ba4b2fddc3912d7cb593391a04fe45ae7` | aligned current Engine/CLI/MCP retrieval result semantics | selection feeds the same Engine contract; retrieval is unchanged |
| PR #101 / Issue #94 | merged, `467ba649f53312cedcecf40caf548af5f766c67b` | Markdown-only successful persistence and no pre-admission mutation | init never rewrites source memories; config remains separate from corpus data |
| PR #108 / Issue #92 | merged, `9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05` | containment and truthful write-gate mutation boundary | reuses strict path/data treatment; config never executes values |
| PR #126 / Issue #95 | merged, `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599` | project-neutral explicit/env/deprecated-env/default resolver and explicit optional integration boundary | preserves canonical env and legacy warning; adds product config without LAO/Blip probing |
| PR #129 / Issue #93 | merged, `c6124548f32b6dc5e1b7acf5127632bc6c75fccc` | same selected canonical store gives Python/CLI/MCP agreement | regression target; **storage parity is not product configuration/discovery** |
| PR #128 / Issue #115 | merged, `b475f1cd805f86cc8ad9526e563e3c6fb8409ff1` | accepted root-package/repository/distribution boundary | new configuration stays inside the distributed `tessera` package |
| PR #131 / Issue #116 | merged, `0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4` | ownership-correct wheel/sdist with 37-export public API and five resources | configuration module remains packaged without adding exports or dependencies |
| PR #133 | merged, `b3be96f4aa842a81c135b6ac87d3311ed292d339` | lifecycle sync: #116 `VALIDATED`, #117 `READY` | canonical starting state; documentation-only delivery, not another runtime capability |

Candidate commits and later canonical merges count once per delivery. PR #133
does not duplicate PR #131 packaging capability. No earlier candidate or
superseded PR implemented the Issue #117 project/global contract.

## #93 versus #117

Issue #93 proved:

```text
same selected canonical store
→ Python / CLI / MCP agreement
```

Issue #117 adds:

```text
explicit/env/project/named-global inputs
→ one inspectable StorageSelection
→ absolute canonical store
→ existing Engine/consumer contract
```

The current MCP bootstrap intentionally retains the compatibility resolver
until #120 adopts the new primitive. Environment-generated MCP configuration
continues to preserve #93 parity. #117 neither redesigns MCP protocol nor
claims that global registry entries are one combined corpus.

## Candidate architecture and migration

ADR 0003 freezes `.tessera/config.yaml`, OS-standard `registry.yaml` paths,
closed schema version 1, persisted UUID identity, exact-marker ancestor
discovery, deterministic precedence, atomic writes, non-interactive failure,
and Engine/MCP boundaries.

Direct library `resolve_storage_dir()` and pre-#120 MCP retain the historical
`./memories` fallback. Product configuration-aware CLI operations require an
explicit/environment/project/named-global choice. `tessera init PATH` remains
a compatibility alias that creates current-project configuration; there is no
automatic migration and no destructive repair.

## Scope and routing

This implementation owns configuration, discovery, init, config inspection,
diagnostics and safe registry mutation. It does not implement clean-room
onboarding (#118), visual CLI redesign (#119), MCP lifecycle (#120), official
Skills (#121), PyPI publication (#134), legal ownership (#87), Quality Gate
#67, corpus Metadata Doctor #13, or conflict containment #16.

## Canonical implementation and lifecycle reconciliation

PR #150 was squash-merged as
`61cf76fbd6ed61972f0f5abae515ba9bffca4b55` from final candidate
`f636e39f4d48726a10a3dce15fa42de88b029a23`. The candidate and canonical
merge have the same tree and count once as one `CONFIGURATION_DISCOVERY`
delivery. The final decision is `KEEP`.

The implementation evidence is `SMOKE_ONLY`: TESSERA CI run `33459718574`
passed the Python 3.9/3.12 tests and distributions, smoke and sanity jobs;
Benchmark Ledger run `33459718572` passed reporting and correctly skipped
LongMemEval. The implementation full suite passed with 301 tests and 14
expected warnings.

This post-merge lifecycle PR is a `DOCUMENTATION_CORRECTION`, not another
configuration delivery. Its benchmark applicability is `NOT_APPLICABLE`
because it synchronizes documentation, governance and executable documentation
assertions only. It introduces no runtime, package, benchmark or schema change.

After this lifecycle is canonically merged, #117 is `VALIDATED`; #118, #119
and #120 are `READY`; #121 remains `BLOCKED` on #120; and #134 remains
`BLOCKED` until #118 is validated and #87 resolves owner-approved legal and
contribution entrypoints. #67 remains `BLOCKED` on regression-gate integration
with its #93 dependency satisfied. No downstream implementation, PyPI or
TestPyPI publication, release workflow, tag or GitHub Release was started.

PR #149 remains separate roadmap/documentation work. This lifecycle preserves
current-`main` truth only and does not absorb, recreate, close or reconcile the
QUMem portfolio owned by #149/#147.
