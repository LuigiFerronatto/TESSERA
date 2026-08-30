# LongMemEval V1 minimal retrieval baseline

This adapter measures the current TESSERA retrieval contract at session granularity. It does not run LongMemEval retrievers, answer generation, a reader, the GPT-4o evaluator, or an LLM judge. The 50-question result is a deterministic development baseline, not an official full LongMemEval score.

## Frozen sources

| Input | Frozen value |
| --- | --- |
| Repository | `https://github.com/xiaowu0162/LongMemEval` |
| Commit | `9e0b455f4ef0e2ab8f2e582289761153549043fc` |
| Repository license | MIT |
| Dataset | `longmemeval_s_cleaned.json` from `xiaowu0162/longmemeval-cleaned` |
| Dataset SHA-256 | `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` |
| Dataset revision label | `cleaned-2025-09` |
| Frozen retrieval contract | `fb23012ba4b2fddc3912d7cb593391a04fe45ae7` (PR #98 merged) |
| TESSERA implementation measured | Resolved from checked-out Git `HEAD` at run time |

LongMemEval V2 is future context only: `https://github.com/xiaowu0162/LongMemEval-V2` at `2cc8c540bdb87fe6761629b585e727e1c4704520`. The setup does not clone, download, install, or execute V2.

## Setup

```bash
bash benchmarks/longmemeval_v1/setup.sh
```

The script creates ignored `.benchmark-cache/LongMemEval/` and `.benchmark-data/longmemeval-v1/` directories, validates the official remote and pinned commit, refuses a dirty external clone, atomically downloads/checksums the dataset, and installs only TESSERA's `dev` extra. It never executes LongMemEval code or installs either LongMemEval requirements file.

## Baseline command

```bash
python -m benchmarks.longmemeval_v1.run \
  --dataset-path .benchmark-data/longmemeval-v1/longmemeval_s_cleaned.json \
  --subset deterministic-small \
  --limit 50 \
  --top-k 10 \
  --output-dir artifacts/longmemeval-v1/baseline
```

Optional full 500-question retrieval run:

```bash
python -m benchmarks.longmemeval_v1.run \
  --dataset-path .benchmark-data/longmemeval-v1/longmemeval_s_cleaned.json \
  --subset full \
  --top-k 10 \
  --output-dir artifacts/longmemeval-v1/full
```

## Validation and selection

The loader requires a JSON list of exactly 500 unique questions and validates all official required fields, aligned session arrays, session lists, and `role`/`content` turns. A checksum mismatch fails before indexing.

The small subset is reconstructed as follows:

1. Group by `question_type`.
2. Mark abstention when `question_id` ends with `_abs`.
3. Allocate 50 proportional type quotas using largest remainder with lexical tie-breaking.
4. Rank each positive/abstention stratum by `sha256("tessera-lme-v1-96:" + question_id)`.
5. Select each type quota with proportional abstention representation and sort the final set by type plus hash.

`selected_questions.json` records order, group, abstention status, and hash. `manifest.json` records quotas and all selected IDs.

## Session projection and leakage controls

Each question receives a fresh temporary corpus. Every haystack session becomes one native TESSERA Markdown document with stable ID:

```text
longmemeval-v1/<question_id>/<session_id>
```

The body preserves the session timestamp, turn order, role, and complete content. Ground-truth fields and derived relevance labels—including `has_answer`, `answer_session_ids`, expected answers, `is_relevant`, and evidence labels—are absent from frontmatter, serialized Markdown, tags, entities, provenance, and searchable/indexed text. The evaluator retains ground truth separately and joins it to stable session IDs only after retrieval. The temporary corpus is destroyed before the next question.

Official `_abs` rows may still carry evaluation-reference `answer_session_ids`. Per the abstention contract, the adapter never treats them as positive retrieval locations and normalizes result `ground_truth_session_ids` to `[]`.

The cleaned file contains 13 repeated session-ID occurrences across 13 questions; their turn content is byte-for-byte equivalent. The adapter deterministically keeps the first occurrence for each session ID so the required stable identity remains unique and repeated copies cannot distort retrieval.

## Artifacts and metrics

Each run writes:

```text
manifest.json
selected_questions.json
results.json
scorecard.json
scorecard.md
```

Metrics are Recall@1/3/5/10, MRR, binary nDCG@10, evidence hit rate, first evidence position, provenance coverage, average context characters/tokens, indexing latency, query latency p50/p95, and abstention retrieval empty rate. Whitespace counting is deterministic and is not presented as model-token usage. Abstention questions are excluded from Recall/MRR/nDCG and reported separately.

## Reproducibility

The runner resolves the checked-out Git `HEAD` as `tessera_commit` and records the frozen PR #98 contract separately as `retrieval_contract_commit`. It serializes `repository_root` as stable `.` rather than an absolute machine path. A dirty worktree fails by default because a commit SHA could not identify the code measured. `--allow-dirty-worktree` is an explicit escape hatch that records `repository_dirty: true`, `dirty_worktree_override: true`, and `reproducible: false`; such an artifact must not be presented as a reproducible baseline.

Run twice into different directories and compare with `compare_runs`:

```bash
python - <<'PY'
from pathlib import Path
from benchmarks.longmemeval_v1.run import compare_runs
assert compare_runs(Path("/tmp/tessera-lme-v1-run-1"), Path("/tmp/tessera-lme-v1-run-2"))
print("equivalent")
PY
```

The comparison includes checksum, selected IDs/order, generated memory IDs, retrieved IDs/order/scores, retrieval metrics, and scorecard schema. It ignores only `created_at`, per-question indexing/query latency, aggregate latency fields, and absolute output location (which is not stored).

## Ledger and CI profiles

The compact canonical dev-50 record lives at
`benchmarks/results/longmemeval-v1-dev-50/baseline.json`; its Markdown view is
mechanically generated and checked in CI. Same-commit repeated runs must have
identical normalized hashes. Cross-commit comparisons first enforce the frozen
dataset, selection, adapter, metric, and retrieval configuration, then compare
metrics and a retrieval-result signature that excludes timestamps and Git
provenance.

Benchmark CI installs with the versioned `constraints-ci.txt` under Python
3.12.14. New ledger records capture the complete forward environment
fingerprint. The #96 record remains the unchanged historical retrieval baseline
with an explicitly incomplete environment; `forward.json` is the separate
pinned-environment drift reference.

CI prepares the dataset through `prepare_dataset.py`, the single authoritative
atomic download/checksum path. Cache hits are verified just like downloads, and
network, cache, upstream, or checksum failures remain explicit infrastructure
failures. The dataset is treated only as data; no LongMemEval code executes.

The future full-500 profile is manual or scheduled, must have a separate name
and record, and must never overwrite dev-50. Reader/answer generation and an LLM
judge remain separate future evaluation layers. LongMemEval V2 is not supported
by this adapter.

## Limitations

- The 50-question slice is a minimal reproducible gate, not the official 500-question result.
- Retrieval and reader quality are intentionally separate; this adapter cannot report answer accuracy.
- Latency is machine-dependent.
- Whitespace token counts are context-size proxies only.
- No retrieval weights, ranking heuristics, graph expansion, temporal behavior, conflict resolution, or arbitration are changed by this benchmark.
