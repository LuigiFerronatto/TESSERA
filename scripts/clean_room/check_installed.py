"""Run against an installed wheel, from an unrelated directory (stdlib driver).

Every product operation uses the installed console script. Python probes only
inspect installed metadata/configuration/index membership and time discovery.
No pytest, source checkout imports, provider credentials or network are used.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import traceback


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root):
    """Full lstat inventory: never follow links or read FIFO/device contents."""
    result = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        mode = info.st_mode
        kind = stat.S_IFMT(mode)
        content = (os.readlink(path) if stat.S_ISLNK(mode) else
                   digest(path) if stat.S_ISREG(mode) else None)
        result[path.relative_to(root).as_posix()] = [kind, stat.S_IMODE(mode), content, info.st_mtime_ns]
    return result


class Experiment:
    def __init__(self, root, fixture, output, tty):
        self.root, self.output, self.tty = root, output, tty
        self.files = json.loads(fixture.read_text())
        self.cli = str(Path(sys.executable).parent / ("tessera.exe" if os.name == "nt" else "tessera"))
        self.commands, self.cases, self.integrity = [], {}, []
        self.env = dict(os.environ)
        self.env.update(HOME=str(root / "home"), XDG_CONFIG_HOME=str(root / "xdg"),
                        APPDATA=str(root / "appdata"), NO_COLOR="1", TERM="dumb",
                        PYTHONDONTWRITEBYTECODE="1", TESSERA_CLEAN_ROOM_OFFLINE="1",
                        TESSERA_CLEAN_ROOM_AUDIT_LOG=str(output.parent / "forbidden-events.log"))
        (root / "home").mkdir()
        (root / "home" / "must-not-scan.md").write_text("Homebeacon must never enter a project.\n")
        self.baseline = {}

    def fixture(self, name):
        project = self.root / name
        project.mkdir()
        for name, text in self.files.items():
            path = project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        outside = self.root / "outside"
        outside.mkdir(exist_ok=True)
        (outside / "outside.md").write_text("Escapebeacon must never enter a project.\n")
        if os.name != "nt":
            (project / "external-link").symlink_to(outside, target_is_directory=True)
            (project / "internal-link.md").symlink_to(project / "README.md")
            os.mkfifo(project / "special.md")
        self.baseline[str(project)] = {
            name: digest(project / name) for name in self.files
            if not name.startswith(".tessera/index/") and name != ".tessera-ignore"
        }
        return project

    def source_check(self, project, stage):
        expected = self.baseline[str(project)]
        actual = {name: digest(project / name) for name in expected}
        assert actual == expected, (stage, actual, expected)
        self.integrity.append({"project": project.name, "stage": stage, "modified": 0,
                               "sha256": actual})

    def run(self, project, args, code=0, parse=False):
        start = time.monotonic()
        p = subprocess.run([self.cli, *args], cwd=project, env=self.env,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        self.commands.append({"cwd": str(project), "args": args, "code": p.returncode,
                              "seconds": time.monotonic() - start,
                              "stdout": p.stdout, "stderr": p.stderr})
        assert p.returncode == code, self.commands[-1]
        self.source_check(project, " ".join(args[:2]))
        return json.loads(p.stdout) if parse else p.stdout

    def init(self, project, *extra, mode="recommended", code=0):
        return self.run(project, ["init", "--project", ".", "--store", "memories/generated",
                                 "--sources", mode, "--non-interactive", "--json", *extra],
                        code=code, parse=True)

    def config(self, project):
        import yaml
        return yaml.safe_load((project / ".tessera/config.yaml").read_text())

    def membership(self, project):
        # Read the persisted index through the installed Engine. No product
        # operation is substituted by this observation probe.
        probe = """
import json
from tessera.config import ConfigurationResolver
from tessera import TesseraEngine
e = TesseraEngine(configuration=ConfigurationResolver(environ={}).resolve())
e.build_index()
print(json.dumps({'files': sorted(e.file_registry.values()), 'nodes': e.graph.number_of_nodes(), 'relations': e.graph.number_of_edges()}))
"""
        p = subprocess.run([sys.executable, "-c", probe], cwd=project, env=self.env,
                           capture_output=True, text=True, timeout=60, check=True)
        data = json.loads(p.stdout)
        data["files"] = [Path(x).relative_to(project).as_posix() for x in data["files"]]
        return data

    def query(self, project):
        result = self.run(project, ["query", "what is this project?", "--json", "--top-n", "5"], parse=True)
        assert result and "Aster Observatory" in result[0]["body"], result
        for row in result:
            assert Path(row["filepath"]).is_relative_to(project)
        assert result[0]["relevant_evidence"] and result[0]["evidence_info"]
        return result

    @staticmethod
    def evidence(rows):
        return [{k: r.get(k) for k in ("id", "relevant_evidence", "evidence_info", "source", "provenance")}
                for r in rows]

    def interactive(self, project, choices, code=0):
        """Drive real input() via a controlling PTY; bound reads and reap child."""
        import errno
        import pty
        import select
        import signal
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(project)
            os.execve(self.cli, [self.cli, "init", "--plain"], self.env)
        chunks, pending, step = b"", b"", 0
        before = snapshot(project)
        deadline = time.monotonic() + 60
        status = None
        try:
            while time.monotonic() < deadline:
                if select.select([fd], [], [], .1)[0]:
                    try:
                        chunk = os.read(fd, 65536)
                    except OSError as exc:
                        if exc.errno == errno.EIO:
                            break
                        raise
                    if not chunk:
                        break
                    chunks += chunk
                    pending += chunk
                    if step < len(choices) and choices[step][0].encode() in pending:
                        # No canonical mutation before confirmation/cancellation.
                        assert snapshot(project) == before
                        os.write(fd, choices[step][1])
                        step += 1
                        pending = b""
            else:
                raise AssertionError("installed TTY timed out: " + chunks.decode(errors="replace"))
            _, status = os.waitpid(pid, 0)
            assert os.waitstatus_to_exitcode(status) == code, chunks.decode(errors="replace")
            assert step == len(choices)
        finally:
            os.close(fd)
            if status is None:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
        transcript = chunks.decode(errors="replace")
        self.commands.append({"cwd": str(project), "args": ["init", "--plain"],
                              "tty": True, "stdout": transcript, "code": code})
        self.source_check(project, "interactive")
        return transcript

    def exercise(self):
        import tessera
        from importlib import resources
        origin = Path(tessera.__file__).resolve()
        assert "site-packages" in origin.parts
        assert origin.is_relative_to(Path(sys.prefix))
        assert importlib.metadata.version("tessera") == tessera.__version__
        for name in ("openai", "anthropic", "google.generativeai", "requests", "mcp"):
            try:
                spec = importlib.util.find_spec(name)
            except ModuleNotFoundError:
                spec = None
            assert spec is None, name
        scripts = {e.name: e.value for e in importlib.metadata.distribution("tessera").entry_points}
        assert scripts == {"tessera": "tessera.cli:main", "tessera-mcp": "tessera.mcp_server:main"}
        self.cases["installation"] = {
            "origin": str(origin), "version": tessera.__version__, "python": sys.version,
            "entry_points": scripts, "requires": importlib.metadata.requires("tessera"),
            "package_data": sorted(x.name for x in resources.files("tessera").joinpath("skills_library").iterdir()),
        }
        project = self.fixture("fixture-project")
        discovery_probe = """
import json, time
from tessera.source_discovery import discover_sources
start = time.perf_counter()
plan = discover_sources('.')
print(json.dumps({'seconds': time.perf_counter() - start, 'metrics': plan.metrics, 'totals': plan.totals}))
"""
        measured = subprocess.run([sys.executable, "-c", discovery_probe], cwd=project,
                                  env=self.env, capture_output=True, text=True, check=True, timeout=60)
        self.cases["discovery_metrics"] = json.loads(measured.stdout)
        self.run(project, ["init", "--help"])
        entire = snapshot(self.root)
        dry = self.init(project, "--dry-run")
        assert not dry["applied"] and snapshot(self.root) == entire
        human = self.run(project, ["init", "--project", ".", "--store", "memories/generated",
                                   "--sources", "recommended", "--non-interactive", "--dry-run", "--plain"])
        assert "Source files modified: 0" in human and snapshot(self.root) == entire
        self.cases["dry_run"] = {"full_filesystem_mutations": 0, "plan": dry["plan"]}
        missing = self.run(project, ["init", "--project", ".", "--non-interactive", "--json"], code=2, parse=True)
        assert "requires --sources" in missing["error"]["message"] and snapshot(self.root) == entire
        applied = self.init(project)
        assert applied["applied"] and applied["plan"] == dry["plan"]
        selected = ["AGENTS.md", "README.md", "docs/architecture.md", "docs/nested/keep.md",
                    "memories/existing-learning.md", "research/market-notes.md"]
        selected.sort(key=lambda x: (x.casefold(), x))
        assert applied["plan"]["sources"]["selected"] == selected
        assert self.membership(project)["files"] == sorted(selected)
        cfg = self.config(project)
        assert cfg["schema_version"] == 2
        assert cfg["store"]["path"] == "memories/generated"
        assert cfg["index"]["path"] == ".tessera/index"
        assert cfg["sources"]["roots"] == [
            {"path": "memories/generated", "include": ["**/*.md"]},
            {"path": ".", "include": selected}]
        self.cases["noninteractive"] = {"result": applied, "config": cfg}
        # Index/query/doctor read project sources but may write only declared
        # generated/derived destinations. Read-only files remain indexable.
        for name in selected:
            (project / name).chmod(0o444)
        self.run(project, ["doctor", "--plain"])
        assert not (project / "memories/generated/.tessera_index").exists()
        diagnostic = self.run(project, ["config", "doctor", "--json"], parse=True)
        self.run(project, ["index", "--plain"])
        before_query = self.query(project)
        before_config = (project / ".tessera/config.yaml").read_bytes()
        repeated = self.init(project)
        assert not repeated["plan"]["planned_mutations"]["config"]
        assert repeated["plan"]["config_changes"] == []
        assert (project / ".tessera/config.yaml").read_bytes() == before_config
        assert repeated["plan"]["sources"]["selected"] == selected
        assert self.membership(project)["files"] == sorted(selected)
        self.cases["idempotency"] = repeated
        self.run(project, ["write", "--id", "project/calibration", "--type", "factual", "--episode", "fixture",
                           "--content", "Cedar calibration completed locally.", "--json"], parse=True)
        self.run(project, ["write", "--id", "../docs/illegal", "--type", "factual", "--episode", "fixture",
                           "--content", "Must not write to a source root.", "--json"], code=2, parse=True)
        generated = list((project / "memories/generated").rglob("*.md"))
        assert len(generated) == 1
        generated_hash = {str(x.relative_to(project)): digest(x) for x in generated}
        self.run(project, ["index", "--plain"])
        before_query = self.query(project)
        before_membership = self.membership(project)
        shutil.rmtree(project / ".tessera/index")
        self.source_check(project, "delete derived index")
        assert (project / ".tessera/config.yaml").read_bytes() == before_config
        self.run(project, ["index", "--plain"])
        after_query = self.query(project)
        assert self.evidence(before_query) == self.evidence(after_query), (before_query, after_query)
        assert before_membership == self.membership(project)
        assert {str(x.relative_to(project)): digest(x) for x in generated} == generated_hash
        self.cases["rebuild"] = {"before": before_query, "after": after_query, "membership": before_membership}
        self.cases["diagnostics"] = diagnostic
        for mode, extra, expected in [
            ("custom", ["--source", "examples", "--source", "docs"],
             ["docs/architecture.md", "docs/nested/keep.md", "examples/optional.md"]),
            ("memory-only", [], []),
        ]:
            p = self.fixture(mode)
            result = self.init(p, *extra, mode=mode)
            assert result["plan"]["sources"]["selected"] == expected
            assert self.membership(p)["files"] == sorted(expected)
            assert (p / ".tessera-ignore").read_text() == self.files[".tessera-ignore"]
            self.cases[mode] = result
        self.security()
        self.migration()
        self.ignore()
        self.failures()
        if self.tty:
            self.tty_cases()
        self.global_isolation(project)
        # Move to a different parent; the old path ceases to exist.
        new_parent = self.root / "relocated-parent"
        new_parent.mkdir()
        moved = new_parent / project.name
        project.rename(moved)
        self.baseline[str(moved)] = self.baseline.pop(str(project))
        assert not project.exists()
        self.run(moved, ["doctor", "--plain"])
        self.run(moved, ["index", "--plain"])
        moved_query = self.query(moved)
        assert [r["id"] for r in moved_query] == [r["id"] for r in after_query]
        assert self.config(moved) == cfg
        assert self.membership(moved) == before_membership
        assert str(project) not in json.dumps(moved_query)
        self.cases["moved"] = {"config": self.config(moved), "query": moved_query}
        assert not Path(self.env["TESSERA_CLEAN_ROOM_AUDIT_LOG"]).exists(), "forbidden runtime operation attempted"
        return moved

    def security(self):
        p = self.fixture("security")
        before = snapshot(self.root)
        bad = [".env", "private.key", ".git", ".tessera/index", "node_modules", ".venv",
               "../outside", str(self.root / "outside")]
        if os.name != "nt":
            bad += ["external-link", "internal-link.md", "special.md"]
        for source in bad:
            self.init(p, "--source", source, mode="custom", code=2)
            assert snapshot(self.root) == before
        # Config normalization uses the same physical containment boundary.
        self.init(p)
        original = (p / ".tessera/config.yaml").read_text()
        import yaml
        for source in ["../outside", str(self.root / "outside"), "external-link"] if os.name != "nt" else ["../outside", str(self.root / "outside")]:
            data = yaml.safe_load(original)
            data["sources"]["roots"] = [{"path": source, "include": ["**/*.md"]}]
            (p / ".tessera/config.yaml").write_text(yaml.safe_dump(data))
            self.run(p, ["index", "--plain"], code=2)
        (p / ".tessera/config.yaml").write_text(original)
        self.cases["security"] = {"rejected": bad, "mutations_on_rejection": 0}

    def migration(self):
        p = self.fixture("v1")
        old = {"schema_version": 1, "store": {"id": "22222222-2222-4222-8222-222222222222", "path": "memories"}}
        import yaml
        (p / ".tessera/config.yaml").write_text(yaml.safe_dump(old))
        before = snapshot(self.root)
        args = ["init", "--project", ".", "--sources", "memory-only", "--non-interactive", "--json"]
        preview = self.run(p, args + ["--dry-run"], parse=True)
        assert preview["plan"]["sources"]["selected"] == []
        self.run(p, args, code=2, parse=True)
        assert snapshot(self.root) == before
        migrated = self.run(p, args + ["--update-existing"], parse=True)
        assert self.config(p)["store"] == old["store"]
        assert self.membership(p)["files"] == ["memories/existing-learning.md"]
        before = snapshot(self.root)
        update = self.init(p, "--dry-run")
        assert update["plan"]["config_changes"]
        self.init(p, code=2)
        assert snapshot(self.root) == before
        self.init(p, "--update-existing")
        self.cases["migration"] = {"preview": preview, "applied": migrated, "v2_update": update}

    def ignore(self):
        p = self.fixture("explicit-ignore")
        before = snapshot(self.root)
        preview = self.init(p, "--persist-exclusion", "research", "--dry-run")
        assert snapshot(self.root) == before
        applied = self.init(p, "--persist-exclusion", "research")
        assert applied["plan"] == preview["plan"]
        assert "research/\n" in (p / ".tessera-ignore").read_text()
        expected = applied["plan"]["sources"]["selected"]
        assert "research/market-notes.md" not in expected
        self.run(p, ["doctor", "--plain"])
        self.run(p, ["config", "doctor", "--json"], parse=True)
        self.run(p, ["index", "--plain"])
        assert self.membership(p)["files"] == sorted(expected)
        self.cases["ignore"] = applied

    def failures(self):
        reports = []
        for target in (".tessera", "memories/generated", ".tessera/index"):
            p = self.fixture("unwritable-" + target.replace("/", "-"))
            dest = p / target
            dest.mkdir(parents=True, exist_ok=True)
            dest.chmod(0o555)
            before = snapshot(self.root)
            try:
                failure = self.init(p, code=2)
                assert failure["error"]["code"] == "preflight_failed"
                assert snapshot(self.root) == before
                reports.append(failure)
            finally:
                dest.chmod(0o755)
            self.init(p)
        # Real filesystem obstruction forces index persistence failure after
        # successful config/store creation, without patching runtime functions.
        p = self.fixture("partial-index")
        obstruction = p / ".tessera/index/graph.pkl"
        obstruction.mkdir()
        failure = self.init(p, code=3)
        assert not failure["applied"]
        assert failure["partial_state"]["config_applied"]
        assert failure["partial_state"]["store_prepared"]
        assert not failure["partial_state"]["index_applied"]
        assert (p / ".tessera/config.yaml").is_file()
        assert (p / "memories/generated").is_dir()
        partial_files = snapshot(p / ".tessera/index")
        human = self.run(p, ["init", "--project", ".", "--store", "memories/generated",
                             "--sources", "recommended", "--non-interactive", "--plain"], code=3)
        assert "Next:" not in human and "✔ TESSERA configured" not in human
        assert "Initialization incomplete:" in self.commands[-1]["stderr"]
        obstruction.rmdir()
        recovered = self.init(p)
        self.cases["failures"] = {"preflight": reports, "partial": failure,
                                  "index_directory_preexisted": True,
                                  "partial_index_files": partial_files, "recovered": recovered}

    def tty_cases(self):
        p = self.fixture("tty")
        before = snapshot(p)
        dry = self.init(p, "--dry-run")
        prefix = [("Selection [1]:", b"1\n"), ("memories]:", b"memories/generated\n"),
                  ("Selection [1]:", b"1\n")]
        transcript = self.interactive(p, prefix + [("Proceed? [y/N]:", b"y\n")])
        for marker in ("Initialization plan:", "Scope: project", dry["plan"]["project_root"],
                       dry["plan"]["store"]["id"], dry["plan"]["index"]["path"],
                       "Ignored: " + str(dry["plan"]["sources"]["ignored_count"]),
                       "Forbidden: " + str(dry["plan"]["sources"]["forbidden_count"])):
            assert marker in transcript, marker
        assert self.config(p) == dry["plan"]["proposed_configuration"]
        assert self.membership(p)["files"] == sorted(dry["plan"]["sources"]["selected"])
        # Compare same project identity via restoring this throwaway fixture.
        tty_cfg, tty_members = self.config(p), self.membership(p)
        shutil.rmtree(p)
        p = self.fixture("tty")
        applied = self.init(p)
        assert self.config(p) == tty_cfg and self.membership(p) == tty_members
        assert applied["plan"] == dry["plan"]
        cancelled = {}
        for name, choices in [
            ("negative", prefix + [("Proceed? [y/N]:", b"n\n")]),
            ("cancel", [("Selection [1]:", b"3\n")]),
            ("selection-cancel", prefix[:2] + [("Selection [1]:", b"4\n")]),
            ("eof", [("Selection [1]:", b"\x04")]),
            ("interrupt", [("Selection [1]:", b"\x03")]),
        ]:
            p = self.fixture("tty-" + name)
            before = snapshot(p)
            whole = snapshot(self.root)
            cancelled[name] = self.interactive(p, choices, code=1)
            assert snapshot(self.root) == whole
        self.cases["tty"] = {"transcript": transcript, "same_project_config_and_membership": True,
                             "cancel_mutations": 0, "cancellations": cancelled}

    def global_isolation(self, project):
        global_store = self.root / "shared-store"
        global_store.mkdir()
        global_source = global_store / "global.md"
        global_source.write_text("# Shared source\n\nGlobalonlybeacon is intentionally shared knowledge.\n")
        args = ["init", "--global", "shared", "--store", str(global_store), "--non-interactive", "--json"]
        first = self.run(project, args, parse=True)
        local_before = snapshot(project)
        # Exercise explicit global rerun while local configuration exists.
        repeated = self.run(project, args, parse=True)
        assert repeated["result"]["indexed_sources"] == [str(global_source)]
        assert repeated["plan"]["store"] == first["plan"]["store"]
        assert snapshot(project) == local_before
        registry = self.root / "xdg/tessera/registry.yaml"
        global_before = snapshot(global_store)
        registry_before = registry.read_bytes()
        self.init(project)
        assert snapshot(global_store) == global_before and registry.read_bytes() == registry_before
        assert str(global_source) not in self.run(project, ["query", "Globalonlybeacon", "--json"])
        self.cases["global_isolation"] = {"first": first, "repeat": repeated}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--fixture", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--tty", action="store_true")
    args = ap.parse_args()
    args.root.mkdir(parents=True)
    exp = Experiment(args.root, args.fixture, args.output, args.tty)
    report = {"passed": False}
    try:
        moved = exp.exercise()
        preserved = snapshot(args.root)
        uninstall = subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "tessera"],
                                   capture_output=True, text=True, check=True, timeout=60)
        assert not Path(exp.cli).exists()
        assert not (Path(exp.cli).parent / ("tessera-mcp.exe" if os.name == "nt" else "tessera-mcp")).exists()
        probe = subprocess.run([sys.executable, "-c", "import importlib.util; assert importlib.util.find_spec('tessera') is None"],
                               cwd=moved, capture_output=True, text=True, check=True)
        assert snapshot(args.root) == preserved
        report.update(passed=True, uninstall={"stdout": uninstall.stdout, "module_and_entrypoint_removed": True,
                                             "user_files_preserved": True, "derived_index_retained": True})
    except Exception:
        report["error"] = traceback.format_exc()
        raise
    finally:
        report.update(cases=exp.cases, commands=exp.commands, source_integrity=exp.integrity,
                      fixture_sha256=digest(args.fixture))
        args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
