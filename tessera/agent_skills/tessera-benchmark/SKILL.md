---
name: tessera-benchmark
description: Reproduce TESSERA deterministic benchmark evidence in a source checkout while keeping model readers and judges separate.
metadata:
  tessera-package: tessera-agent-memory
  tessera-minimum-version: "0.0.3"
  tessera-bundle-version: "1"
---

## Prerequisites and compatibility
This skill requires the TESSERA source checkout containing
`benchmarks/sanity/ci_eval.py`; the installed runtime wheel intentionally excludes
benchmark code/data. Check that the checkout commit and installed package refer
to the intended candidate. Do not claim the version string identifies a commit.

## Deterministic smoke evaluation
Run from the verified repository root into a dedicated artifact directory:

```bash
python benchmarks/sanity/ci_eval.py --output-dir artifacts/sanity
```

Preserve the emitted dataset ID, query count, Hit@k, MRR, evidence hit rate,
missing-evidence result and artifact paths. Record commit, Python/dependency
versions, exact command and baseline identity. Compare candidate and baseline
using the same frozen data and settings. Four-query sanity is a smoke gate, not
LongMemEval, full QUMem fidelity or a broad answer-quality result.

## Required benchmark routing
Read the checkout's `docs/BENCHMARK_CI.md` and the owning Test Card before a PR
claims REQUIRED, SMOKE_ONLY or NOT_APPLICABLE. Use the repository's existing
runner and integrity checks, not a parallel implementation. An applicable
required benchmark must complete on the exact candidate; offline reporting
success alone is not the quality run.

Provider-backed readers/judges and external datasets have separate schemas,
licenses, data-sharing, credential and cost requirements. Never download large
models/data, transmit a private corpus, configure credentials or run paid
inference just because a smoke check passed. If inputs or approval are missing,
prepare the reproducible command/manifest and report the exact unexecuted stage.
Do not fabricate metrics, alter frozen fixtures after inspecting test outcomes,
or weaken success criteria to make a change pass.
