import copy
import hashlib
import json
import subprocess
import sys

import pytest
import yaml

from tessera import TesseraEngine
from tessera.recipes import (
    PrimitiveRegistry, RecipeError, RecipeRunner, builtin_recipe, load_recipe,
)


@pytest.fixture
def engine(tmp_path):
    instance = TesseraEngine(storage_dir=str(tmp_path / "store"))
    for mem_id, mem_type, body in (
        ("project/charter", "factual", "The project provides auditable memory."),
        ("project/preference", "preference", "Prefer auditable memory reports."),
    ):
        instance.write_memory_note(mem_id=mem_id, mem_type=mem_type, episode_id="recipe-fixture",
                                   content=body, tags=["memory"], entities=[])
    instance.build_index()
    return instance


def changed(**updates):
    value = builtin_recipe("search_and_provenance").to_dict()
    value.update(updates)
    return value


def load(value):
    return load_recipe(yaml.safe_dump(value))


def snapshot(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def test_registry_is_closed_typed_and_owned():
    descriptors = PrimitiveRegistry().descriptors()
    assert len(descriptors) == 3
    for descriptor in descriptors:
        assert descriptor.version == 1 and descriptor.owner.startswith("issue-")
        assert descriptor.input_schema and descriptor.output_schema.endswith(".v1")
        assert not descriptor.network and not descriptor.writes_canonical_state
    assert [item.deterministic for item in descriptors] == [False, False, True]
    assert not hasattr(PrimitiveRegistry(), "register")


@pytest.mark.parametrize("name", ["search_and_provenance", "compare_drawers"])
def test_read_only_real_workflow_parity_and_retry(engine, tmp_path, name):
    runner = RecipeRunner(engine)
    recipe = builtin_recipe(name)
    inputs = {"query": "auditable memory"}
    before = snapshot(tmp_path)
    plan = runner.plan(recipe, inputs)
    assert plan["canonical_state_affected"] == [] and not plan["network"]
    assert plan["max_primitive_calls"] == 2 and len(plan["primitive_versions"]) == 2
    first = runner.run(recipe, inputs)
    assert first == runner.run(recipe, inputs)
    assert first["status"] == "completed" and first["completed_steps"] == 2
    if name == "search_and_provenance":
        hits = engine.retrieve_context_contract("auditable memory", top_n=1)
        assert first["outputs"]["search"]["hits"] == hits
        assert first["outputs"]["provenance"]["records"] == [
            record.to_dict() for record in engine.evidence_ledger.for_memory(hits[0]["id"])]
    else:
        for store in ("facts", "preferences"):
            assert first["outputs"][store]["hits"] == engine.retrieve_from_store("auditable memory", store, top_n=1)
    assert snapshot(tmp_path) == before


def test_plan_never_calls_engine_or_scope_reader(engine, monkeypatch):
    runner = RecipeRunner(engine)
    monkeypatch.setattr(runner, "_invoke", lambda *_: pytest.fail("executed"))
    monkeypatch.setattr(runner, "_check_scope", lambda: pytest.fail("read source"))
    runner.plan(builtin_recipe("compare_drawers"), {"query": "memory"})


def test_external_recipes_need_exact_fingerprint(engine):
    definition = load(changed())
    runner = RecipeRunner(engine)
    assert runner.plan(definition, {"query": "memory"})["confirmation_gates"]
    with pytest.raises(RecipeError, match="UNTRUSTED_RECIPE"):
        runner.run(definition, {"query": "memory"})
    with pytest.raises(RecipeError, match="UNTRUSTED_RECIPE"):
        runner.run(definition, {"query": "memory"}, approved_fingerprint="wrong")
    assert runner.run(definition, {"query": "memory"}, approved_fingerprint=definition.fingerprint)["status"] == "completed"
    altered = load(changed(name="renamed"))
    with pytest.raises(RecipeError, match="UNTRUSTED_RECIPE"):
        runner.run(altered, {"query": "memory"}, approved_fingerprint=definition.fingerprint)


@pytest.mark.parametrize("text", [
    "[", "name: a\nname: b", "a: &x [*x]", "!!python/object/apply:os.system [echo forbidden]",
    "a: !local forbidden", "? [unhashable]\n: value", "a: 1\n---\nb: 2",
    "[" * 13 + "]" * 13, "x" * 32769,
])
def test_bad_yaml_rejected_without_execution(text):
    with pytest.raises(RecipeError):
        load_recipe(text)


@pytest.mark.parametrize("update", [
    {"version": True}, {"version": 2}, {"inputs": {"query": "secret"}},
    {"requires": ["read_memory", "network"]}, {"requires": ["read_memory"]},
    {"requires": ["read_memory", "read_source", "read_source"]},
    {"while": True}, {"loop": {"repeat": 100}}, {"shell": "echo forbidden"},
    {"imports": ["os"]}, {"source": "https://invalid.example/recipe"},
    {"steps": []}, {"outputs": ["missing"]}, {"outputs": ["search", "search"]},
    {"inputs": {"../../path": "text"}},
])
def test_closed_schema_rejects_unsupported_features(update):
    with pytest.raises(RecipeError):
        load(changed(**update))


@pytest.mark.parametrize("primitive", ["write_memory", "decompose_episode", "admission_preview", "import_batch", "shell", "os.system"])
def test_unavailable_writes_candidates_and_code_fail_closed(primitive):
    recipe = changed()
    recipe["steps"][0]["use"] = primitive
    with pytest.raises(RecipeError, match="UNAVAILABLE_PRIMITIVE_VERSION"):
        load(recipe)


@pytest.mark.parametrize("value", [0, -1, True, 1.5, 17, 99999999999999999])
def test_step_budgets_are_bounded(value):
    recipe = changed()
    recipe["budgets"]["max_steps"] = value
    with pytest.raises(RecipeError, match="BUDGET"):
        load(recipe)


def test_step_count_overflow_and_loop_refusal():
    recipe = changed()
    recipe["steps"] = [copy.deepcopy(step) for _ in range(9) for step in recipe["steps"]]
    with pytest.raises(RecipeError, match="STEP_BUDGET"):
        load(recipe)
    recipe = changed()
    recipe["steps"][0]["for_each"] = {"ref": "inputs.query"}
    with pytest.raises(RecipeError, match="INVALID_SCHEMA"):
        load(recipe)


@pytest.mark.parametrize("ref", [
    "steps.provenance.records.0.id", "steps.search.hits.0.__class__", "steps.search.hits.50.id",
    "steps.search.hits.-1.id", "steps.search.hits.00.id", "inputs.absent", "env.API_KEY",
    "file:///etc/passwd", "https://invalid.example", "steps.future.hits.0.id",
])
def test_references_are_safe_typed_backward_edges(ref):
    recipe = changed()
    recipe["steps"][1]["with"]["memory_id"] = {"ref": ref}
    with pytest.raises(RecipeError, match="INVALID_REFERENCE"):
        load(recipe)


def test_forward_and_type_mismatches():
    recipe = changed()
    recipe["steps"][0]["with"]["query"] = {"ref": "steps.search.hits.0.id"}
    with pytest.raises(RecipeError, match="INVALID_REFERENCE"):
        load(recipe)
    recipe = changed()
    recipe["steps"][0]["with"]["top_n"] = {"ref": "inputs.query"}
    with pytest.raises(RecipeError, match="REFERENCE_TYPE_MISMATCH"):
        load(recipe)


def test_missing_capability(engine):
    with pytest.raises(RecipeError, match="MISSING_CAPABILITY"):
        RecipeRunner(engine, capabilities=["read_memory"]).plan(builtin_recipe("compare_drawers"), {"query": "memory"})
    with pytest.raises(RecipeError, match="UNKNOWN_EFFECT"):
        RecipeRunner(engine, capabilities=["network"])


def test_contract_version_and_input_types(engine):
    recipe = changed()
    recipe["steps"][0]["version"] = 2
    with pytest.raises(RecipeError, match="UNAVAILABLE_PRIMITIVE_VERSION"):
        load(recipe)
    for inputs in ({"query": "ok", "path": "/etc"}, {"query": None}, {"query": ""}, {"query": "x" * 4097}):
        with pytest.raises(RecipeError):
            RecipeRunner(engine).plan(builtin_recipe("compare_drawers"), inputs)


def test_partial_failure_is_truthful_and_secret_free(engine, monkeypatch):
    runner = RecipeRunner(engine)
    def broken(_):
        raise OSError("secret input or path must not appear")
    monkeypatch.setattr(engine.evidence_ledger, "for_memory", broken)
    result = runner.run(builtin_recipe("search_and_provenance"), {"query": "memory"})
    assert result["status"] == "failed" and result["completed_steps"] == 1
    assert result["error"] == "PRIMITIVE_FAILED"
    assert [entry["status"] for entry in result["journal"]] == ["completed", "failed"]
    assert set(result["outputs"]) == {"search"}
    assert "secret" not in json.dumps(result)


def test_empty_search_reports_reference_failure(engine):
    result = RecipeRunner(engine).run(builtin_recipe("search_and_provenance"), {"query": "zxqvbn"})
    assert result["status"] == "failed" and result["error"] == "REFERENCE_UNAVAILABLE"
    assert result["outputs"]["search"] == {"hits": []}


def test_cancellation_before_and_after_completed_read(engine):
    runner = RecipeRunner(engine)
    result = runner.run(builtin_recipe("compare_drawers"), {"query": "memory"}, cancelled=lambda: True)
    assert result["status"] == "cancelled" and not result["journal"]
    calls = iter([False, True])
    result = runner.run(builtin_recipe("compare_drawers"), {"query": "memory"}, cancelled=lambda: next(calls))
    assert result["status"] == "cancelled" and result["completed_steps"] == 1
    assert result["journal"][0]["status"] == "completed"


def test_timeout_after_read_does_not_claim_rollback(engine, monkeypatch):
    ticks = iter([0, 0, 31])
    monkeypatch.setattr("tessera.recipes.time.monotonic", lambda: next(ticks))
    result = RecipeRunner(engine).run(builtin_recipe("compare_drawers"), {"query": "memory"})
    assert result["status"] == "timed_out" and result["completed_steps"] == 1
    assert result["journal"][0]["status"] == "completed"


def test_resume_refuses_without_execution(engine, monkeypatch):
    runner = RecipeRunner(engine)
    monkeypatch.setattr(runner, "_invoke", lambda *_: pytest.fail("executed"))
    with pytest.raises(RecipeError, match="RESUME_UNSUPPORTED"):
        runner.run(builtin_recipe("compare_drawers"), {"query": "memory"}, resume={})


def test_output_budget_and_output_schema(engine, monkeypatch):
    recipe = changed()
    recipe["budgets"]["max_output_bytes"] = 1
    definition = load(recipe)
    result = RecipeRunner(engine).run(definition, {"query": "memory"}, approved_fingerprint=definition.fingerprint)
    assert result["status"] == "failed" and result["error"] == "OUTPUT_BUDGET_EXCEEDED"
    assert not result["outputs"]
    monkeypatch.setattr(engine, "retrieve_context_contract", lambda **_: [{"id": 123}])
    result = RecipeRunner(engine).run(builtin_recipe("search_and_provenance"), {"query": "memory"})
    assert result["error"] == "INVALID_PRIMITIVE_OUTPUT"


def test_scope_is_bound_and_no_external_paths(engine, tmp_path):
    runner = RecipeRunner(engine)
    external = tmp_path / "external.md"
    external.write_text("OUTSIDE SECRET")
    engine.graph.nodes["project/charter"]["filepath"] = str(external)
    result = runner.run(builtin_recipe("compare_drawers"), {"query": "memory"})
    assert result["error"] == "UNSAFE_SOURCE_PATH" and not result["outputs"]
    engine.storage_dir = str(tmp_path)
    assert runner.run(builtin_recipe("compare_drawers"), {"query": "memory"})["error"] == "SCOPE_CHANGED"


def test_symlink_swap_refused(engine, tmp_path):
    path = tmp_path / "store/project/charter.md"
    outside = tmp_path / "outside.md"
    outside.write_text("OUTSIDE SECRET")
    path.unlink()
    path.symlink_to(outside)
    result = RecipeRunner(engine).run(builtin_recipe("compare_drawers"), {"query": "memory"})
    assert result["error"] == "UNSAFE_SOURCE_PATH"
    assert "OUTSIDE SECRET" not in json.dumps(result)


def test_source_budget_is_bounded(engine, tmp_path):
    (tmp_path / "store/project/charter.md").write_text("x" * (8 * 1024 * 1024 + 1))
    result = RecipeRunner(engine).run(builtin_recipe("compare_drawers"), {"query": "memory"})
    assert result["error"] == "SOURCE_READ_BUDGET_EXCEEDED"


def test_semantic_output_matches_real_cli_and_mcp(engine):
    from tessera import mcp_server
    original = mcp_server._engine
    mcp_server._engine = engine
    try:
        result = RecipeRunner(engine).run(builtin_recipe("search_and_provenance"), {"query": "auditable memory"})
        hits = result["outputs"]["search"]["hits"]
        assert hits == mcp_server.query_memories("auditable memory", top_n=1)
        command = [sys.executable, "-m", "tessera.cli", "query", engine.storage_dir,
                   "auditable memory", "--top-n", "1", "--json"]
        assert hits == json.loads(subprocess.run(command, check=True, text=True, capture_output=True).stdout)
    finally:
        mcp_server._engine = original


def test_definition_integrity_and_builtin_impersonation(engine):
    from tessera.recipes import RecipeDefinition
    original = builtin_recipe("search_and_provenance")
    value = original.to_dict()
    value["steps"][0]["with"]["query"] = "changed"
    forged = RecipeDefinition(json.dumps(value).encode(), "builtin")
    assert forged.fingerprint != original.fingerprint
    with pytest.raises(RecipeError, match="BUILTIN_DEFINITION_MISMATCH"):
        RecipeRunner(engine).run(forged, {"query": "memory"})


def test_repeated_source_paths_count_once(engine, tmp_path):
    path = tmp_path / "store/project/charter.md"
    path.write_text("x" * (4 * 1024 * 1024))
    for index in range(3):
        engine.graph.add_node("duplicate" + str(index), filepath=str(path))
    runner = RecipeRunner(engine)
    runner._check_scope()
    assert runner.plan(builtin_recipe("compare_drawers"), {"query": "memory"})["source_preflight_max_bytes"] == 8 * 1024 * 1024


def test_special_source_refused(engine, tmp_path):
    import os
    path = tmp_path / "store/project/charter.md"
    path.unlink()
    os.mkfifo(path)
    result = RecipeRunner(engine).run(builtin_recipe("compare_drawers"), {"query": "memory"})
    assert result["error"] == "UNSAFE_SOURCE_PATH"
    assert result["journal"][0]["invoked"] is False


def test_input_snapshot_matches_plan_if_caller_changes_it(engine):
    inputs = {"query": "memory"}
    def change_inputs():
        inputs["query"] = "different"
        return False
    runner = RecipeRunner(engine)
    recipe = builtin_recipe("compare_drawers")
    expected = runner.run(recipe, {"query": "memory"})
    assert runner.run(recipe, inputs, cancelled=change_inputs) == expected


@pytest.mark.parametrize("text", ["\ud800", "value: " + "1" * 5000])
def test_parser_failures_use_safe_error_code(text):
    with pytest.raises(RecipeError, match="INVALID_YAML"):
        load_recipe(text)


def test_bad_cancellation_callback_preserves_partial_journal(engine):
    calls = 0
    def failing_callback():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError("sensitive callback content")
        return False
    result = RecipeRunner(engine).run(builtin_recipe("compare_drawers"), {"query": "memory"}, cancelled=failing_callback)
    assert result["status"] == "failed" and result["error"] == "CANCEL_CHECK_FAILED"
    assert result["completed_steps"] == 1 and result["journal"][0]["status"] == "completed"
    assert "sensitive" not in json.dumps(result)
