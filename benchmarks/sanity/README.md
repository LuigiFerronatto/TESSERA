# TESSERA Sanity Evaluation

This directory contains the small deterministic retrieval regression gate used by `TESSERA CI`.

It is intentionally **not** LongMemEval and is not intended to compare TESSERA with other memory systems. Its purpose is to catch behavioral regressions in the repository's own retrieval contract while remaining fast, offline, reproducible, and completely project-agnostic.

## Run locally

```bash
python -m pip install -e ".[dev]"
python benchmarks/sanity/ci_eval.py --output-dir artifacts/sanity
```

The evaluator writes:

- `eval-summary.json` — aggregate Hit@1, Hit@3, Hit@5, MRR, evidence hit rate, latency, and returned context size.
- `eval-results.json` — per-query rankings, gold rank, relevant evidence, and latency.

The synthetic fixture covers:

- direct project-purpose retrieval;
- colloquial/paraphrase robustness;
- procedural learning retrieval;
- an operational worktree/CWD gotcha;
- missing-evidence behavior.

The fixture is intentionally generic. Public CI must never require a private project corpus, personal paths, or knowledge of an external agent system.

## CI policy

Changes to retrieval, ranking, graph behavior, metadata, evidence extraction, indexing, temporal resolution, or conflict resolution should be judged by both the Python test suite and this behavioral sanity gate. Aggregate metric thresholds are deliberately conservative and should only be changed with an explicit explanation of the behavioral tradeoff.

Competitive benchmarks such as LongMemEval or MemPalace are intentionally kept out of this public per-PR CI path. They belong to separate benchmark workflows and Test Cards.
