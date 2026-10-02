# Experimental Open Knowledge Format exchange

## Status and boundary

Issue [#204](https://github.com/LuigiFerronatto/TESSERA/issues/204) has an
**ITERATE candidate**, not a promoted import pipeline. This experiment adds
read-only import and export **plans** and tests semantic exchange offline.
It does not persist imports, change native discovery, install providers,
modify Engine ranking or make OKF the internal storage model.

```text
OKF ↔ isolated adapter ↔ Canonical Metadata ↔ Engine / Retrieval / Evidence
     plans only                         synthetic smoke only
```

The last arrow is exercised by a test-only temporary synthetic corpus. Actual
user-store persistence still requires integration with admission/write safety,
source exposure policy and explicit commit approval. An accepted candidate in
an import report is not an admitted memory. Do not feed the preview directly
into a store as a substitute for that integration.

## Audited external contract

- Repository: [GoogleCloudPlatform/open-knowledge-format](https://github.com/GoogleCloudPlatform/open-knowledge-format)
- Specification: [SPEC.md at ad30107c31c06aec8a7d5636e0d1058118604e6f](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md)
- Advertised version: 0.2; observed 2026-10-02
- SPEC.md SHA-256: `26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101`
- Upstream [issue #24](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues/24)
  explains why the version label alone cannot pin timestamp semantics

Sections 4.1 and 11 require a non-empty concept type, permit arbitrary unknown
fields and types, and tolerate broken links. Sections 3, 8 and 9 reserve
index.md/log.md for navigation/history. Section 5 now defines timestamps as
ISO datetimes with explicit offsets; date-only freshness values are diagnosed
and never given a guessed timezone. Section 6 defines bundle-root and relative
links. Section 10 describes attestation metadata, not permission to execute it.

The independent upstream reference parser/required-key validator is frozen in
`tests/reference/okf_document.py`, retaining its Apache-2.0 license. It checks
concept syntax and the required key, **not every specification recommendation**.
Local structural validation and upstream validation are separately reported;
neither is described as complete external certification.

## Commands: deterministic JSON, no persistence

```bash
python -m tessera.okf validate tests/fixtures/okf_v02
python -m tessera.okf plan tests/fixtures/okf_v02 --namespace synthetic-project
python -m tessera.okf export-native tests/fixtures/okf_native
python benchmarks/okf_roundtrip/run.py
```

`validate` reports external structure, import mapping and safety separately.
`plan` adds canonical candidate records, unchanged bodies, original metadata,
advisory trust/lifecycle signals and reserved navigation/history files.
`export-native` emits a path-to-text dictionary and file hashes on stdout.
There is no `--apply` or `--output` switch. Commands do not construct an Engine,
read project configuration, enumerate other stores or write source files.
A mapping/safety problem exits 2. Warnings may accompany a consumable concept.
The command is intentionally separate from the main `tessera` CLI/MCP.

Python callers can use `plan_import`, `export_records`, `plan_native_export`
and `native_preview`. The preview is a review artifact; it is not a lossless
persistence API. All imported bodies and metadata remain untrusted data.

## Mapping and identity

| External concept | Candidate canonical treatment |
|---|---|
| type | Preserved in raw external metadata; generic factual memory classification |
| title | identity.name, or diagnosed filename-derived display name |
| tags | Searchable tags, plus original metadata |
| resource | Original provenance; stable ID evidence within an explicit namespace |
| sources, footnotes | Preserved intact, not fetched |
| generated / generated.at | Preserved generation metadata; never observed_at/recorded_at |
| verified | Mapping normalized to a one-event list for advisory trust display |
| stale_after | Freshness metadata; never valid_until |
| status | Lifecycle signal; never destructive supersession |
| ordinary supported inline links | Explicit related_to candidates when target resolves |
| unknown producer fields | Preserved without interpretation |

For first import without a TESSERA extension, a non-empty resource plus an
explicit stable namespace supplies deterministic identity evidence. Hashing
that evidence encodes the ID; body hashes and paths are **not** its identity.
Multiple concepts sharing that evidence require review, even if their types
are different. No resource means valid OKF may still need identity review.
A moved file with the same resource/namespace retains its memory/document ID;
its physical source path and document bytes can change. Resource edits require
identity review or an explicitly reviewed stable extension; no automatic merge
is attempted. Changing the namespace intentionally changes derived identities.
An existing canonical extension carries its canonical ID across moves.

Source document identity, original path, body/document hashes and span remain
in the canonical candidate and extension. A temporary native preview gains its
own current source provenance through the normal Engine; the original source
is retained separately as okf_exchange_provenance. These are not interchangeable.

## E1 extension contract and round-trip guarantees

The selected experiment is native OKF fields plus `tessera_exchange`, permitted
by section 4.1. E0 alone would flatten typed relations and truth validity; E2
sidecars add a second coordination mechanism with no demonstrated need here.

The namespace contains:

- profile: tessera-canonical-v1
- canonical: the existing schema-1 CanonicalMetadata dictionary
- external_frontmatter_hash: deterministic integrity check for the outer fields
- any unknown additional extension members, preserved on exchange

Typed relation target/type/origin, scope, quality, state_key, superseded_at,
source provenance, raw frontmatter, utility and truth timestamps travel in the
canonical snapshot. The only excluded field is temporal.indexed_at, a derived
runtime clock. Source-body and outer-metadata hashes reject stale snapshots;
these hashes are consistency checks, **not authenticated signatures**. Unknown
namespace profiles or canonical schema versions require review, not guessed
migration or namespace overwrite.

Within the tested supported profile, OKF → canonical → OKF → canonical and
native canonical → OKF → canonical preserve semantic dictionaries and bodies.
YAML ordering/quoting is normalized, so byte identity of exported documents is
not promised. Source inputs remain byte-identical. Export hashes are deterministic
for the same candidate state. Broken links remain in bodies with diagnostics;
no source or attestation is fetched to resolve them.

## Safety and supported-profile limits

- Local directories only; no archive extraction, URLs, network or LLMs
- Symlink roots/ancestors/children and special files rejected or diagnosed;
  symlink directories never traversed
- Path normalization and percent-decoded traversal checks on links and known
  path-valued fields; bundle-root `/` means the selected root, never filesystem `/`
- 1 MiB per Markdown file, 16 MiB per bundle, 1,000 entries; UTF-8 only
- Non-Markdown files are listed as skipped and never read or executed
- YAML safe types only; duplicate/non-string keys, aliases/anchors, recursive
  or non-finite/non-JSON metadata require review; unknown ordinary fields work
- Attested Computation remains inert: no executor/attester invocation, no receipt
  verification and no claim that an attestation passed
- Trust tiers are unauthenticated producer claims and never access control or
  canonical authority scores
- Work against a stable local snapshot; adversarial concurrent directory-tree
  replacement is not supported by this prototype

Canonical relationship extraction covers simple inline Markdown links. Reference-style and complex links require review; fenced/inline code examples
are excluded. Embedded HTML, indented code and full Markdown AST semantics need
another adapter iteration. Original body
bytes remain available; do not infer comprehensive graph extraction from this
fixture. Native exports with non-JSON raw frontmatter require review rather
than silently converting values. Native reserved filenames need an explicitly
chosen export path. No automatic private/excluded filtering is implemented:
only explicitly selected synthetic input was used in this experiment.

## Evidence and remaining gates

The frozen corpus includes ten concepts, three resolved links, historical and
current/conflicting claims, a deprecated concept, freshness boundary, human and
machine verification, source attribution, unknown extensions and an inert
attested computation. A separate native object carries three typed relations,
scope, quality and truth timestamps.

[Reproducible A0–A4 results](../benchmarks/okf_roundtrip/result.json) report
10/10 external and 1/1 native canonical records preserved, empty semantic diff,
three native typed relations preserved, independent upstream validation of
10 input + 10 re-exported + 1 native-exported concepts, deterministic output
and same-result retrieval/evidence smoke. Latencies are observational synthetic
single runs, not production performance claims.

The decision remains ITERATE. Admission/persistence, realistic-corpus evidence,
independent comprehensive conformance audit, identity review UX, broader
versioned JSON/Markdown/Obsidian/CSV profiles, selection/privacy/exposure policy,
encrypted-store behavior and exact-head governance/merge gates remain open.
No retrieval-quality improvement, full issue completion or promotion is claimed.
