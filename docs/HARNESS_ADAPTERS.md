# Deterministic instruction-format adapters

Candidate for [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71).

The registry isolates filename conventions from canonical normalization. It does
not load another project's instructions, execute instructions, assign authority,
select a provider, discover additional files or change retrieval scoring.

## Existing classification, explicit ownership

| Adapter | Case-insensitive basename rules | Document type | Default harness |
|---|---|---|---|
| agents | AGENTS.md | harness_instructions | None, format is agent-agnostic |
| claude | CLAUDE.md | harness_instructions | claude |
| gemini | GEMINI.md | harness_instructions | gemini |
| copilot | copilot-instructions.md | harness_instructions | copilot |
| skill | SKILL.md, suffix .skill.md, prefix sk_ | skill_instructions | None |
| generic | Any unmatched file | Existing generic classification | None |

The SKILL suffix/prefix and case-insensitive matching preserve TESSERA's existing
compatibility rules, not a claim that every runtime recognizes them. An unknown
guide retains its existing canonical classification; `AGENTS.md.txt` does not
match `AGENTS.md`. Generic decision/report/experiment/README handling is unchanged.

Recognized instruction files default to `drawer=None`. Explicit canonical
frontmatter remains source-owned and wins over defaults under the existing
contract. No filename creates a user preference. AGENTS and SKILL are not
implicitly tied to a particular vendor.

Official format references checked 2026-10-02:
[AGENTS.md](https://agents.md/),
[Claude project memory](https://code.claude.com/docs/en/memory),
[Gemini context](https://geminicli.com/docs/cli/gemini-md/),
[Agent Skills specification](https://agentskills.io/specification).
Only file identity is used here. Runtime-specific loading, import resolution,
applicability and precedence rules are intentionally not reproduced.

## Inspect and extend without global mutation

```python
from tessera.harness_adapters import DEFAULT_HARNESS_ADAPTERS, HarnessAdapter
from tessera.canonical import parse_and_normalize

selection = DEFAULT_HARNESS_ADAPTERS.inspect("src/AGENTS.md")
print(selection.to_dict())
# adapter_id=agents, document_type=harness_instructions, harness=None,
# evidence=filename:AGENTS.md

registry = DEFAULT_HARNESS_ADAPTERS.register(
    HarnessAdapter("custom", filenames=("PROJECT_RULES.md",), harness="custom")
)
metadata = parse_and_normalize(
    "# Build rules\nRun unit tests.", "/project/PROJECT_RULES.md", "/project",
    adapter_registry=registry,
)
assert metadata.classification.drawer is None
```

Registration returns a new immutable registry; it does not mutate Engine/global
configuration or the built-in registry. The Engine uses the versioned built-ins.
Applications can pass their explicit registry to canonical normalization; runtime
plugin loading and cache-aware custom Engine registration are not introduced.
Adding a built-in convention requires changing only the registry plus its fixtures,
not retrieval. A custom registry is not silently applied to an existing cache.

More than one matching adapter raises a deterministic ambiguity error listing
adapter IDs. Registration order never acts as precedence. Duplicate/reserved IDs
and invalid filename rules are rejected. The generic path always exists.

## Source truth and scope

Adapters emit filename-derived document type and harness defaults with a filename
evidence marker. Canonical normalization still owns identity, explicit name/YAML,
source paths, document/content hashes, exact spans, drawer selection and provenance.
Metadata-origin markers remain unchanged: explicit, inferred, default or system.

Existing project/folder scope defaults remain deterministic location defaults;
they are not verified runtime applicability or authority. Explicit scope metadata
wins. The registry neither reads included files nor rewrites source text. Source
hashes/spans and current retrieval results retain the pre-registry contract.

## Validation and limits

Ten frozen canonical outputs from `main` at
`20814a47ec0f72d7bea0639e0b057df1ecf5cded` must match exactly except runtime
`indexed_at`. Tests cover supported/unknown formats, mixed case, ambiguous names,
explicit metadata, provenance equality, independent registries and invalid rules.
A five-query source corpus also produces identical full results after excluding
only `indexed_at`, and source bytes stay unchanged.

The local five-adapter microbenchmark ran five repeats of 10,000 selections;
median selection cost was about 2.93 microseconds on this execution environment.
This is local overhead evidence, not a latency guarantee or retrieval-quality
benchmark. #32 and #72 still own scope/authority and instruction resolution.
