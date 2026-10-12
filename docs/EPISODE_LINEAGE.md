# Source episodes and atomic-memory lineage

Issue [#137](https://github.com/LuigiFerronatto/TESSERA/issues/137) adds an
inspectable source for automatically decomposed memories. It does not decide
episode boundaries, extraction passes, semantic support, or current truth.

## Source input and inspection

```python
from tessera import Episode, EpisodeTurn, TesseraEngine

engine = TesseraEngine("./memories")
episode = Episode.from_turns([
    EpisodeTurn(31, "assistant", "Short summaries would reduce reading time."),
    EpisodeTurn(34, "user", "Yes, I prefer short summaries.", "2026-01-01T12:00:00Z"),
])
# Offline fallback works with no provider. Each nonempty source line retains
# its actual source turn; keyword classification is still only a heuristic.
paths = engine.decompose_and_write_episode("demo/summary", "dialogue/summary", episode)
source = engine.inspect_source_episode("dialogue/summary")
assert [turn["position"] for turn in source["turns"]] == [31, 34]
```

`EpisodeTurn.position` is a positive integer order key supplied by the source
producer. Positions are unique, increasing and may be sparse. They are local
to that episode. `role` is a nonempty source-provided string; an unknown role
must be explicitly represented by the producer rather than inferred from text.
`timestamp` preserves the original string or `None`; no time is fabricated.
The source body keeps exact content, including whitespace. Character ranges
are measured in Unicode codepoints. CRLF/control-character content uses an
explicit JSON-string encoding so text readers cannot silently normalize it.

Source records live in the reserved store-local `_episodes/<ID-hash>.md`
namespace, outside the disposable index. Their metadata declares
`document_type: reference`, `node_type: source_episode`, and therefore no fourth
semantic drawer. They can be indexed as context but are not atomic-memory hits.
`inspect_source_episode()` reads them independently of a built index and returns
ordered turns, roles, timestamps, content, exact line spans and Evidence Ledger
source identity/version. `persist_source_episode()` explicitly retains a source
without decomposing it. Both methods use the same record representation.

A source ID can be reused only for identical content. Publication is atomic and
no-clobber; conflicting content raises `LineageValidationError`. Raw source text
passes the existing gate and is never sanitized/replaced silently. A source
requiring rejection, review or transformation is not persisted. A failed later
memory write may leave its source record available, never a memory whose source
was intentionally deleted. `_episodes` is protected from the normal memory
writer. Back it up with the source store, not as a disposable cache.

## Candidate support and temporal position

A turn-aware assisted response has the existing type/content fields plus:

```json
{"type":"preference","content":"The user prefers short summaries.","supporting_turns":[31,34]}
```

Every turn-aware candidate needs nonempty, ordered, unique, source-bounded
support. Unknown IDs, booleans, fractions, strings, duplicates and reversed
positions fail validation before any candidate/source persistence. These
lineage errors are not silently converted into heuristic support. Expected
provider and JSON/schema failures still use #135's deterministic fallback;
a valid empty array still means no candidates and causes no source write.

The last supporting position defines `temporal_position`, here `34`. If the
provider supplies it, it must match exactly. This number is not a timestamp,
`valid_from`, `valid_until`, current truth, or an ordering across episodes.
Source timestamps remain separately inspectable; earlier and later preference
memories are both retained without automatic supersession (#15/#16).

References establish which source turns a candidate cites. Neither a valid ID
nor an exact source span proves semantic entailment. Even an incorrect inference
can cite existing turns; semantic extraction quality remains #136's concern.
Provider-supplied source paths, hashes and Evidence IDs never become authority.

## Canonical metadata and result parity

Existing native `episode_id` and `provenance_turns` remain the writable fields.
Automatically written notes add `temporal_position`, `episode_source` and
`source_evidence`. `CanonicalMetadata.lineage` is their normalized projection,
not a second writable schema. The writer verifies the projection against the
actual source version before writing. Index schema 3 invalidates older caches;
all metadata can be rebuilt from the Markdown source files.

For automatic memories, Engine results and their CLI JSON/MCP projections add:

```yaml
lineage:
  source_episode_id: dialogue/summary
  supporting_turns: [31, 34]
  temporal_position: 34
  temporal_position_semantics: last_supporting_turn_position_within_source_episode
  support_semantics: source_reference_only_not_semantic_entailment
  status: verified
  episode_source: {schema_version: 1, evidence_id: ev_..., source: {...}, span: {...}, ...}
  source_evidence: [{schema_version: 1, evidence_id: ev_..., source: {...}, span: {...}, ...}]
```

`episode_source` is the independently persisted source's standard Evidence
Ledger record. `source_evidence` uses the same source-document/hash/span-aware
EvidenceRecord contract for each cited turn and the derived memory identity.
Repeated text has distinct provable spans because ranges address actual source
positions. Verified support records are also rebuilt into the Evidence Ledger
and can be looked up by their Evidence IDs. Missing/changed support records are
excluded from that verified ledger while their pinned references remain visible
with a diagnostic status. Existing hit `provenance` and query-specific `evidence` continue to
describe the persisted atomic note; they are not relabeled as original-dialogue
evidence. No new source/version authority model is introduced.

`status` is recomputed against source files: `verified`, `missing_source`,
`invalid_or_changed_source`, or `episode_only_no_source_turns`. Missing/edited
sources remain visible as broken lineage; the engine never repairs them from
an atomic memory or rebinds stale references to a newer version. Pinned records
remain available for audit but must not be read as fresh when status is broken.
The readable index summary also exposes canonical lineage; cache reload and
clean rebuild preserve the same result semantics.

## Compatibility and scope

Existing manual write calls keep their old signatures and output unless the
new keyword-only `lineage` is supplied to the canonical writer. Manual
`episode_id`/`provenance_turns` alone do not establish verified source lineage.
Existing `Episode(beginning, middle, end)` and CLI/MCP section inputs are still
accepted: their exact sections are retained, with empty supporting turns,
null temporal position and `episode_only_no_source_turns`. Summaries cannot
reconstruct actual interaction turns, so no IDs or roles are invented. Existing
notes are not silently migrated or rewritten. Turn-aware source ingestion and
inspection are Python APIs; adding live producer/CLI turn inputs is separate.

Legacy-source enrichment (#176) must reuse the EvidenceRecord document/version/
span contract; this change does not implement an enrichment producer. It does
not implement semantic boundaries (#138), QUMem decomposition passes (#136),
temporal state (#15), version history (#73), durable write receipts (#263), or
claim provider-backed extraction/state-quality results.
