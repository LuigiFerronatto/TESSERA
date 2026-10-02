"""The retired AI audit cannot influence deterministic PR readiness."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from governance import merge_governor as mg

ROOT = Path(__file__).resolve().parents[1]


def green_payload():
    return dict(current_head_sha='abc1234', is_draft=False,
                mergeable_state='clean', ci_success=True, benchmark_success=True,
                has_required_approval=True, has_requested_changes=False,
                has_unresolved_threads=False)


def green_pr():
    pr = dict(headRefOid='abc1234', isDraft=False, mergeable='MERGEABLE',
                reviewDecision='APPROVED', author={'login': 'author'},
                body='Benchmark applicability: NOT_APPLICABLE\nBenchmark rationale: governance only', statusCheckRollup=[
                    dict(name=n, conclusion='SUCCESS')
                    for n in (*mg.REQUIRED_CI_JOBS, mg.BENCHMARK_JOB)])
    pr['statusCheckRollup'].append(dict(name=mg.benchmark_contract_check_name(pr['body']), conclusion='SUCCESS'))
    return pr


def human_review(**changes):
    review = dict(id=1, submitted_at='2026-10-02T00:00:00Z', state='APPROVED',
                  commit_id='abc1234', user={'login': 'reviewer', 'type': 'User'},
                  author_association='COLLABORATOR')
    review.update(changes)
    return review


def payload_from_pr(pr, threads, reviews=None):
    return mg.payload_from_pr(pr, threads, [[human_review()]] if reviews is None else reviews)


def thread_page(resolved=(), more=False):
    return {'data': {'repository': {'pullRequest': {'reviewThreads': {
        'nodes': [{'isResolved': value} for value in resolved],
        'pageInfo': {'hasNextPage': more, 'endCursor': 'cursor'},
    }}}}}


def test_ready_without_ai_audit():
    assert mg.evaluate_runtime_pr_gates(**green_payload()).authorized


@pytest.mark.parametrize('field,value,reason', [
    ('current_head_sha', '', 'head could not'),
    ('is_draft', True, 'draft'),
    ('mergeable_state', 'conflicting', 'mergeable_state'),
    ('mergeable_state', None, 'could not be determined'),
    ('ci_success', False, 'CI is not green'),
    ('benchmark_success', False, 'Benchmark Ledger'),
    ('has_required_approval', False, 'human review approval'),
    ('has_requested_changes', True, 'requested changes'),
    ('has_unresolved_threads', True, 'unresolved review threads'),
    ('required_checks_satisfied', False, 'branch-protection'),
])
def test_each_deterministic_gate_fails_closed(field, value, reason):
    payload = green_payload()
    payload[field] = value
    result = mg.evaluate_runtime_pr_gates(**payload)
    assert not result.authorized
    assert any(reason in r for r in result.reasons)


@pytest.mark.parametrize('state', ['', 'FAILURE', 'PENDING', 'CANCELLED', 'SKIPPED', 'NEUTRAL', 'TIMED_OUT'])
def test_required_job_never_passes_on_non_success(state):
    pr = green_pr()
    pr['statusCheckRollup'][0]['conclusion'] = state
    assert not payload_from_pr(pr, [thread_page()])['ci_success']


def test_exact_job_names_and_all_matching_jobs_must_pass():
    pr = green_pr()
    pr['statusCheckRollup'][0]['name'] += ' unrelated'
    assert not payload_from_pr(pr, [thread_page()])['ci_success']
    pr = green_pr()
    pr['statusCheckRollup'].append(dict(name=mg.REQUIRED_CI_JOBS[0], conclusion='FAILURE'))
    assert not payload_from_pr(pr, [thread_page()])['ci_success']
    assert not mg.check_is_green([], mg.BENCHMARK_JOB)


@pytest.mark.parametrize('decision', [None, '', 'REVIEW_REQUIRED', 'CHANGES_REQUESTED'])
def test_required_human_review_is_never_inferred(decision):
    pr = green_pr()
    pr['reviewDecision'] = decision
    assert not payload_from_pr(pr, [thread_page()])['has_required_approval']


def test_unresolved_thread_on_later_page_blocks():
    payload = payload_from_pr(green_pr(), [thread_page([True] * 100, True), thread_page([False])])
    assert payload['has_unresolved_threads']
    assert not mg.evaluate_runtime_pr_gates(**payload).authorized


@pytest.mark.parametrize('pages', [[], [{}], [{'errors': ['API error']}], [thread_page([], True)]])
def test_missing_or_incomplete_thread_evidence_never_passes(pages):
    with pytest.raises((ValueError, KeyError, TypeError)):
        payload_from_pr(green_pr(), pages)


def test_zero_resolved_threads_and_successful_checks_are_valid():
    payload = payload_from_pr(green_pr(), [thread_page()])
    assert mg.evaluate_runtime_pr_gates(**payload).authorized


@pytest.mark.parametrize('ai_decision', ['KEEP', 'ITERATE', 'BLOCK'])
def test_cli_ignores_old_ai_comments_and_engine_status(ai_decision):
    payload = green_payload()
    payload.update(comments=[{'body': f'## Maintainer audit — {ai_decision}\nAudited head: `deadbee`'}],
                   audit_workflow_conclusion='failure')
    result = subprocess.run([sys.executable, '-m', 'governance.merge_governor', '--payload', json.dumps(payload)],
                            cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'authorized': True, 'reasons': [], 'notes': []}


def test_cli_empty_payload_fails_closed():
    result = subprocess.run([sys.executable, '-m', 'governance.merge_governor', '--payload', '{}'],
                            cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 1
    assert not json.loads(result.stdout)['authorized']


def test_retired_ai_reviewer_is_not_a_ci_workflow():
    workflows = ROOT / '.github/workflows'
    assert not (workflows / 'tessera-pr-maintainer-audit.md').exists()
    assert not (workflows / 'tessera-pr-maintainer-audit.lock.yml').exists()
    source = (workflows / 'tessera-merge-governor.yml').read_text()
    assert 'name="TESSERA Maintainer Audit"' not in source
    assert 'audit_runs.json' not in source
    assert 'comments.json' not in source
    assert 'gh api graphql --paginate --slurp' in source
    assert '"$HEAD_SHA" == "$current_head"' in source
    assert '"$COMPLETED_HEAD" != "$head_sha"' in source
    doc = yaml.safe_load(source)
    on = doc.get('on', doc.get(True))
    assert set(on['workflow_run']['workflows']) == {'TESSERA CI', 'TESSERA Benchmark Ledger'}
    assert on['workflow_run']['types'] == ['completed']
    assert doc['permissions'] == {'contents': 'read', 'pull-requests': 'read', 'checks': 'write'}


def test_fixer_requires_selected_human_findings():
    source = (ROOT / '.github/workflows/tessera-pr-fixer.md').read_text()
    assert 'findings are missing or ambiguous' in source
    assert 'without\n   pushing changes' in source
    assert 'old AI audit comment' in source
    assert 'requires human review and deterministic CI' in source


@pytest.mark.parametrize('state', ['', 'FAILURE', 'PENDING', 'SKIPPED', 'CANCELLED'])
def test_required_benchmark_needs_dev50_success(state):
    pr = green_pr()
    pr['body'] = 'Benchmark applicability: REQUIRED\nBenchmark issue: #194'
    pr['statusCheckRollup'].append(dict(name=mg.benchmark_contract_check_name(pr['body']), conclusion='SUCCESS'))
    if state:
        pr['statusCheckRollup'].append(dict(name='longmemeval-v1-dev-50', conclusion=state))
    assert not payload_from_pr(pr, [thread_page()])['benchmark_success']
    pr['statusCheckRollup'] = [c for c in pr['statusCheckRollup'] if c['name'] != 'longmemeval-v1-dev-50']
    pr['statusCheckRollup'].append(dict(name='longmemeval-v1-dev-50', conclusion='SUCCESS'))
    assert payload_from_pr(pr, [thread_page()])['benchmark_success']


@pytest.mark.parametrize('body', [None, '', 'Benchmark applicability: REQUIRED',
    'Benchmark applicability: SMOKE_ONLY', 'Benchmark applicability: nonsense',
    'Benchmark applicability: REQUIRED\nBenchmark issue: #194\nBenchmark applicability: NOT_APPLICABLE'])
def test_missing_malformed_or_ambiguous_applicability_blocks(body):
    pr = green_pr()
    pr['body'] = body
    assert not payload_from_pr(pr, [thread_page()])['benchmark_success']


@pytest.mark.parametrize('review', [
    human_review(user={'login': 'copilot[bot]', 'type': 'Bot'}),
    human_review(user={'login': 'copilot[bot]', 'type': 'User'}),
    human_review(user={'login': 'author', 'type': 'User'}),
    human_review(commit_id='oldhead'),
    human_review(state='DISMISSED'),
    human_review(state='CHANGES_REQUESTED'),
    human_review(author_association='CONTRIBUTOR'),
])
def test_bot_stale_dismissed_or_untrusted_approval_does_not_count(review):
    assert not payload_from_pr(green_pr(), [thread_page()], [[review]])['has_required_approval']


def test_paginated_latest_human_verdict_and_comment_semantics():
    approval = human_review()
    revoked = human_review(id=2, state='CHANGES_REQUESTED', submitted_at='2026-10-02T00:01:00Z')
    assert not payload_from_pr(green_pr(), [thread_page()], [[approval], [revoked]])['has_required_approval']
    commented = human_review(id=3, state='COMMENTED', submitted_at='2026-10-02T00:02:00Z')
    assert payload_from_pr(green_pr(), [thread_page()], [[approval], [commented]])['has_required_approval']
    assert not payload_from_pr(green_pr(), [thread_page()], [])['has_required_approval']


@pytest.mark.parametrize('body', [
    'Benchmark applicability: REQUIRED\nBenchmark issue: #194',
    'Benchmark applicability: SMOKE_ONLY\nBenchmark rationale: governance only',
    'Benchmark applicability: NOT_APPLICABLE\nBenchmark rationale: changed rationale',
    'Benchmark applicability: NOT_APPLICABLE\nBenchmark rationale: governance only\nBenchmark issue: #195',
])
def test_body_edit_cannot_reuse_old_green_before_new_jobs_register(body):
    pr = green_pr()
    # Even an older successful dev-50 job on this same SHA is insufficient.
    pr['statusCheckRollup'].append(dict(name='longmemeval-v1-dev-50', conclusion='SUCCESS'))
    pr['body'] = body
    assert not payload_from_pr(pr, [thread_page()])['benchmark_success']
    pr['statusCheckRollup'].append(dict(name=mg.benchmark_contract_check_name(body), conclusion='SUCCESS'))
    assert payload_from_pr(pr, [thread_page()])['benchmark_success']


@pytest.mark.parametrize('state', ['', 'PENDING', 'FAILURE', 'CANCELLED', 'SKIPPED', 'NEUTRAL', 'TIMED_OUT'])
def test_pending_or_failed_contract_check_blocks_even_with_old_success(state):
    pr = green_pr()
    pr['statusCheckRollup'].append(dict(name=mg.benchmark_contract_check_name(pr['body']), conclusion=state))
    assert not payload_from_pr(pr, [thread_page()])['benchmark_success']


def test_completed_same_contract_evidence_survives_unrelated_prose_edits():
    pr = green_pr()
    pr['body'] += '\n\nA corrected explanation unrelated to benchmark metadata.'
    assert payload_from_pr(pr, [thread_page()])['benchmark_success']


def test_ignored_title_edit_skips_do_not_replace_authoritative_evidence():
    pr = green_pr()
    pr['statusCheckRollup'].extend([
        dict(name='benchmark-reporting (ignored edit)', conclusion='SKIPPED'),
        dict(name='longmemeval-v1-dev-50 (ignored edit)', conclusion='SKIPPED'),
        dict(name='benchmark-contract (invalid)', conclusion='SKIPPED'),
    ])
    assert payload_from_pr(pr, [thread_page()])['benchmark_success']


def test_required_issue_change_needs_new_terminal_evidence():
    pr = green_pr()
    pr['body'] = 'Benchmark applicability: REQUIRED\nBenchmark issue: #194'
    pr['statusCheckRollup'].extend([
        dict(name='longmemeval-v1-dev-50', conclusion='SUCCESS'),
        dict(name=mg.benchmark_contract_check_name(pr['body']), conclusion='SUCCESS'),
    ])
    assert payload_from_pr(pr, [thread_page()])['benchmark_success']
    pr['body'] = pr['body'].replace('#194', '#195')
    assert not payload_from_pr(pr, [thread_page()])['benchmark_success']


def test_legacy_checks_without_contract_evidence_fail_closed():
    pr = green_pr()
    pr['statusCheckRollup'].pop()
    assert not payload_from_pr(pr, [thread_page()])['benchmark_success']


@pytest.mark.parametrize('current_body', [None, '', 'Benchmark applicability: REQUIRED\nBenchmark issue: #194'])
def test_contract_edit_between_gather_and_publish_fails_closed(current_body):
    result = mg.recheck_benchmark_contract(mg.GateResult(True), green_pr()['body'], current_body)
    assert not result.authorized
    assert any('publication' in reason for reason in result.reasons)


def test_publication_contract_recheck_preserves_other_gate_failures_and_ignores_prose():
    original = green_pr()['body']
    blocked = mg.GateResult(False, ['required human review approval is missing'])
    assert mg.recheck_benchmark_contract(blocked, original, original + '\nClarification') is blocked
    ready = mg.GateResult(True)
    assert mg.recheck_benchmark_contract(ready, original, original + '\nClarification') is ready


def test_body_edit_triggers_and_ignored_edit_concurrency_are_explicit():
    for filename in ('benchmark.yml', 'tessera-merge-governor.yml'):
        text = (ROOT / '.github/workflows' / filename).read_text()
        doc = yaml.load(text, Loader=yaml.BaseLoader)
        assert 'edited' in doc['on']['pull_request']['types']
        job = doc['jobs']['benchmark-reporting' if filename == 'benchmark.yml' else 'evaluate']
        assert "github.event.action != 'edited' || github.event.changes.body != null" in job['if']
        assert "github.event.changes.body == null && github.run_id" in doc['concurrency']['group']
    governor = (ROOT / '.github/workflows/tessera-merge-governor.yml').read_text()
    assert "github.event.inputs.pr_number || github.run_id" in governor
    assert "|| 'manual'" not in governor
    assert '--json headRefOid,body > current_pr.json' in governor
    assert 'recheck_benchmark_contract' in governor
