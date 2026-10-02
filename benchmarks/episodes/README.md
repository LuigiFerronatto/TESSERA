# Role-aware episode experiment (#138)

Status: **draft preparation, opt-in, not a selected runtime replacement**.
The canonical `tessera.episode_boundary.EpisodeBoundaryTracker` (E0), installed
package, Engine/CLI/MCP, source persistence and decomposition are unchanged.
This directory is excluded from distribution artifacts.

The 13 new synthetic dialogues / 52 source turns exercise the eight requested
scenario classes plus intentional lexical counterexamples. Their author-draft
labels are **not independent human review**, ground truth or evidence of
real-world quality. No provider, embedding model, download or credential is
used. E2 is unimplemented and not justified by this small diagnostic.

## Run locally

From an editable development checkout with its normal dev dependencies:

```bash
python -m pytest tests/test_episode_boundary.py
python -m benchmarks.episodes.run --output artifacts/episodes/draft.json
python -m benchmarks.episodes.run --output artifacts/episodes/summary.json --summary
python -m benchmarks.episodes.prepare_review --output-dir artifacts/episodes/review-v1
python -m benchmarks.episodes.run --output artifacts/episodes/reviewed.json --require-reviewed
```

The last command deliberately exits 2 without creating a report: independent
review has not happened. Do not replace that failure with a claimed pass.
`prepare_review` refuses an existing output directory so it cannot overwrite
human annotation work. Give reviewers only `dialogues-blinded.json`, their
respective blank ballot and the annotation instructions below. Do not give them
this directory's labels, scenario purposes or variant predictions before they
lock their independent ballots. Dialogue and source IDs are opaque in the
review packet. The packet preserves ordered raw source content and metadata.

## Variants and explicit contracts

| Variant | Semantic signal | Timeout membership rule | Runtime status |
|---|---|---|---|
| E0 | Actual current accumulated-text TF-IDF across all untyped turns | Current last-turn timeout | Unchanged default |
| E1 | Adjacent user lexical continuity, frozen short-ack abstention and explicit-switch rules | Measured separately, never changes E1 membership | Harness-only |
| E3 | Identical E1 semantic signal | OR with independently reported previous-user time gap | Harness-only |

E0 executes the real `add_turn`/`flush` implementation. A returned close identifies
a source boundary; the harness retains all original turn IDs alongside it.
It does not reverse-parse B/M/E text or substitute a rewritten baseline. E0
exposes no separated semantic/timeout reasons, so its reason field is null.
The shared defaults are TF-IDF cosine `< 0.03` and timeout `> 30` minutes.

E1/E3 accept explicit `user`, `assistant`, `tool` or `system` roles, source ID,
positive increasing sparse position, exact content, nullable ISO-8601 timestamp,
session ID and task ID. Roles are never inferred from content. Missing/unknown
roles, duplicate IDs, reordered positions, mixed sessions/tasks, timezone-less
times and decreasing known timestamps are rejected. Empty content is retained;
it produces no lexical evidence. Missing time remains unknown, never fabricated
from wall-clock time. Segmentation is repeatable for identical inputs.

Only **adjacent user turns** enter semantic classification. Intervening
assistant/tool/system records and leading context stay in their original order,
with their original content, metadata and IDs. A new user boundary assigns that
user and subsequent context to the new episode; preceding context remains in
the previous episode. Non-user-only input stays one context segment. Session or
task boundaries must be routed separately by the capture adapter.

The frozen acknowledgement vocabulary is `sim`, `ok`, `okay`, `faz isso`,
`yes`, `do it`, `continue`, ignoring case and punctuation. If either adjacent
user is such an acknowledgement, the semantic signal abstains and E1 continues.
It never silently substitutes an older user turn. Other short requests such as
`Book flights` still receive a lexical comparison. English/Portuguese explicit
switch prefixes override this abstention; this is a transparent lexical rule,
not learned semantic understanding or a complete multilingual contract.

E3 computes its operational gap between the same adjacent **user** timestamps,
not time since the most recent assistant/tool output. This deliberately differs
from E0's last-any-turn timeout and is recorded in every decision. A busy tool
stream does not hide a long user pause. Exact threshold equality continues;
missing either user time means `timed_out: null`. A timeout may split an otherwise
semantically continuous task; the long-pause fixture exposes that false split.
A semantic decision and a timeout decision are always reported separately.

## Source membership is not B/M/E

E1/E3 return ordered source memberships and decision traces; they do not write
memories or produce summaries. Beginning/Middle/End is an optional **TESSERA**
rendering/summary structure applied after membership. It is not attributed to
QUMem, is not a boundary classifier, and never replaces the raw turns. Existing
E0 B/M/E formatting remains untouched for a genuine baseline comparison.

## Canonical #137 and capture #177 adapter boundary

`ExperimentTurn` is confined to the benchmark. It is not exported by `tessera`,
not an ingestion API, and not a second durable turn schema. This candidate is
based on canonical `20814a47ec0f72d7bea0639e0b057df1ecf5cded`; it does not assume
that the unmerged [#297 lineage draft](https://github.com/LuigiFerronatto/TESSERA/pull/297)
exists on `main`. That draft supplies `EpisodeTurn(position, role, content,
timestamp)` and `Episode.from_turns`.

After #137 is merged and its current contract is verified, the exact prospective
projection for each already-segmented episode is:

```python
Episode.from_turns([
    EpisodeTurn(position=t.position, role=t.role,
                content=t.content, timestamp=t.timestamp)
    for t in membership
])
```

Positions must be the preserved real source-order keys, not synthetic turn IDs
or summary section numbers. A companion adapter mapping must retain each
`(session_id, task_id, turn_id, position)` binding; #297's present `EpisodeTurn`
has no `turn_id`/session/task fields, so the projection alone is **not** a complete
lossless ingestion adapter. Empty records are retained here; #297 currently
rejects empty turn content, so a reviewed capture/lineage decision is required
rather than dropping, padding or fabricating those records. No durable adapter
is enabled in this PR.

#177 normalized events are the preferred future source. Its adapter must retain
runtime-provided identities/order and explicitly map `user_turn` to user,
`assistant_turn` to assistant, and tool call/result events to their true source
roles. Lifecycle, feedback and error events require a documented mapping, not
role inference from text. Capture must not decide episode semantics. #136
consumes decided source episodes separately; this PR neither changes typed
decomposition nor assumes boundary improvement implies extraction improvement.

## Metrics and frozen artifacts

`dialogues.sha256` freezes the exact JSON bytes. `annotation-template.json`
binds blank ballots to that hash and keeps every unreviewed label null. Editing
labels/turns after review starts requires a new version, fresh hash and disclosure;
do not silently refresh this checksum to make an altered fixture appear frozen.

The report records fixture hash, source-file hashes, Git HEAD and dirty status,
Python/scikit-learn versions, per-case memberships and E1/E3 traces. It runs each
variant twice and compares outputs excluding measured latency. Timing is a small
single-process diagnostic, not a speed guarantee; first-run E0 work and warming
can differ. Persisted evidence identifies exact measured source bytes even when
documentation commits later change HEAD.

All scores live under `draft_label_diagnostics`. Boundary precision/recall/F1
count boundary starts across **all** inter-turn slots, so E0 assistant/tool
false splits are not hidden. False split = FP/reference-negative slots; false
merge = FN/reference-positive slots. Unavailable rates use null. Perfect empty
predictions/references have F1=1. Corpus precision/recall/F1 aggregate counts.
WindowDiff compares boundary counts in windows of `k=max(1, round(N/(2*S)))`
slots, clipped to the available slots, where S is the reference episode count;
the corpus result is the unweighted mean over dialogues. Length distributions
count source turns, not tokens. The runner records wall-clock milliseconds per
turn and exact repeatability separately.

Human boundary precision/recall/F1 and downstream decomposition delta remain
**null**. Draft-label numbers cannot satisfy #138's success gate or justify
selecting E1/E3. The report's decision stays `PENDING`.

## Independent annotation and decision protocol

1. Lock the fixture hash, code revision, parameters and this protocol before
   human review. Record any future change as a new experiment, never a relabelled
   run. Keep a representative holdout separate from this author-designed
   development fixture before making generalized quality claims.
2. Two independent human reviewers each receive a blinded packet. Record reviewer
   identity, review date and whether they saw model predictions/draft labels.
   An automated agent or self-review cannot count as independent human review.
3. Label each new semantic episode by the starting user `turn_id`. The first
   user is not a boundary. Keep the same task together across clarifications,
   acknowledgements, tools and a long pause. Split on a new user task/topic even
   if vocabulary overlaps. Read assistant/tool content as context for human
   interpretation; do not label a boundary merely because its vocabulary changes.
   Pure operational timeout is recorded separately from semantic labels.
4. Use an empty boundary list only when reviewed and genuinely no boundaries;
   null means unreviewed. Record rationales and ambiguous turns. Do not force
   ambiguous cases into invented certainty.
5. Lock both independent ballots before comparing them or inspecting predictions.
   Report exact agreement, boundary agreement/F1 between reviewers and disputed
   positions. A documented human adjudication resolves disagreements, preserves
   original ballots, rationale and a third-party reviewer where needed. This
   directory contains no completed or adjudicated ballots.
6. Freeze the adjudicated reviewed set as a separately identified version; add
   a strict reviewed-label loader with fixture identity, complete coverage and
   unknown-turn checks. Such a loader is intentionally not faked here. Re-run
   E0/E1/E3 on exactly the same reviewed inputs and retain per-scenario errors.
7. Proposed pre-review boundary gate: E1/E3 must improve micro boundary F1 by at
   least 0.10 absolute over E0 without worse macro WindowDiff or short-turn false
   split count, retain 100% of source records, and repeat deterministically.
   Report uncertainty and sample size; these 13 synthetic cases alone cannot
   establish generalization. A simpler variant may be chosen by an explicit
   maintainer decision with measured cost/complexity evidence, not silently.
8. With #136/#137 canonical interfaces available, freeze one decomposer/config
   across E0/E1/E3. Human-review factual/preference/insight extraction and source
   support on identical dialogues, recording quality deltas and cost. Unit tests,
   the retrieval sanity test and LongMemEval do not substitute for that work.
9. A maintainer records KEEP E0/E1/E3, ITERATE or DROP only after reviewing the
   evidence. E2 needs a separately justified model/dependency/cost experiment.
   Default behavior changes require a later reviewed runtime PR. Do not close
   #138, mark the reviewed-fixture readiness gate satisfied or claim improvement
   merely because the harness or draft diagnostics pass.
