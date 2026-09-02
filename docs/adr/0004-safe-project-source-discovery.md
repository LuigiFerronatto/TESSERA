# ADR 0004: Safe project source discovery

- Status: Accepted for the Issue #154 implementation candidate
- Date: 2026-09-01
- Issue: [#154](https://github.com/LuigiFerronatto/TESSERA/issues/154)

## Context

Configuration v2 (#153) defines which paths are the write store, explicit read
sources, and derived index. It deliberately does not inspect the project or
suggest additional sources. A later onboarding flow (#155) needs a safe,
explainable proposal without gaining authority to scan outside the project,
select files, mutate configuration, or start indexing.

## Decision

`tessera.source_discovery.discover_sources()` resolves exactly one supplied
project root and returns a versioned `SourceDiscoveryPlan`. The plan contains
deterministically ordered file/directory entries, top-level location clusters,
classification totals, diagnostics, and scan counters.

The explicit classification vocabulary is:

```text
RECOMMENDED  supported Markdown suggested by default
SUPPORTED    selectable Markdown not suggested by default
IGNORED      excluded by ignore/default/format/size/readability policy
FORBIDDEN    security or containment boundary; never ordinarily selectable
```

The scanner uses `lstat`-style metadata and suffix/path rules. Markdown is the
only supported format because the canonical runtime indexes only Markdown;
#154 does not absorb #69 ingestion or #70 segmentation. Files larger than 2 MiB
are ignored before content reads. All symlinks are skipped and represented as
forbidden diagnostics, including aliases whose target remains inside the root.
This avoids escapes, loops, and duplicate physical counting.

Mandatory exclusions are evaluated before ordinary ignore logic: `.git`, the
resolved `index.path`, legacy `.tessera_index`, special filesystem entries,
`secrets/`, `.env` variants, credentials artifacts, private-key suffixes, and
common private-key filenames. Filename policy is a conservative high-confidence
deny list, not a claim of content-based secret detection. Safe example/template
credential names remain unsupported rather than selectable while their format
is outside current ingestion.

An optional root `.tessera-ignore` supports UTF-8 blank lines, `#` comments,
ordered patterns using `*`, `?`, `**`, directory suffix `/`, and `!`
re-inclusion. Absolute/parent-traversal patterns, empty negations, and bracket
classes are diagnosed as unsupported. This is a documented subset, not full
`.gitignore` compatibility. Re-inclusion may override safe convenience ignores
such as `archive/`, including recursive forms such as `!**/decisions.md` and
`!archive/**/keep.md`, but never mandatory exclusions.

Important root files remain individual entries. Nested paths are clustered by
their actual top-level directory; counts preserve supported, recommended,
ignored, and forbidden children. Cluster classification and selectability come
from safe selectable children, so a forbidden child remains visible through its
count without poisoning safe siblings; forbidden-only clusters remain
forbidden. Ordering is recommendation class then normalized path.

## Boundaries and consequences

Discovery is read-only and project-root-bounded. It never enumerates an
ancestor, sibling, `$HOME`, global registry, or external schema-v1 store. It
does not mutate `store.path`, `sources`, `index.path`, source bytes, config,
`.tessera-ignore`, or index files. Existing v1/v2 selected corpora therefore
remain unchanged until a separate future #155 confirmation persists an
explicit plan.

`tessera config doctor --json` may expose the structured plan and reject an
invalid/unreadable ignore contract. It does not become a picker or general
corpus doctor. #155 owns display/select/confirm/persist/index; #166 owns broad
rendering; #13 owns corpus diagnostics; #12 owns incremental indexing.
