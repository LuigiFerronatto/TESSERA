# 157 — Keep model roles separate without requiring a provider

| Field | Value |
|---|---|
| Issue | [#157](https://github.com/LuigiFerronatto/TESSERA/issues/157) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` configuration / optional adapter boundary |
| Pull request | [Draft PR #286](https://github.com/LuigiFerronatto/TESSERA/pull/286) |
| Head commit | [Current PR head and exact-head checks](https://github.com/LuigiFerronatto/TESSERA/pull/286/commits) |
| Tested runtime commit | [`f113460`](https://github.com/LuigiFerronatto/TESSERA/commit/f113460cf0cf3b061daae7414cd58d1020740d53); subsequent change only adds these PR links |
| Merge commit | Not merged |
| Decision | `PENDING`; proposed KEEP of the bounded schema experiment |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-02 |

## In one sentence

Applications can name different models for embedding, generation and reranking
without enabling those capabilities or changing ordinary offline retrieval.

## What problem existed?

The configuration-v2 boundary separated writes, readable sources and disposable
indexes, but had no typed model identities. A generic model setting would mix
unrelated roles, vendor choices and credentials. Adding optional configuration
must not turn a working offline installation into a provider-dependent one.

## How did TESSERA behave before?

At baseline `20814a47ec0f72d7bea0639e0b057df1ecf5cded`, project `models` was
an unsupported field. Named-global entries accepted only store ID/path. Legacy
assisted APIs used their existing explicit application function; no model profile
selected them. These assisted APIs remain unchanged in this candidate.

## What changed or is being tested?

- Three immutable profile types, resolved by capability plus profile name
- Closed project-v2 and per-named-global schema with no inheritance/corpus merge
- Environment-only credential references; no persisted credential values
- Declared model identity and conservative mutable/unverified identity warnings
- Explicit application-owned adapter registration/preparation with actionable
  missing-reference, missing-credential, unavailable-adapter and dependency errors
- Profile preservation across project/global initialization and unregister
- Credential-safe YAML parser errors and immutable profile deepcopy compatibility

## How does it work now? TARGET — NOT YET ON MAIN

```text
selected project or named global store
 -> ResolvedConfiguration.models
 -> ModelReference(capability, profile)
 -> correctly typed profile + declared provider/model identity
 -> explicit application-owned adapter preparation (optional)
```

Loading or inspecting configuration never invokes a factory, reads credential
values, imports a provider SDK, checks a model over the network or activates a
stage. Local profiles reject credentials/endpoints. Model configuration is not
copied into graph or index metadata. The existing source/write/index boundaries
and deterministic retrieval output remain unchanged.

## Concrete example

An application can resolve `embedding/local-default` and
`reranking/local-default` to different profile types. It cannot substitute
`generation/local-default` unless that exact generation profile exists.
Changing `generation/fast` leaves the embedding identity unchanged.

See [the complete profile/API contract](../MODEL_PROFILES.md) for project and
named-global examples, supported provider classes and safe credential references.
Examples deliberately use fictional models; no universal default was selected.

## How was it validated?

`tests/test_issue_157_model_profiles.py` covers all ten issue scenarios, including
provider/capability rejection, config/identity inspection, late dependency and
credential errors, native local paths, secret-free round trips, init preservation,
core offline operation and disposable Engine snapshots. Existing configuration,
MCP, init, packaging and deterministic retrieval tests remain regression gates.

Reproducible commands from a dedicated external environment installed against
this candidate:

```bash
python -m pytest -ra
python benchmarks/sanity/ci_eval.py --output-dir /tmp/tessera-157-sanity
python -m build --no-isolation --outdir /tmp/tessera-157-dist
```

Local Python 3.12.14 validation: 634 passed, 5 explicitly skipped governance
compilation checks (the `gh-aw` CLI extension is unavailable); 69 focused profile
tests passed. Sanity: Hit@1 0.75, Hit@3/5 1.0, MRR 0.875, evidence hit 1.0,
missing-evidence check passed. The tested tree, remote head and CI are recorded
in the PR. The base-only wheel is separately installed outside the
checkout and checked for profile round trip, credential-free/no-network retrieval,
optional SDK absence and Engine deepcopy. Python 3.9 syntax is checked locally;
actual Python 3.9/3.12 distribution and CI gates belong to exact-head GitHub CI.
No real provider, model inference or retrieval-quality comparison is claimed.

## What improved?

The schema represents each capability independently and fails invalid selections
before execution. Project/global round trips preserve references and ownership.
Configured unavailable optional models do not disable unrelated core retrieval.
An independent review found a snapshot incompatibility in the first immutable
mapping implementation; deepcopy is now explicitly supported and regression-tested.

## What remains unimplemented?

Concrete provider adapters, inference, model-name availability verification,
semantic retrieval (#158), reranking (#159), pipeline configuration (#160),
presets (#161), integrated model diagnostics (#162), artifact/cache lifecycle
(#163), and model quality evaluation. Application factories own their runtime
interfaces and must redact their own errors/logs. Declared revisions/digests are
never represented as independently verified model content.

## What is unlocked next?

No dependency is canonically satisfied by an unmerged candidate. After review,
exact-head CI, merge and lifecycle reconciliation, #157 can satisfy its own
prerequisite for #158/#160/#163; each dependent keeps its other gates. No dependent
card is implemented here.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#157](https://github.com/LuigiFerronatto/TESSERA/issues/157) |
| Baseline | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Configuration prerequisite | #153 / PR #173 / canonical `2508676d472088733702b6ed920fc829df9a7681` |
| Core boundary prerequisite | #74 / [ADR 0001](../adr/0001-core-vs-optional-llm-boundary.md) |
| PR / exact head / CI | [PR #286 checks](https://github.com/LuigiFerronatto/TESSERA/pull/286/checks); not merged |
| Evidence/Learnings/Decision | This record and PR validation; decision pending |
| Benchmark record | SMOKE_ONLY; deterministic sanity, no model-quality claim |

## Risks and rollback

No default/model/index migration is introduced. Older releases reject optional
`models` fields; remove those sections before downgrading. Revert this candidate
and its optional config additions to restore the baseline. Do not promote the
schema, mark dependencies satisfied or call this capability validated until the
canonical merge and its required gates are recorded.

## Evolution

```text
#153 store/source/index + #74 independent deterministic core
 -> #157 typed-profile candidate with offline config tests
 -> pending human review / exact-head CI / canonical merge
 -> separately selected dependent experiments
```
