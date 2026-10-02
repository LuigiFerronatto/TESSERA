# 196 — One lifecycle vocabulary across agent runtimes

| Field | Value |
|---|---|
| Issue | [#196](https://github.com/LuigiFerronatto/TESSERA/issues/196) |
| Record status | `IN_PROGRESS` |
| Capability type | runtime / benchmark |
| Pull request | Candidate branch `feat/196-neutral-hook-core`; see issue-linked draft |
| Head commit | Exact measured head and source hash in CI `hooks-parity.json` |
| Merge commit | Not merged |
| Decision | `ITERATE` proposed; human review pending |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

This experiment translates different agent lifecycle signals into the same small
memory-facing vocabulary without treating the end of a response as permission
to save a memory.

## What problem existed?

Canonical main has an explicit task wrapper, `TesseraTaskHook`, but no common
multi-provider lifecycle event, bounded run journal or semantic parity benchmark.

## How did TESSERA behave before?

Callers explicitly invoked task-start retrieval and task-end writes. Connecting
three hook systems otherwise required separate lifecycle interpretations.

## What changed or is being tested?

An additive SDK separates provider wire adapters from project/run identity,
redacted ephemeral evidence, bounded prepared-context injection and candidate
learning boundaries. Four official-reference provider subsets have frozen
synthetic fixtures. Existing Hook, Engine, CLI and MCP behavior is unchanged.

## How does it work now?

TARGET — NOT YET ON MAIN. Provider JSON becomes canonical events, then a bounded
in-memory journal and context/boundary result. No writer or admission pipeline
is reachable. Read [the contract](../HOOK_CORE.md) for exact SDK ownership and
capability gaps.

## Concrete example

Claude UserPromptSubmit and Codex UserPromptSubmit produce the same input and
before-reasoning milestones. Their Stop events produce response/turn boundaries,
not task completion or a saved memory. Child evidence echoed by a parent tool
keeps one explicitly identified origin with both source references.

## How was it validated?

- `python -m pytest tests/test_issue_196_hook_core.py -q`
- `python -m benchmarks.hooks.run --output artifacts/hooks-parity.json`
- Full suite: `python -m pytest -ra`; exact-head TESSERA CI remains the remote gate
- Dedicated exact-head `TESSERA Hook Core Parity` workflow uploads the report

The semantic experiment has 14 strict gates. Each equivalent Claude/Codex run
has 14 canonical events, 5 episode-input groups, one failed tool event, two
parent-child links, one compaction checkpoint and one child/parent origin with
two references. Same-input runs are repeated; corrupt mapping/missing-evidence
negative controls must be detected. No LTM quality claim follows from zero writes.

## What improved?

The bounded core now has a concrete, testable semantic contract instead of a
provider-specific persistence assumption. The experiment measures real evidence
and lineage equivalence while showing unsupported effects explicitly.

## What remains unimplemented?

Actual Working Context/compiler, episode construction, candidate generation,
admission, durable lineage/writes, index self-heal, relevant-write validators,
hygiene/drift handlers, persistent executable transport and installation remain
outside this slice. OS-specific command/interpreter fixtures are not delivered.
Copilot command prompt injection and inline final text are unavailable in the
frozen reference; Gemini has lifecycle gaps. See the full [limitations](../HOOK_CORE.md).
The expanded issue is not complete and must not be closed from this candidate.

## What is unlocked next?

No dependency is marked unblocked before merge and review. #177/#190 may review
the proposed SDK; #138/#137 may review its evidence and explicit lineage inputs.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Canonical baseline | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Existing compatibility surface | `tessera/hooks.py:TesseraTaskHook`, unchanged |
| New core / wire boundary | `tessera/lifecycle.py`, `tessera/hook_adapters.py` |
| Schema | [lifecycle-event-v1](../schemas/lifecycle-event-v1.json) |
| Tests | `tests/test_issue_196_hook_core.py` |
| Benchmark | `benchmarks/hooks/run.py`, exact-head CI artifact |
| PR Evolution Audit | First isolated #196 Hook Core candidate; no prior delivery claimed |

## Evolution

Explicit task wrapper on main -> additive normalized SDK candidate -> review and
required semantic experiment -> future downstream handlers on fresh canonical main.
