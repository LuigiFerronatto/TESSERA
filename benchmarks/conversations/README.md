# Synthetic historical conversation benchmark

The `evaluate.py` profile is offline and fixture-only. It creates 24 overlapping
sessions, 96 turns across all four supported generic roles, timestamps and tool
references. The raw JSONL baseline is invisible to the existing text index; the
candidate imports one inspectable non-memory source per session and measures
turn retention, query Hit@1, original-byte integrity, idempotent retries and cost.

Run from the repository root with its own installed environment:

```bash
python benchmarks/conversations/evaluate.py --output /tmp/conversations.json
```

The record captures fixture SHA-256, exact Git HEAD and dirty state. Only clean,
exact-head runs are release evidence. Repeat runs must match non-timing metrics.
There is no reader, judge, model, external dataset or private conversation. This
is a source-ingestion experiment, not a competitive retrieval-quality claim.
Required LongMemEval dev-50 CI and the existing sanity gate are separate gates.
