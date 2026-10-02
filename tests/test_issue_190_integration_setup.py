"""All mutations here are synthetic pytest tmp_path fixtures, never client config."""
import json
from pathlib import Path

import pytest

from tessera.cli import main
from tessera.integration_setup import (
    DocumentState, IntegrationError, SetupRequest, apply_plan, build_plan,
    config_path, detect_runtimes, ownership_path, preview_target, rollback_plan,
)


def raw(value):
    return json.dumps(value).encode()


def install(runtime="gemini", scope="project", name="fixture-store"):
    return SetupRequest(runtime, scope, store_name=name)


def save_fixture(root, state):
    """Explicit fixture materialization, deliberately not a product filesystem API."""
    root.mkdir(parents=True, exist_ok=True)
    for path, data in [(root / "config.json", state.config), (root / "owner.json", state.ownership)]:
        if data is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(data)


def read_fixture(root):
    return DocumentState(*[path.read_bytes() if path.exists() else None
                           for path in (root / "config.json", root / "owner.json")])


@pytest.mark.parametrize("runtime", ["claude", "gemini"])
@pytest.mark.parametrize("scope", ["project", "user"])
def test_fixture_apply_idempotency_remove_and_exact_rollback(tmp_path, runtime, scope):
    original = DocumentState(b'{ "editor": {"theme":"dark"}, "mcpServers": {"other": {"command":"fixture"}} }\n')
    folder = tmp_path / runtime / scope
    save_fixture(folder, original)
    request = install(runtime, scope)
    plan = build_plan(request, read_fixture(folder))
    assert plan.operation == "add"
    applied = apply_plan(plan, read_fixture(folder))
    save_fixture(folder, applied)
    assert json.loads(applied.config)["editor"] == {"theme": "dark"}
    assert json.loads(applied.config)["mcpServers"]["other"] == {"command": "fixture"}
    assert build_plan(request, read_fixture(folder)).operation == "noop"
    assert build_plan(request, applied).after == applied
    save_fixture(folder, rollback_plan(plan, read_fixture(folder)))
    assert read_fixture(folder) == original  # including whitespace and missing sidecar
    save_fixture(folder, apply_plan(plan, read_fixture(folder)))
    removal = build_plan(SetupRequest(runtime, scope, remove=True), read_fixture(folder))
    removed = apply_plan(removal, read_fixture(folder))
    save_fixture(folder, removed)
    assert json.loads(removed.config) == json.loads(original.config)
    assert removed.ownership is None
    assert build_plan(SetupRequest(runtime, scope, remove=True), removed).operation == "noop"
    assert rollback_plan(removal, read_fixture(folder)) == applied


@pytest.mark.parametrize("original", [DocumentState(), DocumentState(b"{}"), DocumentState(b'{"mcpServers":{}}')])
def test_remove_only_owned_empty_containers(original):
    applied = apply_plan(build_plan(install(), original), original)
    removal = build_plan(SetupRequest("gemini", "project", remove=True), applied)
    removed = apply_plan(removal, applied)
    assert (removed.config is None) == (original.config is None)
    if removed.config is not None:
        assert json.loads(removed.config) == json.loads(original.config)


def test_remove_preserves_new_unrelated_config():
    added = build_plan(install()).after
    data = json.loads(added.config)
    data["mcpServers"]["other"] = {"command": "unrelated"}
    data["theme"] = "dark"
    edited = DocumentState(raw(data), added.ownership)
    removed = build_plan(SetupRequest("gemini", "project", remove=True), edited).after
    assert json.loads(removed.config) == {"theme": "dark", "mcpServers": {"other": {"command": "unrelated"}}}


def test_owned_command_upgrade_and_stale_apply_rollback():
    first = build_plan(install()).after
    plan = build_plan(install(name="new-store"), first)
    assert plan.operation == "update"
    assert plan.to_dict()["planned_mutations"][0]["after"]["args"] == ["--global", "new-store"]
    for state in (DocumentState(first.config + b" ", first.ownership),
                  DocumentState(first.config, first.ownership + b" ")):
        with pytest.raises(IntegrationError, match="stale plan"):
            apply_plan(plan, state)
    applied = apply_plan(plan, first)
    with pytest.raises(IntegrationError, match="stale rollback"):
        rollback_plan(plan, DocumentState(applied.config + b" ", applied.ownership))
    assert rollback_plan(plan, applied) == first


@pytest.mark.parametrize("remove", [True, False])
def test_existing_unowned_entry_is_never_adopted_even_if_equal(remove):
    current = DocumentState(raw({"mcpServers": {"tessera": install().descriptor()}}))
    request = SetupRequest("gemini", "project", remove=True) if remove else install()
    with pytest.raises(IntegrationError, match="not owned"):
        build_plan(request, current)


@pytest.mark.parametrize("change", ["entry", "missing", "empty_owner", "unknown_owner", "wrong_runtime"])
def test_partial_or_modified_ownership_is_not_silently_repaired(change):
    state = build_plan(install()).after
    data, owner = json.loads(state.config), json.loads(state.ownership)
    if change == "entry":
        data["mcpServers"]["tessera"]["command"] = "old-or-user-edited-command"
    elif change == "missing":
        del data["mcpServers"]["tessera"]
    elif change == "empty_owner":
        owner = {}
    elif change == "unknown_owner":
        owner["schema_version"] = "future-version"
    else:
        owner["runtime"] = "claude"
    with pytest.raises(IntegrationError):
        build_plan(install(), DocumentState(raw(data), raw(owner)))


@pytest.mark.parametrize("bad", [b"[]", b"null", b'{"mcpServers": []}', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"mcpServers":', b"\xff", b" " * (1024*1024 + 1)])
def test_unknown_or_ambiguous_json_is_refused(bad):
    with pytest.raises(IntegrationError):
        build_plan(install(), DocumentState(bad))


def test_cross_scope_conflicts_block_install_but_not_owned_removal():
    other = DocumentState(raw({"mcpServers": {"tessera": {"url": "fixture-invalid.example"}}}))
    with pytest.raises(IntegrationError, match="scope conflict"):
        build_plan(install(), other_scope=other)
    state = build_plan(install()).after
    assert build_plan(SetupRequest("gemini", "project", remove=True), state, other_scope=other).operation == "remove"


def test_no_secrets_in_public_plan_owner_or_repr():
    secret = "fixture-secret-never-print"
    state = DocumentState(raw({"credentials": secret, "mcpServers": {"other": {"env": {"TOKEN": secret}}}}))
    plan = build_plan(install(), state)
    assert secret not in json.dumps(plan.to_dict())
    assert secret.encode() not in plan.after.ownership
    assert secret not in repr(plan) + repr(state)
    assert secret in plan.after.config.decode()  # preserved in provider document, never copied to ownership


def test_portable_project_descriptor_and_user_local_scope(tmp_path):
    plan = build_plan(install("claude"))
    descriptor = json.loads(plan.after.config)["mcpServers"]["tessera"]
    assert descriptor == {"command": "tessera-mcp", "args": ["--global", "fixture-store"]}
    assert str(tmp_path) not in json.dumps(descriptor)
    with pytest.raises(IntegrationError, match="user-local"):
        build_plan(SetupRequest("claude", "project", store_path=str(tmp_path / "store")))
    user = build_plan(SetupRequest("claude", "user", store_path=str(tmp_path / "store")))
    assert user.to_dict()["binding"]["kind"] == "user-local-path"
    with pytest.raises(IntegrationError, match="absolute"):
        build_plan(SetupRequest("gemini", "user", store_path="relative"))


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    home, project = tmp_path / "home", tmp_path / "project"
    home.mkdir()
    project.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(project)
    for key in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "GEMINI_CLI_HOME", "COPILOT_HOME"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PATH", "")
    return home, project


def contents(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("runtime", ["claude", "gemini"])
def test_direct_guided_json_parity_zero_mutation_and_no_probe(sandbox, capsys, monkeypatch, runtime):
    home, project = sandbox
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("provider execution is forbidden"))
    before = contents(project.parent)
    flags = ["--scope", "project", "--store-name", "fixture-store", "--dry-run", "--json"]
    assert main(["integrate", runtime, *flags]) == 0
    direct = json.loads(capsys.readouterr().out)
    assert main(["mcp", "setup", "--runtime", runtime, *flags]) == 0
    guided = json.loads(capsys.readouterr().out)
    assert direct == guided
    assert direct["applied"] is False
    assert direct["selected_integrations"][0]["operation"] == "add"
    assert contents(project.parent) == before
    assert all(item["version_probed"] is False for item in direct["detected_runtimes"])


def test_apply_is_blocked_without_writes(sandbox, capsys):
    home, project = sandbox
    before = contents(project.parent)
    assert main(["integrate", "claude", "--scope", "project", "--store-name", "fixture", "--apply", "--json"]) == 2
    output = json.loads(capsys.readouterr().out)
    assert "unavailable" in output["error"]
    assert output["applied"] is False
    assert contents(project.parent) == before


@pytest.mark.parametrize("runtime", ["codex", "copilot", "generic-mcp"])
def test_unsupported_runtime_reports_real_boundary(sandbox, capsys, runtime):
    assert main(["integrate", runtime, "--scope", "project", "--store-name", "fixture", "--json"]) == 2
    result = json.loads(capsys.readouterr().out)["selected_integrations"][0]
    assert result["status"] == "blocked" and not result["planned_mutations"]
    assert result["capabilities"]["before_reasoning_context"] is False
    assert result["capabilities"]["runtime_compatibility"] == "unverified"


def test_no_silent_selection_or_missing_store(sandbox, capsys):
    assert main(["mcp", "setup", "--scope", "project", "--json"]) == 2
    output = json.loads(capsys.readouterr().out)
    assert not output["selected_integrations"]
    assert "select targets" in output["error"]
    assert main(["integrate", "claude", "--scope", "project", "--json"]) == 2
    assert "exactly one" in json.loads(capsys.readouterr().out)["selected_integrations"][0]["error"]


def test_guided_prompt_selection_and_cancel(sandbox, capsys, monkeypatch):
    import sys
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *_: "gemini, claude,gemini")
    assert main(["mcp", "setup", "--scope", "project", "--store-name", "fixture"]) == 0
    output = capsys.readouterr().out
    assert output.count("gemini / project: planned") == 1
    assert "claude / project: planned" in output
    monkeypatch.setattr("builtins.input", lambda *_: "")
    assert main(["mcp", "setup", "--scope", "project", "--store-name", "fixture"]) == 2
    assert "did not select" in capsys.readouterr().out


def test_config_is_not_installation_and_versions_never_assumed(sandbox):
    home, project = sandbox
    (project / ".mcp.json").write_text("{}")
    evidence = detect_runtimes(project, home, which=lambda _: None)[0]
    assert evidence["executable_on_path"] is None
    assert evidence["config_evidence"] == [str(project / ".mcp.json")]
    assert evidence["version"] is None


def test_shadowed_local_scope_custom_home_symlink_and_home_overlap(sandbox):
    home, project = sandbox
    (home / ".claude.json").write_bytes(raw({"projects": {str(project): {"mcpServers": {"tessera": {"command": "other"}}}}}))
    assert "local scope conflicts" in preview_target(install("claude"), project, home, environ={})["error"]
    assert "custom provider home" in preview_target(install(), project, home, environ={"GEMINI_CLI_HOME": "fixture"})["error"]
    assert "equals home" in preview_target(install(), home, home, environ={})["error"]
    target = project / ".gemini"
    target.symlink_to(home, target_is_directory=True)
    assert "symlink" in preview_target(install(), project, home, environ={})["error"]


def test_existing_owned_removal_preview_and_malformed_error_redaction(sandbox, capsys):
    home, project = sandbox
    path = config_path("gemini", "project", project, home)
    path.parent.mkdir()
    state = build_plan(install()).after
    path.write_bytes(state.config)
    ownership_path(path, "gemini", "project").write_bytes(state.ownership)
    before = contents(project.parent)
    assert main(["integrate", "gemini", "--scope", "project", "--remove", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["selected_integrations"][0]["operation"] == "remove"
    assert contents(project.parent) == before
    path.write_bytes(b'{"SECRET": "fixture-private", BROKEN}')
    assert main(["integrate", "gemini", "--scope", "project", "--remove", "--json"]) == 2
    assert "fixture-private" not in capsys.readouterr().out


def test_stale_other_scope_is_guarded_before_in_memory_apply():
    state = DocumentState()
    other = DocumentState(raw({"theme": "original"}))
    plan = build_plan(install(), state, other_scope=other)
    with pytest.raises(IntegrationError, match="other scope changed"):
        apply_plan(plan, state)
    assert apply_plan(plan, state, other_scope=other) == plan.after
    changed = DocumentState(raw({"mcpServers": {"tessera": {"command": "other"}}}))
    with pytest.raises(IntegrationError, match="other scope changed"):
        apply_plan(plan, state, other_scope=changed)


def fixture_file_plan(tmp_path, *, before=DocumentState(), request=None):
    from tessera.integration_files import bind_file_plan
    request = request or install()
    target = tmp_path / "project" / ".gemini" / "settings.json"
    other = tmp_path / "home" / ".gemini" / "settings.json"
    if before.config is not None:
        target.parent.mkdir(parents=True)
        target.write_bytes(before.config)
    if before.ownership is not None:
        ownership_path(target, request.runtime, request.scope).write_bytes(before.ownership)
    return bind_file_plan(build_plan(request, before), target, other)


def test_explicit_filesystem_apply_and_rollback_restore_bytes_modes_and_absence(tmp_path):
    from tessera.integration_files import apply_file_plan, rollback_file_plan
    plan = fixture_file_plan(tmp_path)
    receipt = apply_file_plan(plan)
    assert plan.config_path.read_bytes() == plan.plan.after.config
    assert plan.owner_path.read_bytes() == plan.plan.after.ownership
    assert plan.config_path.stat().st_mode & 0o777 == 0o600
    rollback_file_plan(receipt)
    assert not plan.config_path.parent.exists()
    assert not list(tmp_path.rglob("*"))
    before = DocumentState(b'{ "theme": "fixture" }\n')
    plan = fixture_file_plan(tmp_path, before=before)
    plan.config_path.chmod(0o640)
    from tessera.integration_files import bind_file_plan
    plan = bind_file_plan(plan.plan, plan.config_path, plan.other_config_path)
    receipt = apply_file_plan(plan)
    assert plan.config_path.stat().st_mode & 0o777 == 0o640
    rollback_file_plan(receipt)
    assert plan.config_path.read_bytes() == before.config
    assert plan.config_path.stat().st_mode & 0o777 == 0o640


def test_filesystem_remove_only_owned_entry_and_noop(tmp_path):
    from tessera.integration_files import apply_file_plan, bind_file_plan, rollback_file_plan
    initial = DocumentState(raw({"mcpServers": {"other": {"command": "fixture"}}}))
    plan = fixture_file_plan(tmp_path, before=initial)
    receipt = apply_file_plan(plan)
    repeated = bind_file_plan(build_plan(install(), plan.plan.after), plan.config_path, plan.other_config_path)
    assert repeated.plan.operation == "noop"
    apply_file_plan(repeated)
    removal = build_plan(SetupRequest("gemini", "project", remove=True), plan.plan.after)
    removed_receipt = apply_file_plan(bind_file_plan(removal, plan.config_path, plan.other_config_path))
    assert json.loads(plan.config_path.read_bytes()) == json.loads(initial.config)
    assert not plan.owner_path.exists()
    rollback_file_plan(removed_receipt)
    assert plan.config_path.read_bytes() == receipt.after_config.data


@pytest.mark.parametrize("target", ["config", "owner", "other", "permissions"])
def test_filesystem_stale_plan_refuses_changes(tmp_path, target):
    from tessera.integration_files import FileTransactionError, apply_file_plan
    plan = fixture_file_plan(tmp_path, before=DocumentState(b"{}"))
    if target == "config":
        plan.config_path.write_text('{"changed": true}')
    elif target == "owner":
        plan.owner_path.write_text("{}")
    elif target == "other":
        plan.other_config_path.parent.mkdir(parents=True)
        plan.other_config_path.write_text('{"changed": true}')
    else:
        plan.config_path.chmod(0o640)
    before = contents(tmp_path)
    with pytest.raises(FileTransactionError, match="no partial writes remain"):
        apply_file_plan(plan)
    assert contents(tmp_path) == before


def test_filesystem_apply_failure_restores_first_file_without_disk_backup(tmp_path, monkeypatch):
    from tessera import integration_files as files
    plan = fixture_file_plan(tmp_path, before=DocumentState(b'{"fixture": "keep"}'))
    original = files._replace
    def fail_owner(path, before, after):
        if path == plan.owner_path:
            raise OSError("simulated write failure")
        return original(path, before, after)
    monkeypatch.setattr(files, "_replace", fail_owner)
    before = contents(tmp_path)
    with pytest.raises(files.FileTransactionError) as error:
        files.apply_file_plan(plan)
    assert error.value.recovery_complete is True
    assert contents(tmp_path) == before
    assert not list(tmp_path.rglob(".tessera-setup-*"))


def test_filesystem_failure_and_rollback_never_clobber_intervening_edit(tmp_path, monkeypatch):
    from tessera import integration_files as files
    plan = fixture_file_plan(tmp_path)
    original = files._replace
    concurrent = b'{"external": "keep this"}'
    def edit_then_fail(path, before, after):
        if path == plan.owner_path:
            plan.config_path.write_bytes(concurrent)
            raise OSError("simulated concurrent edit")
        return original(path, before, after)
    monkeypatch.setattr(files, "_replace", edit_then_fail)
    with pytest.raises(files.FileTransactionError) as error:
        files.apply_file_plan(plan)
    assert error.value.recovery_complete is False
    assert plan.config_path.read_bytes() == concurrent


def test_filesystem_stale_rollback_lock_symlink_and_hardlink(tmp_path):
    from tessera import integration_files as files
    plan = fixture_file_plan(tmp_path)
    receipt = files.apply_file_plan(plan)
    plan.config_path.write_text('{"concurrent": true}')
    before = contents(tmp_path)
    with pytest.raises(files.FileTransactionError):
        files.rollback_file_plan(receipt)
    assert contents(tmp_path) == before
    lock = plan.owner_path.with_suffix(".lock")
    lock.write_text("another transaction")
    with pytest.raises(files.FileTransactionError):
        files.apply_file_plan(plan)
    assert lock.read_text() == "another transaction"
    link = tmp_path / "link.json"
    link.symlink_to(plan.config_path)
    with pytest.raises(IntegrationError, match="symlink"):
        files.bind_file_plan(plan.plan, link, plan.other_config_path)
    hardlink = tmp_path / "hardlink.json"
    import os
    os.link(plan.config_path, hardlink)
    with pytest.raises(IntegrationError, match="single-link"):
        files.bind_file_plan(plan.plan, plan.config_path, plan.other_config_path)


def test_filesystem_rejects_special_files_and_alias_scope(tmp_path):
    from tessera import integration_files as files
    import os
    config = tmp_path / "config.json"
    if hasattr(os, "mkfifo"):
        os.mkfifo(config)
        with pytest.raises(IntegrationError, match="regular file"):
            files.bind_file_plan(build_plan(install()), config, tmp_path / "other.json")
        config.unlink()
    with pytest.raises(IntegrationError, match="distinct"):
        files.bind_file_plan(build_plan(install()), config, tmp_path / "child" / ".." / "config.json")


@pytest.mark.parametrize("bad", [b'{"unrelated": 1e999}', b'{"unrelated": "\\ud800"}'])
def test_nonfinite_or_invalid_unicode_roundtrip_is_refused(bad):
    with pytest.raises(IntegrationError, match="finite UTF-8"):
        build_plan(install(), DocumentState(bad))


def test_owned_legacy_launcher_update_and_exact_sidecar_preview():
    import hashlib
    old = build_plan(install()).after
    document, owner = json.loads(old.config), json.loads(old.ownership)
    document["mcpServers"]["tessera"] = {"command": "python", "args": ["-m", "tessera.mcp_server"]}
    canonical_entry = (json.dumps(document["mcpServers"]["tessera"], ensure_ascii=False, indent=2) + "\n").encode()
    owner["entry_sha256"] = hashlib.sha256(canonical_entry).hexdigest()
    plan = build_plan(install(), DocumentState(raw(document), raw(owner)))
    assert plan.operation == "update"
    mutations = plan.to_dict()["planned_mutations"]
    assert mutations[0]["after"]["command"] == "tessera-mcp"
    assert mutations[0]["config_file_action"] == "rewrite"
    assert mutations[1]["after"] == json.loads(plan.after.ownership)
