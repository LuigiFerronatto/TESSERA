"""Deterministic merge-authorization gate logic for TESSERA pull requests.

This module contains pure, unit-testable functions used by the
``tessera-merge-governor`` GitHub Actions workflow to decide whether a pull
request's *exact current head* satisfies deterministic merge-authorization
gates. AI semantic judgment (the ``tessera-pr-maintainer-audit`` workflow)
and deterministic authorization (this module) are deliberately separate:
this module never re-judges code quality, it only verifies that a
previously-recorded AI decision is still bound to the exact current head and
that deterministic repository checks are green.

The module purposefully does no network I/O itself. The calling workflow
fetches PR/comment/check-run state via the GitHub API/CLI and passes plain
data structures in, which keeps the authorization logic runnable and
testable without any GitHub credentials.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable, Optional

# Matches the machine-readable contract emitted by
# `.github/workflows/tessera-pr-maintainer-audit.md`:
#
#   ## Maintainer audit — KEEP | ITERATE | BLOCK
#   ...
#   Audited head: `<sha>`
_DECISION_RE = re.compile(
    r"##\s*Maintainer audit\s*[-\u2014]\s*(KEEP|ITERATE|BLOCK)", re.IGNORECASE
)
_AUDITED_HEAD_RE = re.compile(r"Audited head:\s*`([0-9a-fA-F]{7,40})`")

VALID_DECISIONS = ("KEEP", "ITERATE", "BLOCK")

# Engine-run conclusions that mean the audit workflow itself never produced a
# semantic judgment (quota exhaustion, auth failure, timeout, provider
# outage) as opposed to a completed run that chose not to comment. These are
# treated as `ENGINE_UNAVAILABLE`, a state distinct from `BLOCK`: "I could
# not analyze this" is never conflated with "I analyzed this and found a
# problem." A maintainer must never let engine unavailability quietly
# authorize a merge; the only escape hatch is an explicit, head-bound human
# override (see `parse_override_comment`).
ENGINE_FAILURE_CONCLUSIONS = ("failure", "timed_out", "cancelled", "action_required")

# Matches a maintainer-authored break-glass override, posted only when the
# maintainer-audit engine is confirmed unavailable (never as a substitute for
# a real ITERATE/BLOCK decision):
#
#   ## Maintainer override — KEEP
#
#   Audited head: `<sha>`
#   Reason: engine_unavailable (quota_exceeded)
_OVERRIDE_RE = re.compile(r"##\s*Maintainer override\s*[-\u2014]\s*(KEEP)", re.IGNORECASE)


@dataclass(frozen=True)
class AuditRecord:
    """A parsed maintainer-audit decision bound to a specific head SHA."""

    decision: str
    audited_head_sha: str
    comment_id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass(frozen=True)
class OverrideRecord:
    """A parsed human break-glass override, bound to a specific head SHA.

    The caller is responsible for only passing comments authored by an
    actual human maintainer (never a bot identity) into
    :func:`find_latest_override`, mirroring the same contract
    :func:`find_latest_audit` already documents for audit comments.
    """

    audited_head_sha: str
    comment_id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class GateResult:
    """Outcome of evaluating deterministic merge-authorization gates."""

    authorized: bool
    reasons: list[str] = field(default_factory=list)
    # Non-blocking informational notes (e.g. "authorized via human
    # break-glass override"). Never affects `authorized`; exists purely so
    # the calling workflow can surface *why* a gate that could have blocked
    # did not, for auditability.
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "authorized": self.authorized,
            "reasons": list(self.reasons),
            "notes": list(self.notes),
        }


def parse_audit_comment(body: str) -> Optional[AuditRecord]:
    """Parse one maintainer-audit comment body into an :class:`AuditRecord`.

    Returns ``None`` when the comment does not carry the expected
    machine-readable decision + audited-head-SHA contract. A comment that
    matches the decision heading but is missing an audited head SHA is
    treated as unparseable (``None``), because an audit result that cannot
    be bound to an exact head must never authorize a merge.
    """

    if not body:
        return None
    decision_match = _DECISION_RE.search(body)
    head_match = _AUDITED_HEAD_RE.search(body)
    if not decision_match or not head_match:
        return None
    decision = decision_match.group(1).upper()
    if decision not in VALID_DECISIONS:
        return None
    return AuditRecord(decision=decision, audited_head_sha=head_match.group(1))


def find_latest_audit(comments: Iterable[dict]) -> Optional[AuditRecord]:
    """Find the most recent parseable maintainer-audit comment.

    ``comments`` is a list of GitHub comment dicts with at least ``body``,
    ``id`` and ``created_at`` keys, in any order. Only comments authored by
    the maintainer-audit workflow's bot identity should be passed in by the
    caller; this function does not itself filter by author, since author
    identity/bot-detection depends on the calling context (workflow vs. test).
    """

    parsed: list[AuditRecord] = []
    for comment in comments:
        record = parse_audit_comment(comment.get("body", ""))
        if record is None:
            continue
        parsed.append(
            AuditRecord(
                decision=record.decision,
                audited_head_sha=record.audited_head_sha,
                comment_id=comment.get("id"),
                created_at=comment.get("created_at"),
            )
        )
    if not parsed:
        return None
    # created_at is ISO-8601 and sorts lexicographically in chronological order.
    parsed.sort(key=lambda r: (r.created_at or "", r.comment_id or 0))
    return parsed[-1]


def parse_override_comment(body: str) -> Optional[OverrideRecord]:
    """Parse one human break-glass override comment into an
    :class:`OverrideRecord`. Returns ``None`` when the comment does not
    carry the expected `## Maintainer override — KEEP` + audited-head-SHA
    contract. An override can only ever assert KEEP — there is no such thing
    as a human "override BLOCK", since a maintainer can always simply
    decline to merge through ordinary repository permissions.
    """

    if not body:
        return None
    override_match = _OVERRIDE_RE.search(body)
    head_match = _AUDITED_HEAD_RE.search(body)
    if not override_match or not head_match:
        return None
    return OverrideRecord(audited_head_sha=head_match.group(1))


def find_latest_override(comments: Iterable[dict]) -> Optional[OverrideRecord]:
    """Find the most recent parseable human override comment.

    The caller must only pass comments authored by a genuine human
    maintainer (never a bot identity) — this function does not itself
    filter by author, since author/bot detection depends on the calling
    context (workflow vs. test).
    """

    parsed: list[OverrideRecord] = []
    for comment in comments:
        record = parse_override_comment(comment.get("body", ""))
        if record is None:
            continue
        parsed.append(
            OverrideRecord(
                audited_head_sha=record.audited_head_sha,
                comment_id=comment.get("id"),
                created_at=comment.get("created_at"),
            )
        )
    if not parsed:
        return None
    parsed.sort(key=lambda r: (r.created_at or "", r.comment_id or 0))
    return parsed[-1]


def is_engine_unavailable(audit_workflow_conclusion: Optional[str]) -> bool:
    """Classify whether the maintainer-audit engine itself failed to
    produce a semantic judgment (quota exhaustion, auth failure, timeout,
    provider outage), as distinct from a completed run that legitimately
    chose not to comment. ``audit_workflow_conclusion`` is the GitHub
    Actions run conclusion (e.g. ``"success"``, ``"failure"``,
    ``"timed_out"``, ``"cancelled"``, ``None`` when unknown/not yet run) for
    the maintainer-audit workflow's most recent run on the current head.
    """

    return audit_workflow_conclusion in ENGINE_FAILURE_CONCLUSIONS


def evaluate_runtime_pr_gates(
    *,
    current_head_sha: str,
    is_draft: bool,
    mergeable_state: Optional[str],
    audit: Optional[AuditRecord],
    ci_success: bool,
    benchmark_success: bool,
    has_requested_changes: bool,
    has_unresolved_threads: bool,
    required_checks_satisfied: bool = True,
    engine_unavailable: bool = False,
    override: Optional[OverrideRecord] = None,
) -> GateResult:
    """Evaluate the merge-authorization gates for a runtime (non-lifecycle) PR.

    This is the anti-stale-head mechanism: a KEEP decision only authorizes a
    merge when ``audit.audited_head_sha == current_head_sha``. Any newer
    commit invalidates the previous audit and blocks authorization until a
    fresh KEEP is recorded against the new head.

    ``engine_unavailable`` and ``override`` implement the break-glass
    escape hatch for a confirmed maintainer-audit engine failure (quota,
    auth, timeout, provider outage — see :func:`is_engine_unavailable`).
    Absence of an audit record NEVER silently authorizes a merge on its own,
    even when the engine is unavailable: it only becomes non-blocking when a
    human has posted an explicit, head-bound
    ``## Maintainer override — KEEP`` comment (see
    :func:`parse_override_comment`). An override can never substitute for an
    actual ITERATE/BLOCK decision — it only applies when ``audit is None``
    and ``engine_unavailable`` is true.
    """

    reasons: list[str] = []
    notes: list[str] = []

    if is_draft:
        reasons.append("PR is a draft")
    if mergeable_state not in ("clean", None):
        # `mergeable_state` here reflects only GitHub's raw git-level merge
        # computation ("clean" == no conflicts against the base branch),
        # deliberately NOT the aggregate `mergeStateStatus`, which also
        # folds in every required status check (including this workflow's
        # own `tessera-merge-governor` check) and previously created a
        # self-referential loop: a run triggered by a fresh audit review
        # could see a stale/non-clean aggregate state from before it
        # published its own checks and reject an otherwise fully green
        # head. CI/Benchmark/audit freshness are each verified independently
        # below; this check exists only to catch actual merge conflicts.
        reasons.append(f"PR mergeable_state is '{mergeable_state}', not 'clean'")
    if mergeable_state is None:
        reasons.append("PR mergeable_state could not be determined")

    if audit is None:
        if engine_unavailable and override is not None and override.audited_head_sha == current_head_sha:
            notes.append(
                "maintainer-audit engine is unavailable; authorized via "
                "explicit human break-glass override bound to the current head"
            )
        elif engine_unavailable:
            reasons.append(
                "maintainer-audit engine is unavailable (quota/auth/timeout/outage) "
                "and no valid human override is bound to the current head"
            )
        else:
            reasons.append("no parseable maintainer-audit decision found")
    else:
        if audit.decision != "KEEP":
            reasons.append(f"latest maintainer-audit decision is {audit.decision}, not KEEP")
        if audit.audited_head_sha != current_head_sha:
            reasons.append(
                "stale audit: audited_head_sha "
                f"({audit.audited_head_sha}) does not match current head "
                f"({current_head_sha})"
            )

    if not ci_success:
        reasons.append("TESSERA CI is not green on the current head")
    if not benchmark_success:
        reasons.append("Benchmark Ledger is not green/appropriate on the current head")
    if has_requested_changes:
        reasons.append("a reviewer has requested changes")
    if has_unresolved_threads:
        reasons.append("unresolved review threads remain")
    if not required_checks_satisfied:
        reasons.append("required branch-protection checks are not satisfied")

    return GateResult(authorized=not reasons, reasons=reasons, notes=notes)


def evaluate_lifecycle_pr_gates(
    *,
    changed_files: Iterable[str],
    allowed_path_prefixes: Iterable[str],
    ci_success: bool,
    benchmark_success: bool,
    is_mergeable: bool,
    has_requested_changes: bool,
) -> GateResult:
    """Evaluate the (currently report-only, Stage A) gates for a lifecycle PR.

    Lifecycle/documentation PRs generated by the post-merge reconciler may
    only ever be considered for auto-merge (a future rollout stage) when
    every changed file stays under an explicitly allowed path prefix. This
    keeps a lifecycle PR from silently carrying runtime changes.
    """

    reasons: list[str] = []
    allowed = tuple(allowed_path_prefixes)
    offending = [f for f in changed_files if not any(f.startswith(p) for p in allowed)]
    if offending:
        reasons.append(f"changed files outside allowed lifecycle paths: {offending}")
    if not ci_success:
        reasons.append("TESSERA CI is not green")
    if not benchmark_success:
        reasons.append("Benchmark Ledger is not green/appropriate")
    if not is_mergeable:
        reasons.append("PR is not mergeable")
    if has_requested_changes:
        reasons.append("a reviewer has requested changes")

    return GateResult(authorized=not reasons, reasons=reasons)


def _main(argv: Optional[list[str]] = None) -> int:
    """CLI entrypoint used by the merge-governor workflow.

    Reads a JSON payload (see ``--payload``/``--payload-file``) describing
    the current PR, its comments, and check results, evaluates the runtime
    PR gates, prints a JSON result, and exits non-zero when not authorized so
    the workflow step can fail a required check truthfully.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-file", type=str, default=None)
    parser.add_argument("--payload", type=str, default=None)
    args = parser.parse_args(argv)

    if args.payload_file:
        with open(args.payload_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    elif args.payload:
        data = json.loads(args.payload)
    else:
        data = json.loads(sys.stdin.read())

    current_head_sha = data["current_head_sha"]
    audit = find_latest_audit(data.get("comments", []))

    # Only comments from a genuine human maintainer role can ever authorize
    # a break-glass override; bot-authored or outside-collaborator comments
    # must never count, even if they happen to match the override heading.
    trusted_roles = ("OWNER", "MEMBER", "COLLABORATOR")
    human_comments = [
        c
        for c in data.get("comments", [])
        if not c.get("author_is_bot") and c.get("author_association") in trusted_roles
    ]
    override = find_latest_override(human_comments)
    engine_unavailable = is_engine_unavailable(data.get("audit_workflow_conclusion"))

    result = evaluate_runtime_pr_gates(
        current_head_sha=current_head_sha,
        is_draft=data.get("is_draft", False),
        mergeable_state=data.get("mergeable_state"),
        audit=audit,
        ci_success=data.get("ci_success", False),
        benchmark_success=data.get("benchmark_success", False),
        has_requested_changes=data.get("has_requested_changes", False),
        has_unresolved_threads=data.get("has_unresolved_threads", False),
        required_checks_satisfied=data.get("required_checks_satisfied", True),
        engine_unavailable=engine_unavailable,
        override=override,
    )
    output = result.to_dict()
    # Exposed so the calling workflow can publish a dedicated
    # `TESSERA Maintainer Audit` check run (see audit_check_conclusion),
    # independent from the aggregate merge-governor conclusion. This lets
    # branch protection require the audit signal on its own, in addition to
    # the aggregate gate, per "defense in depth" (individual gates AND the
    # final aggregator are each independently required).
    output["audit"] = (
        None
        if audit is None
        else {
            "decision": audit.decision,
            "audited_head_sha": audit.audited_head_sha,
            "stale": audit.audited_head_sha != current_head_sha,
        }
    )
    output["engine_unavailable"] = engine_unavailable
    output["override"] = (
        None
        if override is None
        else {
            "audited_head_sha": override.audited_head_sha,
            "stale": override.audited_head_sha != current_head_sha,
        }
    )
    print(json.dumps(output))
    return 0 if result.authorized else 1


def audit_check_conclusion(audit: Optional[dict]) -> Optional[str]:
    """Map a parsed audit record (as emitted in the CLI JSON output) to a
    GitHub check-run conclusion for the dedicated `TESSERA Maintainer Audit`
    check.

    Returns ``None`` when no audit has been recorded yet for this PR at all,
    signalling the caller should leave the check unpublished (pending)
    rather than publish a false failure before the audit has had a chance to
    run. Returns ``"failure"`` for a stale audit (bound to a superseded
    head), for ``ITERATE``/``BLOCK`` decisions, and ``"success"`` only for a
    non-stale ``KEEP``.
    """

    if audit is None:
        return None
    if audit.get("stale"):
        return "failure"
    if audit.get("decision") == "KEEP":
        return "success"
    return "failure"


def audit_check_status(audit: Optional[dict], engine_unavailable: bool) -> Optional[dict]:
    """Decide what (if anything) to publish for the dedicated `TESSERA
    Maintainer Audit` check, distinguishing a genuine semantic decision
    (KEEP/ITERATE/BLOCK, via :func:`audit_check_conclusion`) from a
    confirmed engine failure (`ENGINE_UNAVAILABLE`) and from "hasn't run
    yet" (still pending).

    Returns ``None`` when the check should be left unpublished (no audit
    recorded yet, and no confirmed engine failure — genuinely still
    pending). Otherwise returns a dict with ``conclusion`` (``"success"`` or
    ``"failure"``) and ``status_label`` (``"KEEP"``/``"ITERATE"``/
    ``"BLOCK"``/``"ENGINE_UNAVAILABLE"``) for the caller to render.

    Note this reports the audit's own state honestly: even when a human
    break-glass override authorizes the *aggregate* merge-governor gate
    (see `evaluate_runtime_pr_gates`), this check is never faked to
    `success` — the audit genuinely did not run, and the override is a
    property of the aggregate governor decision, not of the audit itself.
    """

    conclusion = audit_check_conclusion(audit)
    if conclusion is not None:
        assert audit is not None
        status_label = "KEEP" if conclusion == "success" else audit.get("decision", "BLOCK")
        if audit.get("stale"):
            status_label = f"STALE_{audit.get('decision', 'KEEP')}"
        return {"conclusion": conclusion, "status_label": status_label}
    if engine_unavailable:
        return {"conclusion": "failure", "status_label": "ENGINE_UNAVAILABLE"}
    return None


if __name__ == "__main__":
    raise SystemExit(_main())
