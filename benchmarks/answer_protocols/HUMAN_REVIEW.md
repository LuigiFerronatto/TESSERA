# Draft independent-human calibration protocol (#104)

**Not executed, accepted, calibrated or labeled.** This packet prepares a decision
for reviewers. Do not mark the model, sample, thresholds or human labels accepted
on the strength of synthetic parser tests.

1. Confirm accepted canonical #74/#100/#103 boundaries, legal use of the sample
   and the privacy/retention location for references and persisted reader outputs.
   Select an immutable judge model/revision, exact prompt/rubric and bounded
   execution budget separately. Keep judge data out of the reader's storage and
   process. The reader receives neither calibration labels nor reviewer rationales.
2. Freeze sample membership/order/hash and disjoint calibration/held-out membership
   before model judging or held-out evaluation. Use the eight coverage slots:
   correct, partially correct, unsupported, explicit abstention, incorrect
   abstention, temporal staleness, conflicting claims, malformed/non-responsive.
   Reviewers decide adequate counts for the intended use. No sample size or
   threshold has been accepted in this draft.
3. Assign two independent humans who did not author the reader's outputs or
   prompts. Each sees the question, permitted benchmark reference and already
   persisted reader output, with model/renderer/run identity and the other
   reviewer's judgment concealed. Counterbalance case order with a recorded seed.
   Keep sampling category hints out of the blind review view.
4. Each reviewer records one of `correct`, `incorrect`, `abstain_correct`,
   `abstain_incorrect`, plus a concise evidence-linked rationale and an immutable
   review artifact hash. Partial, stale, unsupported and conflicting answers need
   explicit rubric decisions; do not silently coerce those categories into a
   positive label. A malformed **reader** answer is an answer-quality category;
   a malformed **judge** response is `judge_failure`, never reader incorrectness.
5. Retain both original judgments unchanged. Agreement becomes the reference
   label only with traceability. Disagreement needs a distinct independent third
   adjudicator, recorded rationale and artifact hash. Unresolved cases remain
   unresolved, with explicit denominators; no AI output may substitute for human
   review. Role independence is asserted by verified review evidence, not merely
   by different strings in a JSON file.
6. Reviewers approve decision thresholds for agreement, macro/per-class F1,
   kappa, repeated-run agreement, sensitivity, parse/provider failure and intended
   downstream decision use before scoring held-out outputs. Keep all draft numeric
   fields null until this review. Freeze the final rubric/prompt/config hashes.
7. A later provider implementation must persist exact requests first, preserve
   raw responses and every retry, validate a closed verdict schema and record
   input/output tokens, p50/p95 latency, estimates and actual attributable cost.
   Pin question/output/request/raw-response hashes to every verdict, with score,
   reference support, unsupported-claim and temporal flags, diagnostic rationale,
   parse status and attempt count. Rationale is not source evidence.
8. Publish deterministic J0 separately from probabilistic J1. Optional J2 is a
   declared sensitivity comparison, never a silent ensemble or model fallback.
   Include confusion counts, per-class denominators, accuracy, macro F1, kappa,
   judge–J0 disagreement, repeated-run agreement and uncertainty. Low or unstable
   agreement yields ITERATE/DROP; do not lower thresholds after observing results.

The committed JSON is an unfilled review packet and is intentionally validated
against its exact draft shape. Actual review records are separate private
artifacts. Adopting an accepted calibration contract needs a later reviewed
change, real human evidence and canonical dependency reconciliation. No judge
implementation, CI judging, model selection or accepted human calibration is
claimed by this preparation.
