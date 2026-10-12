"""Renderer, terminal and machine-contract acceptance tests for #166/#119."""
from __future__ import annotations

import argparse
from dataclasses import replace
import errno
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from tessera import cli
from tessera.presentation import (
    CommandResult, JsonRenderer, OutputPolicy, PlainRenderer, RichRenderer,
    UiEvent, event, human_lines, output_policy,
)


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config-home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache-home"))
    monkeypatch.setenv("TESSERA_NO_UPDATE_CHECK", "1")
    monkeypatch.setenv("TERM", "xterm-256color")
    for key in ("TESSERA_STORAGE_DIR", "TESSERA_LANG", "NO_COLOR", "TESSERA_NO_COLOR", "FORCE_COLOR", "TESSERA_FORCE_COLOR"):
        monkeypatch.delenv(key, raising=False)


def invoke_json(args, capsys):
    code = cli.main([*args, "--json"])
    captured = capsys.readouterr()
    assert "\x1b" not in captured.out
    return code, json.loads(captured.out), captured.err


def init_project(root, capsys, sources="recommended"):
    root.mkdir(exist_ok=True)
    (root / "README.md").write_text("# Project\n\nAurora memory beacon.\n", encoding="utf-8")
    code, payload, _ = invoke_json([
        "init", "--project", str(root), "--store", "memories",
        "--sources", sources, "--non-interactive",
    ], capsys)
    assert code == 0
    return payload


def bytes_in(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_empty_query_and_paths_only_have_clean_stdout(tmp_path, capsys):
    code, result, stderr = invoke_json(["query", str(tmp_path / "empty"), "beacon"], capsys)
    assert code == 0 and result == [] and stderr == ""
    assert cli.main(["query", str(tmp_path / "empty"), "beacon", "--paths-only"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("arguments", [
    ["not-a-command"], ["query"], ["query", "term", "--top-n", "0"],
    ["query", "term", "--top-n", "wrong"], ["query", "term", "--unknown"],
    ["config"], ["--lang", "pt-BR"],
])
def test_invalid_usage_is_one_json_value(arguments, capsys):
    code, payload, stderr = invoke_json(arguments, capsys)
    assert code == 2 and payload["error"]["code"] == "invalid_usage"
    assert payload["error"]["suggested_command"] == "tessera --help"
    assert "Traceback" not in stderr


def test_invalid_configuration_is_actionable_in_all_modes(tmp_path, capsys):
    root = tmp_path / ".tessera"
    root.mkdir()
    (root / "config.yaml").write_text("schema_version: 999\n")
    code, payload, stderr = invoke_json([], capsys)
    assert code == 2 and payload["error"]["code"] == "configuration_error"
    assert payload["error"]["suggested_command"] == "tessera config doctor"
    assert stderr == ""
    assert cli.main(["--plain"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "How to fix" in captured.err
    assert "Traceback" not in captured.err


def test_dashboard_is_read_only_and_reports_stale_state(tmp_path, capsys, monkeypatch):
    before = bytes_in(tmp_path)
    code, result, _ = invoke_json([], capsys)
    assert code == 0 and not result["configured"]
    assert bytes_in(tmp_path) == before
    init_project(tmp_path, capsys)
    before = bytes_in(tmp_path)
    # Dashboard must not construct an Engine, make a network request, or rebuild.
    monkeypatch.setattr(cli, "TesseraEngine", lambda **_: pytest.fail("dashboard constructed engine"))
    code, result, _ = invoke_json(["status"], capsys)
    assert code == 0 and result["configured"]
    assert result["sources"] == 1 and result["source_files_modified"] == 0
    assert bytes_in(tmp_path) == before
    (tmp_path / "README.md").write_text("Changed Aurora memory beacon.\n")
    before = bytes_in(tmp_path)
    _, result, _ = invoke_json([], capsys)
    assert result["index_status"] == "needs attention"
    assert bytes_in(tmp_path) == before


@pytest.mark.parametrize("command", [
    ["index"], ["query", "Aurora"], ["list"], ["stats"], ["doctor"],
    ["corpus", "doctor"], ["config", "show"], ["config", "list"],
    ["config", "doctor"], ["skills", "list"], ["skills", "install"],
    ["quickstart"], ["banner"], ["--version"], ["update", "--check"],
    ["write", "--id", "project/note", "--type", "factual", "--episode", "fixture", "--content", "A safe Aurora memory."],
])
def test_every_current_command_has_machine_output(command, tmp_path, capsys):
    init_project(tmp_path, capsys)
    code, payload, _ = invoke_json(command, capsys)
    assert code == 0
    assert isinstance(payload, (list, dict))


@pytest.mark.parametrize("argv", [["--json", "skills", "list"], ["skills", "--json", "list"], ["skills", "list", "--json"]])
def test_flags_work_at_each_group_level(argv, capsys):
    assert cli.main(argv) == 0
    assert len(json.loads(capsys.readouterr().out)) == 5


def test_parser_inventory_has_uniform_output_flags():
    def walk(parser):
        assert {"--plain", "--json", "--no-color", "--quiet", "--verbose", "--debug", "--lang"} <= set(parser._option_string_actions)
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for child in action.choices.values():
                    walk(child)
    walk(cli.build_parser())


def test_json_help_is_valid_json(capsys):
    with pytest.raises(SystemExit) as stopped:
        cli.main(["query", "--help", "--json"])
    assert stopped.value.code == 0
    assert "--full" in json.loads(capsys.readouterr().out)["help"]


@pytest.mark.parametrize("failure,code,category", [
    (PermissionError("fixture denied"), 4, "filesystem_error"),
    (RuntimeError("private internal detail"), 70, "internal_error"),
    (KeyboardInterrupt(), 130, "cancelled"),
])
def test_operational_errors_and_debug(failure, code, category, capsys, monkeypatch):
    def fail(_):
        raise failure
    monkeypatch.setattr(cli, "cmd_skills_list", fail)
    status, payload, err = invoke_json(["skills", "list"], capsys)
    assert status == code and payload["error"]["code"] == category
    assert "Traceback" not in err and "private internal detail" not in json.dumps(payload)
    status, payload, err = invoke_json(["skills", "list", "--debug"], capsys)
    assert status == code and "Traceback" in err


def test_provider_missing_is_actionable_without_traceback(tmp_path, capsys):
    code, result, err = invoke_json(["start", str(tmp_path / "empty"), "task"], capsys)
    assert code == 5 and result["error"]["code"] == "provider_missing"
    assert "Traceback" not in err


def test_json_warnings_do_not_pollute_result(capsys, monkeypatch):
    original = cli.cmd_skills_list
    def with_warning(args):
        event(UiEvent("source.warning", level="warning", fields={"path": "malformed.md"}))
        return original(args)
    monkeypatch.setattr(cli, "cmd_skills_list", with_warning)
    code, result, err = invoke_json(["skills", "list", "--quiet"], capsys)
    assert code == 0 and len(result) == 5
    assert "warning" in err and "malformed.md" in err


def test_output_policy_color_layout_and_pipe_rules(monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    colored = OutputPolicy.detect()
    assert colored.mode == "rich" and colored.color
    monkeypatch.setenv("NO_COLOR", "")
    uncolored = OutputPolicy.detect()
    assert uncolored.mode == "rich" and not uncolored.color
    plain = OutputPolicy.detect(argparse.Namespace(plain=True))
    assert plain.mode == "plain" and not plain.color
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert OutputPolicy.detect().mode == "plain"


def hits(count):
    return [{"id": f"project/note-{i}", "type": "factual", "score": 0.7,
             "filepath": f"docs/note-{i}.md", "relevant_evidence": "An Aurora memory.",
             "body": "The complete memory body. " * 30, "score_explain": {"lexical_score": 0.7, "raw_pagerank": 0.25},
             "related_ids": ["project/other"]} for i in range(count)]


@pytest.mark.parametrize("count", [1, 3, 20])
@pytest.mark.parametrize("width", [60, 80, 120])
def test_renderers_share_semantics_and_rich_respects_width(count, width, capsys):
    data = hits(count)
    original = json.dumps(data, sort_keys=True)
    result = CommandResult("query", data)
    output = OutputPolicy(width=width, mode="rich", color=False)
    RichRenderer(output).render(result)
    rich = capsys.readouterr().out
    PlainRenderer(replace(output, mode="plain")).render(result)
    plain = capsys.readouterr().out
    JsonRenderer().render(result)
    structured = json.loads(capsys.readouterr().out)
    assert structured == data and json.dumps(data, sort_keys=True) == original
    assert " ".join(rich.split()) == " ".join(plain.split())
    assert all(len(line) <= width for line in rich.splitlines())
    assert "Relevance score" not in rich and "complete memory body" not in rich
    full = list(human_lines(result, replace(output, full=True, explain=True, show_related=True)))
    assert data[0]["body"] in full
    assert any("not confidence" in line for line in full)
    assert any("raw_pagerank:" in line for line in full)
    assert any("project/other" in line for line in full)


def test_terminal_control_sequences_are_literal_data_only_in_json(capsys):
    result = CommandResult("query", [{**hits(1)[0], "id": "[red]hostile\x1b[2J", "relevant_evidence": "safe\x1b]0;hostile-title\x07 text"}])
    for renderer in (PlainRenderer(), RichRenderer(OutputPolicy(mode="rich", width=60))):
        renderer.render(result)
        text = capsys.readouterr().out
        assert "\x1b" not in text and "hostile-title" not in text
        assert "[red]hostile" in text
    JsonRenderer().render(result)
    assert json.loads(capsys.readouterr().out) == result.data


def test_ascii_fallback_and_json_preserve_content(capsys):
    result = CommandResult("query", [{**hits(1)[0], "relevant_evidence": "café 日本"}])
    PlainRenderer(OutputPolicy(unicode=False)).render(result)
    assert capsys.readouterr().out.isascii()
    JsonRenderer().render(result)
    assert json.loads(capsys.readouterr().out)[0]["relevant_evidence"] == "café 日本"


def test_existing_init_keep_and_cancel_preserve_configuration(tmp_path, capsys, monkeypatch):
    init_project(tmp_path, capsys, sources="memory-only")
    config = tmp_path / ".tessera" / "config.yaml"
    before = config.read_bytes()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    answers = iter(["1", "yes"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert cli.main(["init", "--project", str(tmp_path), "--plain"]) == 0
    output = capsys.readouterr().out
    assert "already has TESSERA configured" in output and "Index rebuilt" in output
    assert config.read_bytes() == before
    state = bytes_in(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "3")
    assert cli.main(["init", "--project", str(tmp_path), "--plain"]) == 1
    assert "cancelled" in capsys.readouterr().out
    assert bytes_in(tmp_path) == state


def test_dry_run_and_yes_do_not_bypass_explicit_scope(tmp_path, capsys):
    code, result, _ = invoke_json(["init", "--project", str(tmp_path), "--yes"], capsys)
    assert code == 2 and result["error"]["code"] == "invalid_usage"
    code, result, _ = invoke_json(["init", "--project", str(tmp_path), "--yes", "--non-interactive"], capsys)
    assert code == 2 and "requires --sources" in result["error"]["message"]
    before = bytes_in(tmp_path)
    code, result, _ = invoke_json(["init", "--project", str(tmp_path), "--sources", "memory-only", "--yes", "--non-interactive", "--dry-run"], capsys)
    assert code == 0 and not result["applied"]
    assert bytes_in(tmp_path) == before


def test_lang_is_explicit_and_does_not_leak_between_invocations(capsys, monkeypatch):
    monkeypatch.setenv("TESSERA_LANG", "pt-BR")
    assert invoke_json([], capsys)[0] == 2
    assert invoke_json(["--lang", "en"], capsys)[0] == 0
    assert invoke_json([], capsys)[0] == 2


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX PTY fixture")
@pytest.mark.parametrize("width,flags,colored", [(60, [], True), (80, ["--no-color"], False), (120, ["--plain"], False), (60, ["--json"], False)])
def test_real_pty_dashboard(width, flags, colored, tmp_path):
    import fcntl
    import pty
    import select
    import struct
    import termios
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, width, 0, 0))
    process = subprocess.Popen([sys.executable, "-m", "tessera.cli", *flags], cwd=tmp_path,
                               stdin=slave, stdout=slave, stderr=subprocess.PIPE)
    os.close(slave)
    output = bytearray()
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
        assert process.wait(timeout=5) == 0
        text = output.decode()
        assert ("\x1b[" in text) is colored
        if "--json" in flags:
            assert json.loads(text)["configured"] is False
        else:
            assert "not configured" in text and "tessera init" in text
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX PTY fixture")
def test_real_pty_init_sigint_cancels_before_mutation(tmp_path):
    import pty
    import select
    # A controlling PTY delivers the actual terminal Ctrl+C to the foreground
    # process group, rather than racing a synthetic signal against input().
    pid, master = pty.fork()
    if pid == 0:
        os.chdir(tmp_path)
        os.execv(sys.executable, [sys.executable, "-m", "tessera.cli", "init", "--plain"])
    output = bytearray()
    reaped = False
    try:
        deadline = time.monotonic() + 20
        while b"Selection [1]:" not in output and time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                output.extend(os.read(master, 65536))
        assert b"Selection [1]:" in output
        os.write(master, b"\x03")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            waited, status = os.waitpid(pid, os.WNOHANG)
            if waited:
                reaped = True
                assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 1
                break
            if select.select([master], [], [], 0.1)[0]:
                try:
                    output.extend(os.read(master, 65536))
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
        assert reaped, output.decode(errors="replace")
        while select.select([master], [], [], 0)[0]:
            try:
                chunk = os.read(master, 65536)
            except OSError as exc:
                if exc.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            output.extend(chunk)
        assert b"cancelled" in output
        assert not (tmp_path / ".tessera").exists()
        assert not (tmp_path / "memories").exists()
    finally:
        if not reaped:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(master)


def test_stage_is_delayed_and_cleans_up_after_cancellation(capsys):
    from tessera.presentation import stage
    with output_policy(OutputPolicy()):
        with stage("progress.index", delay=0.05):
            pass
        time.sleep(0.07)
        assert capsys.readouterr().err == ""
        with pytest.raises(KeyboardInterrupt):
            with stage("progress.index", delay=0.01):
                time.sleep(0.03)
                raise KeyboardInterrupt()
        assert capsys.readouterr().err.count("Updating index") == 1
        time.sleep(0.03)
        assert capsys.readouterr().err == ""


def test_provider_runtime_failure_has_stable_category(capsys, monkeypatch, tmp_path):
    def fail(*_):
        raise TimeoutError("private provider reply")
    monkeypatch.setattr("tessera.llm_bridge.resolve_llm_fn", lambda **_: (fail, "fixture"))
    code, payload, stderr = invoke_json(["start", str(tmp_path / "empty"), "task"], capsys)
    assert code == 5 and payload["error"]["code"] == "provider_failure"
    assert "private provider reply" not in json.dumps(payload) and stderr == ""


def test_ascii_only_real_subprocess_is_parseable(tmp_path):
    env = {**os.environ, "PYTHONIOENCODING": "ascii"}
    completed = subprocess.run([sys.executable, "-m", "tessera.cli", "banner", "--json"],
                               cwd=tmp_path, env=env, capture_output=True, text=True)
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["name"] == "TESSERA"
    completed = subprocess.run([sys.executable, "-m", "tessera.cli", "banner", "--plain"],
                               cwd=tmp_path, env=env, capture_output=True, text=True)
    assert completed.returncode == 0 and completed.stdout.isascii()


def test_legacy_domain_warning_is_safe_and_json_stays_parseable(tmp_path, capsys):
    store = tmp_path / "store"
    store.mkdir()
    (store / "bad\x1b[2J.md").write_text("---\ntags: [unterminated\n---\nBody")
    code, payload, err = invoke_json(["query", str(store), "body"], capsys)
    assert code == 0 and payload == []
    assert "Failed to process" in err and "\x1b" not in err


def test_assisted_and_decomposition_json_preserve_complete_domain_results(tmp_path, capsys, monkeypatch):
    init_project(tmp_path, capsys)
    monkeypatch.setattr("tessera.llm_bridge.resolve_llm_fn", lambda **_: (lambda *args: "Aurora", "fixture"))
    code, result, _ = invoke_json(["start", "Aurora"], capsys)
    assert code == 0 and result["raw_memories"]
    assert result["raw_memories"][0]["body"] and result["consolidated_context"] == "Aurora"
    monkeypatch.setattr("tessera.llm_bridge.resolve_llm_fn", lambda **_: (lambda *args: '[]', "fixture"))
    code, result, _ = invoke_json(["decompose", "--mem-id-prefix", "project/episode", "--beginning", "goal", "--middle", "work", "--end", "done"], capsys)
    assert code == 0 and "filepaths" in result and "decomposition" in result


def test_dashboard_honors_environment_precedence_without_inventing_project(tmp_path, capsys, monkeypatch):
    init_project(tmp_path, capsys)
    env_store = tmp_path / "environment-store"
    monkeypatch.setenv("TESSERA_STORAGE_DIR", str(env_store))
    before = bytes_in(tmp_path)
    code, result, _ = invoke_json(["status"], capsys)
    assert code == 0 and result["configuration_source"] == "environment"
    assert result["project"] is None and result["config_path"] is None
    assert result["storage_dir"] == str(env_store)
    assert bytes_in(tmp_path) == before and not env_store.exists()
