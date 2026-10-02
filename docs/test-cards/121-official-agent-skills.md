# #121 — Package thin agent instructions for current TESSERA capabilities

| Field | Value |
|---|---|
| Issue | [#121](https://github.com/LuigiFerronatto/TESSERA/issues/121) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` |
| Pull request | Candidate branch `feat/121-official-agent-skills` |
| Merge commit | Not merged |
| Decision | `PENDING` review |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-02 |

## In one sentence
Ship reusable agent instructions that exercise current public TESSERA contracts safely and truthfully.

## What problem existed?
The package had five procedural-anchor memory notes, but no distinct agent
Skills teaching TESSERA setup, write, query, diagnosis and evaluation.

## How did TESSERA behave before?
Consumers had to reconstruct commands and failure boundaries from scattered
docs; `skills install` installed memory notes rather than agent instructions.

## What changed or is being tested?
Five standard SKILL.md resources, a versioned read-only lookup API, artifact
packaging and real command-level tests. Existing anchor behavior is unchanged.

## How does it work now?
TARGET — NOT YET ON MAIN: agents read a narrowly triggered Skill, verify runtime
features and call existing public operations. Loading does not install hooks,
change consumer settings, write a store or run example commands. See the
[bundle contract](../AGENT_SKILLS.md).

## Concrete example
The doctor Skill calls read-only `corpus doctor`; it does not silently replace
it with the separate write/read smoke test. The write Skill requires actual
`persisted: true`, rather than inferring success from transport completion.

## How was it validated?
`tests/test_agent_skills_bundle.py` extracts and runs the supplied shell examples
in synthetic projects, checks real structured results, source integrity,
rejection behavior, same-scope empty retrieval and emitted sanity metrics.
Metadata validation and wheel/sdist byte comparison cover packaging. Exact full
suite/remote counts are recorded in the PR.

## What improved?
Five bounded workflows have maintained commands, compatibility probes and
failure interpretation without duplicating memory semantics.

## What remains unimplemented?
No native runtime installation, hook integration or future #171/#167/#169 APIs
are introduced. No generic multi-agent task-success benchmark is claimed.
Read-only resource access does not authorize installing or applying the Skills.

## What is unlocked next?
Packaging for specific consumers can build on this bundle only after canonical
review/merge; #193's other semantic/API prerequisites remain independent.

## Technical provenance
- Baseline:`20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Resources:`tessera/agent_skills/*/SKILL.md`
- API:`tessera/agent_skills.py`, bundle version1
- Tests:`tests/test_agent_skills_bundle.py`, packaging contract
- Existing runtime/write prerequisites:[MCP](120-mcp-runtime-robustness.md),[write gate](92-write-gate-integrity.md)

## Evolution
Existing public primitives → thin versioned instructions and artifact tests →
independent review/canonical merge → separately scoped consumer integrations.
