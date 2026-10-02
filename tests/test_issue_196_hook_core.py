"""Offline lifecycle semantics, provider snapshots and negative safety contracts."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tessera.hook_adapters import FrozenHookAdapter, Invocation, parse_provider_input
from tessera.lifecycle import (Capabilities, CapturePolicy, ContextCatalog, ContextSection,
                               EventType, ExecutionPolicy, HookCore, HookResult, Identities,
                               LifecycleError, LifecycleEvent, ProjectBinding, RunBuffer,
                               canonical_json, resolve_binding)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/hooks/providers-v1.json").read_text())
SCOPE = ProjectBinding("fixture-project", "/fixture/project")
STAMP = "2026-10-02T00:00:00Z"


def event(kind=EventType.INPUT, *, sequence=0, payload=None, **kwargs):
    values = dict(event_id="evt-" + str(sequence), canonical_type=kind,
                  identities=Identities("session-1", "run-main", "turn-1", "task-1"),
                  scope=SCOPE, sequence=sequence, occurred_at=STAMP, runtime="generic",
                  provider_event="Input", adapter_version="v1",
                  payload_json=canonical_json(payload or {"text": "Check the release procedure."}),
                  capabilities=Capabilities(can_inject_context=True))
    values.update(kwargs)
    return LifecycleEvent(**values)


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["runtime"] + ":" + c["event"] + ":" + c["payload"].get("source", ""))
def test_frozen_provider_fixture(case):
    adapter = FrozenHookAdapter(case["runtime"])
    invocation = Invocation("fixture-1", 1, STAMP, "run-main", "turn-1", **case["invocation"])
    result = adapter.normalize(case["event"], case["payload"], invocation, SCOPE)
    assert result.events
    assert result == adapter.normalize(case["event"], case["payload"], invocation, SCOPE)
    for index, normalized in enumerate(result.events):
        assert normalized.schema_version == 1
        assert normalized.sequence == 4 + index
        assert normalized.scope == SCOPE
        assert normalized.identities.runtime_session_id == case["runtime"] + "-session"
        assert "transcript_path" not in normalized.payload_json
        assert "compact_summary" not in normalized.payload_json
        assert LifecycleEvent.from_dict(normalized.to_dict()) == normalized
    if "ubagent" in case["event"]:
        assert result.events[0].identities.parent_run_id == "run-main"
        assert result.events[0].identities.parent_turn_id == "turn-1"
        assert result.events[0].identities.tessera_run_id == "run-child"
    if case["payload"].get("source") in ("resume", "compact"):
        assert result.events[0].canonical_type == EventType.SESSION_RESUMED


def test_provider_fixture_covers_every_profile_event():
    for runtime in FIXTURE["sources"]:
        frozen = {case["event"] for case in FIXTURE["cases"] if case["runtime"] == runtime}
        assert frozen == set(FrozenHookAdapter(runtime).describe()["events"])


@pytest.mark.parametrize("raw", [b'[]', b'{"x":NaN}', b'{"x":1,"x":2}', b'\xff', b'{broken', b'{}{}'])
def test_strict_provider_json_rejects_nonobjects_duplicates_nonfinite_and_noise(raw):
    with pytest.raises(LifecycleError):
        parse_provider_input(raw)


def test_input_size_and_schema_fail_before_capture():
    with pytest.raises(LifecycleError, match="too_large"):
        parse_provider_input(b" " * 131073)
    with pytest.raises(LifecycleError, match="unknown_payload_field"):
        event(payload={"provider_raw": {"password": "never"}})
    with pytest.raises(LifecycleError, match="unsupported_event_schema"):
        event(schema_version=True)
    with pytest.raises(LifecycleError, match="invalid_timestamp"):
        event(occurred_at="2026-10-02")
    with pytest.raises(LifecycleError, match="invalid_capabilities"):
        Capabilities(can_block="false")


def test_explicit_project_resolution_no_git_language_or_home_scan(tmp_path, monkeypatch):
    root = tmp_path / "arbitrary-documents"
    nested = root / "nested"
    nested.mkdir(parents=True)
    binding = ProjectBinding("notes", str(root))
    other = ProjectBinding("other", str(tmp_path / "other"))
    glob = ProjectBinding("named-global", global_scope=True)
    monkeypatch.setenv("TESSERA_STORAGE_DIR", str(tmp_path / "unrelated"))
    assert resolve_binding([binding, other, glob], cwd=str(nested)) == binding
    assert resolve_binding([binding], cwd=str(nested), provider_root=str(root)) == binding
    assert resolve_binding([binding, glob], cwd=str(tmp_path)) is None
    assert resolve_binding([binding, glob], cwd=str(tmp_path), global_scope="named-global") == glob
    assert resolve_binding([binding, glob], cwd=str(nested), provider_root=str(tmp_path / "unknown")) is None
    with pytest.raises(LifecycleError, match="explicit_scope_mismatch"):
        resolve_binding([binding, other], cwd=str(nested), explicit_scope="other")
    with pytest.raises(LifecycleError, match="absolute"):
        resolve_binding([binding], cwd="relative")
    assert not (tmp_path / "unrelated").exists()
    assert sorted(p.name for p in root.iterdir()) == ["nested"]


def test_scope_escape_and_ambiguous_bindings(tmp_path):
    root, outside = tmp_path / "project", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    binding = ProjectBinding("one", str(root))
    assert resolve_binding([binding], cwd=str(root / "escape")) is None
    with pytest.raises(LifecycleError, match="ambiguous_scope"):
        resolve_binding([binding, ProjectBinding("two", str(root))], cwd=str(root))


def test_unknown_runtime_event_is_not_success():
    adapter = FrozenHookAdapter("gemini")
    assert adapter.normalize("SubagentStart", {}, Invocation("d", 0, STAMP, "run-main"), SCOPE).diagnostics == ("unsupported_provider_event",)
    wire = adapter.render_response(HookResult("ok"), "SubagentStart")
    assert wire.exit_code == 1 and json.loads(wire.stdout) == {}


def test_missing_turn_does_not_use_session_as_turn():
    case = next(c for c in FIXTURE["cases"] if c["runtime"] == "gemini" and c["event"] == "BeforeAgent")
    with pytest.raises(LifecycleError, match="turn_identity_required"):
        FrozenHookAdapter("gemini").normalize(case["event"], case["payload"], Invocation("d", 0, STAMP, "run-main"), SCOPE)
    codex = next(c for c in FIXTURE["cases"] if c["runtime"] == "codex" and c["event"] == "Stop")
    with pytest.raises(LifecycleError, match="turn_identity_mismatch"):
        FrozenHookAdapter("codex").normalize(codex["event"], codex["payload"], Invocation("d", 0, STAMP, "run-main", "wrong"), SCOPE)


def test_missing_child_identity_not_invented_from_name():
    case = next(c for c in FIXTURE["cases"] if c["runtime"] == "copilot" and c["event"] == "subagentStart")
    with pytest.raises(LifecycleError, match="subagent_lineage_required"):
        FrozenHookAdapter("copilot").normalize(case["event"], case["payload"], Invocation("d", 0, STAMP, "run-main", "turn-1", child_run_id="child"), SCOPE)


def test_codex_opaque_tool_output_does_not_claim_success_or_parse_text():
    case = next(c for c in FIXTURE["cases"] if c["runtime"] == "codex" and c["event"] == "PostToolUse")
    payload = dict(case["payload"], tool_name="Bash", tool_response="Exit code: 1. command failed")
    result = FrozenHookAdapter("codex").normalize("PostToolUse", payload, Invocation("d", 0, STAMP, "run-main", "turn-1"), SCOPE)
    assert result.events[0].payload["outcome"] == "unknown"
    assert result.diagnostics == ("tool_outcome_unknown",)


def test_journal_idempotency_collision_order_and_identity():
    buffer = RunBuffer("run-main", SCOPE, capture_policy=CapturePolicy(include_content=True))
    first = event(sequence=2)
    assert buffer.append(first) == "appended"
    assert buffer.append(first) == "duplicate"
    with pytest.raises(LifecycleError, match="event_id_collision"):
        buffer.append(replace(first, payload_json=canonical_json({"text": "Different submission"})))
    with pytest.raises(LifecycleError, match="out_of_order"):
        buffer.append(event(sequence=1))
    with pytest.raises(LifecycleError, match="session_identity_mismatch"):
        buffer.append(event(sequence=3, identities=Identities("other-session", "run-main", "turn-1")))
    with pytest.raises(LifecycleError, match="run_scope_mismatch"):
        buffer.append(event(sequence=3, scope=ProjectBinding("other", "/fixture/other")))
    assert buffer.events == (first,)


def test_default_capture_omits_content_before_journal_checkpoint_and_restore():
    buffer = RunBuffer("run-main", SCOPE)
    buffer.append(event(payload={"text": "arbitrary private string", "arguments": {"password": "do-not-store"}}))
    serialized = buffer.checkpoint()
    assert b"arbitrary private string" not in serialized and b"do-not-store" not in serialized
    restored = RunBuffer.restore(serialized)
    assert restored.checkpoint() == serialized
    copied = restored.events[0].payload
    copied["text"] = "mutated"
    assert restored.checkpoint() == serialized
    with pytest.raises(LifecycleError):
        RunBuffer.restore(serialized[:-1])
    with pytest.raises(LifecycleError, match="too_large"):
        RunBuffer.restore(b" " * 6000, max_bytes=1024)


def test_opt_in_redaction_scrubs_nested_credentials_before_any_capture():
    buffer = RunBuffer("run-main", SCOPE, capture_policy=CapturePolicy(include_content=True))
    buffer.append(event(payload={"text": "Bearer abcdef123456 and api_key=fixture-value",
                                "arguments": {"password": "fixture-pass", "nested": [{"authorization": "private"}]},
                                "output": "-----BEGIN PRIVATE KEY----- never retain"}))
    serialized = buffer.checkpoint().decode()
    for secret in ("abcdef123456", "fixture-value", "fixture-pass", '"private"', "never retain"):
        assert secret not in serialized
    assert "[redacted]" in serialized


def test_capture_failure_and_budget_never_block_or_claim_saved():
    core = HookCore(RunBuffer("run-main", SCOPE, max_events=1))
    assert core.receive(event()).persisted is False
    result = core.receive(event(sequence=1))
    assert result.status == "degraded" and result.diagnostics == ("capture_budget_exceeded",)
    assert len(core.buffer.events) == 1
    wire = FrozenHookAdapter("claude").render_response(result, "Stop")
    assert wire.exit_code == 1 and json.loads(wire.stdout) == {} and "persist" not in wire.stdout
    strict = HookCore(core.buffer, policy=ExecutionPolicy(capture_failure="raise"))
    with pytest.raises(LifecycleError, match="capture_budget_exceeded"):
        strict.receive(event(sequence=2))


def test_redaction_failure_prevents_capture():
    class BrokenRedactor(CapturePolicy):
        def redact(self, value):
            raise LifecycleError("redaction_unavailable")
    core = HookCore(RunBuffer("run-main", SCOPE, capture_policy=BrokenRedactor()))
    assert core.receive(event()).status == "degraded"
    assert core.buffer.events == () and core.buffer._seen == {}


def test_stop_session_task_and_episode_are_not_equated(tmp_path):
    buffer = RunBuffer("run-main", SCOPE)
    core = HookCore(buffer)
    result = core.receive(event(EventType.TURN_COMPLETED))
    assert result.learning_boundary == "turn_completed"
    assert result.persisted is False and "WRITE_AFTER_LEARNING" not in result.milestones
    assert buffer.state == "quiescent"
    core.receive(event(sequence=1, identities=Identities("session-1", "run-main", "turn-2", "task-1")))
    assert buffer.state == "open"
    assert buffer.events[-1].identities.tessera_episode_id is None
    core.receive(event(EventType.SESSION_ENDED, sequence=2))
    assert buffer.state == "closed"
    assert core.receive(event(sequence=3)).diagnostics == ("run_closed",)
    assert list(tmp_path.iterdir()) == []


def test_child_parent_echo_uses_explicit_origin_and_preserves_observations():
    buffer = RunBuffer("run-main", SCOPE, capture_policy=CapturePolicy(include_content=True))
    child_ids = Identities("session-1", "run-child", "turn-1", subagent_id="child", parent_run_id="run-main", parent_turn_id="turn-1")
    child = event(EventType.SUBAGENT_COMPLETED, payload={"text": "Shared result", "evidence_origin_id": "origin-child"}, identities=child_ids)
    parent = event(EventType.TOOL_COMPLETED, sequence=1, payload={"output": "Shared result", "evidence_origin_id": "origin-child"})
    buffer.append(child)
    buffer.append(parent)
    buffer.append(event(sequence=2, payload={"text": "Shared result"}))
    groups = buffer.episode_inputs()
    assert len(groups) == 2  # equal text alone cannot collapse unrelated evidence
    assert groups[0]["event_ids"] == [child.event_id, parent.event_id]
    assert len(groups[0]["lineage"]) == 2
    assert groups[0]["lineage"][0]["parent_run_id"] == "run-main"


def test_context_budget_reports_exact_omissions_and_pointer_degradation():
    catalog = ContextCatalog(SCOPE.scope_id, (ContextSection("keep", "Hello"),
                  ContextSection("oversize", "多" * 100, "evidence/one"), ContextSection("missing", "X" * 100)))
    core = HookCore(RunBuffer("run-main", SCOPE), catalog=catalog,
                    policy=ExecutionPolicy(max_context_bytes=30, max_context_token_bound=30))
    result = core.receive(event(EventType.BEFORE_REASONING))
    assert result.context == "Hello\n\nEvidence: evidence/one"
    assert result.omitted_sections == ("oversize", "missing")
    assert result.pointer_sections == ("oversize",)
    assert result.context_bytes == len(result.context.encode()) <= 30
    assert result.context_token_upper_bound == result.context_bytes
    assert result.status == "degraded"


def test_context_deadline_drops_late_packet_without_background_work():
    ticks = iter((0.0, 0.1, 0.11))
    core = HookCore(RunBuffer("run-main", SCOPE), catalog=ContextCatalog(SCOPE.scope_id, (ContextSection("late", "late"),)), clock=lambda: next(ticks))
    result = core.receive(event(EventType.BEFORE_REASONING))
    assert result.context == ""
    assert result.omitted_sections == ("late",)
    assert "context_deadline_exceeded" in result.diagnostics
    assert "execution_budget_exceeded" in result.diagnostics


def test_catalog_scope_and_unimplemented_effects_explicit():
    core = HookCore(RunBuffer("run-main", SCOPE), catalog=ContextCatalog("wrong-scope", (ContextSection("s", "secret-other-project"),)))
    result = core.receive(event(EventType.SESSION_STARTED))
    assert result.context == "" and result.diagnostics == ("context_scope_mismatch",)
    assert result.deferred_effects == ("index_health_refresh_unimplemented",)
    assert core.receive(event(EventType.TOOL_COMPLETED, sequence=1)).deferred_effects == ("relevant_write_validation_unimplemented",)
    compact = core.receive(event(EventType.COMPACTION_BEFORE, sequence=2, payload={"trigger": "auto"}))
    assert compact.checkpoint and b"secret-other-project" not in compact.checkpoint
    assert core.receive(event(scope=None, sequence=3)).status == "no_project"


@pytest.mark.parametrize("runtime,provider_event", [("claude", "UserPromptSubmit"), ("codex", "UserPromptSubmit"), ("gemini", "BeforeAgent"), ("copilot", "sessionStart")])
def test_provider_output_single_json_only(runtime, provider_event):
    adapter = FrozenHookAdapter(runtime)
    wire = adapter.render_response(HookResult("ok", context="Prepared evidence"), provider_event)
    value = json.loads(wire.stdout)
    assert wire.stdout.endswith("\n") and len(wire.stdout.splitlines()) == 1
    assert "Prepared evidence" in wire.stdout and wire.exit_code == 0 and not wire.stderr
    assert "decision" not in value and "continue" not in value
    if runtime in ("claude", "codex"):
        assert value["hookSpecificOutput"]["hookEventName"] == provider_event
    if runtime == "gemini":
        assert "hookEventName" not in value["hookSpecificOutput"]


def test_copilot_prompt_output_limitation_not_false_success():
    adapter = FrozenHookAdapter("copilot")
    assert adapter.capabilities("userPromptSubmitted").can_inject_context is False
    wire = adapter.render_response(HookResult("ok", context="Ignored by provider"), "userPromptSubmitted")
    assert json.loads(wire.stdout) == {} and wire.exit_code == 1
    assert wire.stderr == "context_injection_unsupported\n"


def test_core_source_contains_no_provider_memory_branch_or_writer():
    import tessera.lifecycle as core
    source = Path(core.__file__).read_text()
    for forbidden in ("claude", "codex", "gemini", "copilot", "write_memory", "decompose_and_write", "subprocess", "ThreadPool", "llm_fn"):
        assert forbidden not in source


def test_required_semantic_parity_benchmark_and_negative_controls():
    from benchmarks.hooks.run import run
    report = run()
    assert report["passed"] and len(report["gates"]) >= 14
    assert len(set(report["semantic_sha256"].values())) == 1
    assert all(metrics["event_count"] == 14 for metrics in report["metrics"].values())
    assert report["unexecuted"]["memory_candidates"].startswith("NOT_EXECUTED")


def test_machine_readable_schema_matches_python_envelope():
    schema = json.loads((ROOT / "docs/schemas/lifecycle-event-v1.json").read_text())
    data = event().to_dict()
    assert set(schema["required"]) == set(data)
    assert schema["properties"]["canonical_type"]["enum"] == [kind.value for kind in EventType]
    assert set(schema["properties"]["identities"]["required"]) == set(data["identities"])
    assert schema["additionalProperties"] is False


def test_strict_context_error_and_identity_validation():
    core = HookCore(RunBuffer("run-main", SCOPE), policy=ExecutionPolicy(context_failure="raise"))
    with pytest.raises(LifecycleError, match="context_catalog_unavailable"):
        core.receive(event(EventType.BEFORE_REASONING))
    with pytest.raises(LifecycleError, match="invalid_identifier"):
        Identities(None, "run-main")
    with pytest.raises(LifecycleError, match="incomplete_parent_lineage"):
        Identities("s", "r", parent_run_id="parent")
    with pytest.raises(LifecycleError, match="self_parent_run"):
        Identities("s", "r", parent_run_id="r", parent_turn_id="t")


def test_provider_cwd_cannot_be_attached_to_unrelated_explicit_scope():
    case = next(c for c in FIXTURE["cases"] if c["runtime"] == "claude" and c["event"] == "UserPromptSubmit")
    payload = dict(case["payload"], cwd="/fixture/unrelated")
    with pytest.raises(LifecycleError, match="explicit_scope_mismatch"):
        FrozenHookAdapter("claude").normalize("UserPromptSubmit", payload, Invocation("d", 0, STAMP, "run-main", "turn-1"), SCOPE)


def test_result_cannot_claim_persistence_or_unrecognized_success():
    with pytest.raises(LifecycleError, match="invalid_hook_result"):
        HookResult("ok", persisted=True)
    with pytest.raises(LifecycleError, match="invalid_hook_result"):
        HookResult("did_not_execute")


def test_native_required_fields_are_not_replaced_by_integration_guesses():
    case = next(c for c in FIXTURE["cases"] if c["runtime"] == "codex" and c["event"] == "PreToolUse")
    payload = dict(case["payload"])
    payload.pop("tool_use_id")
    with pytest.raises(LifecycleError, match="invalid_provider_field:tool_use_id"):
        FrozenHookAdapter("codex").normalize("PreToolUse", payload, Invocation("d", 0, STAMP, "run-main", "turn-1", tool_call_id="guessed"), SCOPE)
    wire = FrozenHookAdapter("gemini").render_response(HookResult("ok", context="x" * 131073), "BeforeAgent")
    assert wire.exit_code == 1 and json.loads(wire.stdout) == {}
