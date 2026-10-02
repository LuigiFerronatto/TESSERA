"""Deterministic, exact-head merge-readiness checks; no AI review dependency.

GitHub branch protection remains the final authority. This module performs no
network I/O and never merges a PR or interprets AI comments as approval.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Iterable, Optional

from benchmarks.reporting.applicability import benchmark_contract_check_name, parse_applicability

REQUIRED_CI_JOBS = (
    "distribution (Python 3.9)",
    "distribution (Python 3.12)",
    "test (Python 3.9)",
    "test (Python 3.12)",
    "smoke",
    "sanity-eval",
)
BENCHMARK_JOB = "benchmark-reporting (offline)"

@dataclass
class GateResult:
    """Outcome of evaluating deterministic merge-authorization gates."""

    authorized: bool
    reasons: list[str] = field(default_factory=list)
    # Reserved for non-blocking deterministic diagnostics.
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "authorized": self.authorized,
            "reasons": list(self.reasons),
            "notes": list(self.notes),
        }


def check_is_green(rollup: Iterable[dict], name: str) -> bool:
    """Require an exact-name, completed success; absent/pending/skipped fail closed."""
    matches = [check for check in rollup if (check.get("name") or check.get("context")) == name]
    return bool(matches) and all(
        str(check.get("conclusion") or check.get("state") or "").upper() == "SUCCESS"
        for check in matches
    )


def has_current_human_approval(pr: dict, review_pages: list[list[dict]]) -> bool:
    """Require GitHub aggregate approval plus a current, trusted human verdict.

    REST review pages are chronological, but sort explicitly by submission and ID.
    A later dismissal/requested-changes supersedes the same reviewer's approval;
    a COMMENTED review does not revoke a prior approval. Stale approvals never count.
    """
    if pr.get("reviewDecision") != "APPROVED" or not review_pages:
        return False
    latest = {}
    reviews = [review for page in review_pages for review in page]
    for review in sorted(reviews, key=lambda value: (value.get("submitted_at") or "", value.get("id") or 0)):
        user = review.get("user") or {}
        login = user.get("login")
        state = review.get("state")
        if not login or state not in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            continue
        latest[login] = review
    return any(
        review.get("state") == "APPROVED"
        and review.get("commit_id") == pr.get("headRefOid")
        and (review.get("user") or {}).get("type") == "User"
        and not login.lower().endswith("[bot]")
        and login != (pr.get("author") or {}).get("login")
        and review.get("author_association") in {"OWNER", "MEMBER", "COLLABORATOR"}
        for login, review in latest.items()
    )


def payload_from_pr(pr: dict, thread_pages: list[dict], review_pages: list[list[dict]]) -> dict:
    """Build gates from the current PR and every page of GraphQL review threads.

    Missing/partial thread data is an error, never proof that no threads exist.
    The caller must use gh api graphql --paginate --slurp and stop on API errors.
    """
    if not thread_pages:
        raise ValueError("review-thread evidence is missing")
    threads = []
    for index, page in enumerate(thread_pages):
        if page.get("errors"):
            raise ValueError("review-thread query returned errors")
        connection = page["data"]["repository"]["pullRequest"]["reviewThreads"]
        nodes = connection["nodes"]
        if not isinstance(nodes, list) or any(type(n.get("isResolved")) is not bool for n in nodes):
            raise ValueError("review-thread evidence is malformed")
        if index == len(thread_pages) - 1 and connection["pageInfo"]["hasNextPage"] is not False:
            raise ValueError("review-thread evidence is incomplete")
        threads.extend(nodes)
    rollup = pr.get("statusCheckRollup") or []
    try:
        applicability = parse_applicability(pr.get("body"))["applicability"]
        contract_check = benchmark_contract_check_name(pr.get("body"))
    except ValueError:
        applicability = None
        contract_check = None
    # The terminal contract check certifies reporting and applicable dev-50
    # success in one workflow run for this exact metadata. Old name-only green
    # checks must not bridge a body edit while new jobs have not registered yet.
    benchmark_success = (
        contract_check is not None
        and check_is_green(rollup, BENCHMARK_JOB)
        and check_is_green(rollup, contract_check)
    )
    if applicability == "REQUIRED":
        benchmark_success = benchmark_success and check_is_green(rollup, "longmemeval-v1-dev-50")
    return {
        "current_head_sha": pr.get("headRefOid"),
        "is_draft": pr.get("isDraft") is not False,
        "mergeable_state": {"MERGEABLE": "clean", "CONFLICTING": "conflicting"}.get(pr.get("mergeable")),
        "ci_success": all(check_is_green(rollup, name) for name in REQUIRED_CI_JOBS),
        "benchmark_success": benchmark_success,
        "has_required_approval": has_current_human_approval(pr, review_pages),
        "has_requested_changes": pr.get("reviewDecision") == "CHANGES_REQUESTED",
        "has_unresolved_threads": any(not thread["isResolved"] for thread in threads),
    }


def recheck_benchmark_contract(result: GateResult, evaluated_body: str, current_body: str) -> GateResult:
    """Fail closed if metadata changed between evidence gathering and publish."""
    try:
        unchanged = benchmark_contract_check_name(evaluated_body) == benchmark_contract_check_name(current_body)
    except ValueError:
        unchanged = False
    if unchanged:
        return result
    return GateResult(
        authorized=False,
        reasons=[*result.reasons, "benchmark contract changed or is invalid at publication; fresh evidence is required"],
        notes=list(result.notes),
    )


def evaluate_runtime_pr_gates(
    *,
    current_head_sha: str,
    is_draft: bool,
    mergeable_state: Optional[str],
    ci_success: bool,
    benchmark_success: bool,
    has_required_approval: bool,
    has_requested_changes: bool,
    has_unresolved_threads: bool,
    required_checks_satisfied: bool = True,
) -> GateResult:
    """Require deterministic evidence and human review for the current PR head.

    No AI audit, provider status, label or break-glass comment participates.
    GitHub must still enforce strict required checks and review requirements.
    """
    reasons = []
    if not current_head_sha:
        reasons.append("current PR head could not be determined")
    if is_draft:
        reasons.append("PR is a draft")
    if mergeable_state is None:
        reasons.append("PR mergeable_state could not be determined")
    elif mergeable_state != "clean":
        reasons.append(f"PR mergeable_state is '{mergeable_state}', not 'clean'")
    if not ci_success:
        reasons.append("TESSERA CI is not green on the current head")
    if not benchmark_success:
        reasons.append("Benchmark Ledger is not green/appropriate on the current head")
    if not has_required_approval:
        reasons.append("required human review approval is missing")
    if has_requested_changes:
        reasons.append("a reviewer has requested changes")
    if has_unresolved_threads:
        reasons.append("unresolved review threads remain")
    if not required_checks_satisfied:
        reasons.append("required branch-protection checks are not satisfied")
    return GateResult(authorized=not reasons, reasons=reasons)


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-file", type=str, default=None)
    parser.add_argument("--payload", type=str, default=None)
    args = parser.parse_args(argv)
    if args.payload_file:
        with open(args.payload_file, encoding="utf-8") as handle:
            data = json.load(handle)
    elif args.payload:
        data = json.loads(args.payload)
    else:
        data = json.loads(sys.stdin.read())
    result = evaluate_runtime_pr_gates(
        current_head_sha=data.get("current_head_sha", ""),
        is_draft=data.get("is_draft", True),
        mergeable_state=data.get("mergeable_state"),
        ci_success=data.get("ci_success", False),
        benchmark_success=data.get("benchmark_success", False),
        has_required_approval=data.get("has_required_approval", False),
        has_requested_changes=data.get("has_requested_changes", False),
        has_unresolved_threads=data.get("has_unresolved_threads", True),
        required_checks_satisfied=data.get("required_checks_satisfied", True),
    )
    print(json.dumps(result.to_dict()))
    return 0 if result.authorized else 1


if __name__ == "__main__":
    raise SystemExit(_main())
