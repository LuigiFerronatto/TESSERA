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
    assert "plan-hash" in output["error"]
    assert output["applied"] is False
    assert contents(project.parent) == before


@pytest.mark.parametrize("runtime", ["codex", "generic-mcp"])
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


def cli_result(capsys, args):
    code = main([*args, "--json"])
    return code, json.loads(capsys.readouterr().out)


def preview_and_apply(capsys, args):
    code, preview = cli_result(capsys, args)
    assert code == 0, preview
    code, applied = cli_result(capsys, [*args, "--apply", "--plan-hash", preview["plan_hash"]])
    assert code == 0, applied
    assert applied["applied"] is True
    return preview, applied


@pytest.mark.parametrize("runtime", ["claude", "gemini", "copilot"])
@pytest.mark.parametrize("scope", ["project", "user"])
def test_cli_hash_bound_install_update_remove_rollback(sandbox, capsys, runtime, scope):
    home, project = sandbox
    base = ["integrate", runtime, "--scope", scope, "--config-home", str(home)]
    path = config_path(runtime, scope, project, home)
    path.parent.mkdir(parents=True, exist_ok=True)
    original = {"mcpServers": {"unrelated": {"command": "fixture", "env": {"TOKEN": "fixture-secret"}}}}
    path.write_bytes(raw(original))
    first, _ = preview_and_apply(capsys, [*base, "--store-name", "fixture"])
    assert "fixture-secret" not in json.dumps(first)
    code, unchanged = cli_result(capsys, [*base, "--store-name", "fixture"])
    assert code == 0 and unchanged["selected_integrations"][0]["operation"] == "noop"
    preview_and_apply(capsys, [*base, "--store-name", "changed"])
    preview_and_apply(capsys, [*base, "--rollback"])
    assert json.loads(path.read_bytes())["mcpServers"]["tessera"]["args"] == ["--global", "fixture"]
    preview_and_apply(capsys, [*base, "--remove"])
    assert json.loads(path.read_bytes()) == original
    preview_and_apply(capsys, [*base, "--rollback"])
    assert json.loads(path.read_bytes())["mcpServers"]["tessera"]["args"] == ["--global", "fixture"]
    assert json.loads(path.read_bytes())["mcpServers"]["unrelated"] == original["mcpServers"]["unrelated"]


def test_cli_rollback_fresh_install_restores_absence_and_does_not_store_secrets(sandbox, capsys):
    home, project = sandbox
    args = ["integrate", "gemini", "--scope", "project"]
    preview_and_apply(capsys, [*args, "--store-name", "fixture"])
    path = config_path("gemini", "project", project, home)
    preview_and_apply(capsys, [*args, "--rollback"])
    assert not path.exists()
    assert not ownership_path(path, "gemini", "project").exists()
    assert not list(path.parent.glob("*"))


@pytest.mark.parametrize("change", ["config", "permissions", "receipt", "selection", "binding"])
def test_cli_hash_refuses_stale_or_changed_request_without_writes(sandbox, capsys, change):
    home, project = sandbox
    args = ["integrate", "gemini", "--scope", "project", "--store-name", "fixture"]
    path = config_path("gemini", "project", project, home)
    path.parent.mkdir()
    path.write_text("{}")
    code, preview = cli_result(capsys, args)
    assert code == 0
    if change == "config":
        path.write_text('{"other": true}')
    elif change == "permissions":
        path.chmod(0o640)
    elif change == "receipt":
        from tessera.integration_cli import receipt_path
        receipt_path(path, "gemini", "project").write_text("{}")
    elif change == "selection":
        args[1] = "claude"
    else:
        args[-1] = "changed"
    before = contents(project.parent)
    code, result = cli_result(capsys, [*args, "--apply", "--plan-hash", preview["plan_hash"]])
    assert code == 2 and not result["applied"]
    assert contents(project.parent) == before


def test_cli_stale_rollback_receipt_preserves_external_changes(sandbox, capsys):
    home, project = sandbox
    args = ["integrate", "gemini", "--scope", "project"]
    preview_and_apply(capsys, [*args, "--store-name", "fixture"])
    path = config_path("gemini", "project", project, home)
    data = json.loads(path.read_bytes())
    data["external"] = "preserve"
    path.write_bytes(raw(data))
    before = contents(project.parent)
    code, result = cli_result(capsys, [*args, "--rollback"])
    assert code == 2 and "stale rollback" in result["selected_integrations"][0]["error"]
    assert contents(project.parent) == before


def test_cli_receipt_failure_rolls_back_config_and_owner(sandbox, capsys, monkeypatch):
    from tessera import integration_files as files
    home, project = sandbox
    args = ["integrate", "gemini", "--scope", "project", "--store-name", "fixture"]
    code, preview = cli_result(capsys, args)
    original = files._replace
    def fail_receipt(path, expected, desired):
        if path.name.endswith("-undo.json"):
            raise OSError("fixture receipt failure")
        return original(path, expected, desired)
    monkeypatch.setattr(files, "_replace", fail_receipt)
    before = contents(project.parent)
    code, result = cli_result(capsys, [*args, "--apply", "--plan-hash", preview["plan_hash"]])
    assert code == 2 and not result["applied"]
    assert "no partial writes" in result["error"]
    assert contents(project.parent) == before


def test_guided_apply_and_rollback_share_direct_hash_core(sandbox, capsys):
    args = ["--scope", "project", "--store-name", "fixture"]
    code, direct = cli_result(capsys, ["integrate", "gemini", *args])
    code, guided = cli_result(capsys, ["mcp", "setup", "--runtime", "gemini", *args])
    assert direct["plan_hash"] == guided["plan_hash"]
    code, applied = cli_result(capsys, ["mcp", "setup", "--runtime", "gemini", *args,
                                       "--apply", "--plan-hash", direct["plan_hash"]])
    assert code == 0 and applied["applied_integrations"] == ["gemini"]
    preview_and_apply(capsys, ["mcp", "setup", "--runtime", "gemini", "--scope", "project", "--rollback"])


def test_copilot_schema_precedence_and_native_scope(sandbox, capsys):
    home, project = sandbox
    base = ["integrate", "copilot", "--store-name", "fixture"]
    code, user = cli_result(capsys, [*base, "--scope", "user"])
    assert code == 0
    target = user["selected_integrations"][0]
    assert target["native_cli_candidate"] == ["copilot", "mcp", "add", "tessera", "--", "tessera-mcp", "--global", "fixture"]
    assert target["planned_mutations"][0]["after"]["type"] == "local"
    code, planned = cli_result(capsys, [*base, "--scope", "project"])
    assert planned["selected_integrations"][0]["native_cli_candidate"] is None
    (project / ".mcp.json").write_bytes(raw({"mcpServers": {"tessera": {"command": "fixture"}}}))
    code, blocked = cli_result(capsys, [*base, "--scope", "project"])
    assert code == 2 and "precedence" in blocked["selected_integrations"][0]["error"]


def test_codex_native_plan_is_pinned_argv_only_and_never_runs_clients(sandbox, capsys, monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("actual provider execution is forbidden"))
    base = ["integrate", "codex", "--scope", "user", "--store-name", "fixture"]
    code, result = cli_result(capsys, base)
    assert code == 0
    plan = result["selected_integrations"][0]
    assert plan["strategy"] == "native-command-plan"
    assert plan["native_cli_candidate"] == ["codex", "mcp", "add", "tessera", "--", "tessera-mcp", "--global", "fixture"]
    assert plan["native_rollback_candidate"] == ["codex", "mcp", "remove", "tessera"]
    code, applied = cli_result(capsys, [*base, "--apply", "--plan-hash", result["plan_hash"]])
    assert code == 2 and not applied["applied"]
    assert "native-command plans" in applied["error"]


def test_codex_owned_remove_plan_preserves_unrelated_toml(sandbox, capsys):
    import hashlib
    from tessera.integration_setup import OWNER_SCHEMA
    home, project = sandbox
    path = config_path("codex", "user", project, home)
    path.parent.mkdir()
    data = b'model = "fixture-model"\n# preserved comment\n[mcp_servers.tessera]\ncommand = "tessera-mcp"\nargs = ["--global", "fixture"]\n'
    path.write_bytes(data)
    entry = {"command": "tessera-mcp", "args": ["--global", "fixture"]}
    canonical = (json.dumps(entry, ensure_ascii=False, indent=2) + "\n").encode()
    owner = {"schema_version": OWNER_SCHEMA, "runtime": "codex", "scope": "user", "entry_sha256": hashlib.sha256(canonical).hexdigest(), "created_file": False, "created_servers": False}
    ownership_path(path, "codex", "user").write_bytes(raw(owner))
    code, result = cli_result(capsys, ["integrate", "codex", "--scope", "user", "--remove"])
    assert code == 0
    assert result["selected_integrations"][0]["native_cli_candidate"] == ["codex", "mcp", "remove", "tessera"]
    assert path.read_bytes() == data


def test_cli_receipt_never_contains_unrelated_credentials_and_refuses_unknown_fields(sandbox, capsys):
    from tessera.integration_cli import receipt_path
    home, project = sandbox
    path = config_path("gemini", "project", project, home)
    path.parent.mkdir()
    path.write_bytes(raw({"credentials": "synthetic-secret-value"}))
    args = ["integrate", "gemini", "--scope", "project"]
    preview_and_apply(capsys, [*args, "--store-name", "fixture"])
    undo = receipt_path(path, "gemini", "project")
    assert b"synthetic-secret-value" not in undo.read_bytes()
    data = json.loads(undo.read_bytes())
    data["prior_entry"] = {"command": "tessera-mcp", "args": ["--global", 42]}
    undo.write_bytes(raw(data))
    code, output = cli_result(capsys, [*args, "--rollback"])
    assert code == 2 and output["selected_integrations"][0]["status"] == "blocked"


def test_cli_group_collision_is_in_preview_and_blocks_every_write(sandbox, capsys):
    home, project = sandbox
    args = ["mcp", "setup", "--runtime", "claude", "--runtime", "copilot",
            "--scope", "project", "--store-name", "fixture"]
    code, preview = cli_result(capsys, args)
    assert code == 2
    assert all(target["status"] == "blocked" for target in preview["selected_integrations"])
    before = contents(project.parent)
    code, output = cli_result(capsys, [*args, "--apply", "--plan-hash", preview["plan_hash"]])
    assert code == 2 and not output["applied"]
    assert contents(project.parent) == before


def test_filesystem_in_process_rollback_includes_cli_receipt(tmp_path):
    from tessera.integration_files import FileSnapshot, apply_file_plan, rollback_file_plan
    plan = fixture_file_plan(tmp_path)
    extra = (plan.config_path.with_name("fixture-undo.json"), FileSnapshot(None, None), FileSnapshot(b'{}', 0o600))
    receipt = apply_file_plan(plan, extra_changes=(extra,))
    assert extra[0].is_file()
    rollback_file_plan(receipt)
    assert not list(tmp_path.rglob("*"))


def test_cli_replay_after_apply_is_stale_and_noop_requires_fresh_hash(sandbox, capsys):
    home, project = sandbox
    args = ["integrate", "gemini", "--scope", "project", "--store-name", "fixture"]
    preview, _ = preview_and_apply(capsys, args)
    before = contents(project.parent)
    code, output = cli_result(capsys, [*args, "--apply", "--plan-hash", preview["plan_hash"]])
    assert code == 2 and "stale" in output["error"]
    assert contents(project.parent) == before
    _, result = preview_and_apply(capsys, args)
    assert result["selected_integrations"][0]["operation"] == "noop"
    assert contents(project.parent) == before


def test_copilot_documented_bare_shape_preserves_unrelated_servers():
    bare = DocumentState(raw({"other": {"type": "local", "command": "fixture"}}))
    plan = build_plan(install("copilot"), bare)
    assert plan.server_path == "/tessera"
    assert "mcpServers" not in json.loads(plan.after.config)
    assert json.loads(plan.after.config)["other"] == json.loads(bare.config)["other"]
    removed = build_plan(SetupRequest("copilot", "project", remove=True), plan.after)
    assert json.loads(removed.after.config) == json.loads(bare.config)


def test_cli_subprocess_cross_process_apply_and_rollback(tmp_path):
    import os
    import subprocess
    import sys
    home, root = tmp_path / "home", tmp_path / "project"
    home.mkdir(); root.mkdir()
    env = dict(os.environ)
    for key in ("CODEX_HOME", "GEMINI_CLI_HOME", "CLAUDE_CONFIG_DIR", "COPILOT_HOME"):
        env.pop(key, None)
    base = [sys.executable, "-m", "tessera.cli", "integrate", "copilot", "--scope", "user",
            "--project-root", str(root), "--config-home", str(home), "--json"]
    def run(flags):
        output = subprocess.run([*base, *flags], env=env, capture_output=True, text=True, check=True)
        return json.loads(output.stdout)
    plan = run(["--store-name", "fixture"])
    assert run(["--store-name", "fixture", "--apply", "--plan-hash", plan["plan_hash"]])["applied"]
    undo = run(["--rollback"])
    assert run(["--rollback", "--apply", "--plan-hash", undo["plan_hash"]])["applied"]
    assert not (home / ".copilot" / "mcp-config.json").exists()


def test_copilot_bare_cli_apply_remove_and_semantic_rollback(sandbox, capsys):
    home, project = sandbox
    path = config_path("copilot", "project", project, home)
    path.parent.mkdir()
    original = {"other": {"type": "local", "command": "fixture"}}
    path.write_bytes(raw(original))
    args = ["integrate", "copilot", "--scope", "project"]
    preview_and_apply(capsys, [*args, "--store-name", "fixture"])
    assert "mcpServers" not in json.loads(path.read_bytes())
    preview_and_apply(capsys, [*args, "--remove"])
    assert json.loads(path.read_bytes()) == original
    preview_and_apply(capsys, [*args, "--rollback"])
    assert "tessera" in json.loads(path.read_bytes()) and "mcpServers" not in json.loads(path.read_bytes())


def test_guided_sequential_failure_reports_completed_targets(sandbox, capsys, monkeypatch):
    from tessera import integration_files as files
    home, project = sandbox
    args = ["mcp", "setup", "--runtime", "gemini", "--runtime", "claude",
            "--scope", "user", "--store-name", "fixture"]
    code, preview = cli_result(capsys, args)
    assert code == 0
    original = files._replace
    claude = config_path("claude", "user", project, home)
    def fail_later(path, before, after):
        if path == claude:
            raise OSError("fixture second-target failure")
        return original(path, before, after)
    monkeypatch.setattr(files, "_replace", fail_later)
    code, result = cli_result(capsys, [*args, "--apply", "--plan-hash", preview["plan_hash"]])
    assert code == 2 and result["applied_integrations"] == ["gemini"]
    assert config_path("gemini", "user", project, home).is_file()
    assert not claude.exists()
