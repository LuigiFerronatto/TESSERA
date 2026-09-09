"""Create an external venv and run the installed-wheel contract (Python 3.9+)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
import tarfile


def run(argv, cwd, env, timeout=300):
    start = time.monotonic()
    p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    return {"seconds": time.monotonic() - start, "stdout": p.stdout, "stderr": p.stderr}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wheel", required=True, type=Path)
    ap.add_argument("--sdist", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--tty", action="store_true")
    ap.add_argument("--source-sha", required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output.resolve()
    root = Path(tempfile.mkdtemp(prefix="tessera-118-"))
    # Credential-free allowlist; no inherited store selection or PYTHONPATH.
    env = {k: v for k, v in os.environ.items() if k in {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL",
        "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE"}}
    env.update(PIP_CONFIG_FILE=os.devnull, PIP_INDEX_URL="https://pypi.org/simple",
               PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1", PYTHONDONTWRITEBYTECODE="1",
               HOME=str(root / "installer-home"), XDG_CONFIG_HOME=str(root / "installer-xdg"))
    metadata = {"source_sha": args.source_sha, "python": sys.version, "root": str(root), "artifacts": {}}
    for path in (args.wheel.resolve(), args.sdist.resolve()):
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
        else:
            with tarfile.open(path) as archive:
                names = [p.split("/", 1)[-1] for p in archive.getnames()]
        forbidden = {"tests", "benchmarks", "archive", "docs", "examples", ".github", ".venv", "venv", ".tessera", "scripts"}
        assert not [n for n in names if any(p in forbidden for p in Path(n).parts)], names
        assert not [n for n in names if Path(n).name in {".env", "private.key"}]
        assert "tessera/cli.py" in names and "tessera/init_flow.py" in names
        source_root = Path(__file__).resolve().parents[2]
        runtime_files = {p.relative_to(source_root).as_posix()
                         for p in (source_root / "tessera").glob("*.py")}
        assert runtime_files
        assert {n for n in names if n.startswith("tessera/") and n.endswith(".py")} == runtime_files
        assert len([n for n in names if n.startswith("tessera/skills_library/") and n.endswith(".md")]) == 5
        metadata["artifacts"][path.name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                             "bytes": path.stat().st_size, "inventory": names}
    venv = root / "venv"
    metadata["environment"] = run([sys.executable, "-m", "venv", str(venv)], root, env)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    metadata["install"] = run([str(python), "-m", "pip", "install", str(args.wheel.resolve())], root, env)
    metadata["installer"] = run([str(python), "-m", "pip", "--version"], root, env)
    site = Path(run([str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], root, env)["stdout"].strip())
    # Install a CI-only audit hook. It applies to the actual console executable,
    # proves network denial is active, and records attempted external scans.
    guard = '''import os, sys
if os.environ.get("TESSERA_CLEAN_ROOM_OFFLINE") == "1":
    def forbidden(message):
        log = os.environ.get("TESSERA_CLEAN_ROOM_AUDIT_LOG")
        if log:
            with open(log, "a") as stream:
                stream.write(message + "\\n")
        raise RuntimeError(message)
    def audit(event, args):
        if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.gethostbyname", "socket.sendto"}:
            forbidden("clean-room network forbidden: " + event)
        if event == "os.scandir" and args and isinstance(args[0], (str, bytes)):
            path = os.fsdecode(args[0])
            if os.path.abspath(path) == os.environ["HOME"]:
                forbidden("implicit home scan forbidden")
        if event == "import" and args[0].split(".")[0] in {"openai", "anthropic", "litellm"}:
            forbidden("provider import forbidden")
    sys.addaudithook(audit)
'''
    (site / "clean_room_audit.pth").write_text("import builtins; exec(" + repr(guard) + ", {})\n")
    offline = dict(env, TESSERA_CLEAN_ROOM_OFFLINE="1")
    metadata["offline_guard"] = run([str(python), "-c", "import socket\ntry: socket.create_connection(('127.0.0.1',9))\nexcept RuntimeError as e: print(e)\nelse: raise AssertionError('guard not active')"], root, offline)
    here = Path(__file__).parent
    shutil.copyfile(here / "check_installed.py", root / "check_installed.py")
    shutil.copyfile(here / "fixture.json", root / "fixture.json")
    command = [str(python), str(root / "check_installed.py"), "--root", str(root / "experiment"),
               "--fixture", str(root / "fixture.json"), "--output", str(output / "installed.json")]
    if args.tty:
        command.append("--tty")
    try:
        metadata["experiment"] = run(command, root, env, timeout=600)
        metadata["passed"] = True
        shutil.rmtree(root)
        metadata["temporary_state_removed"] = True
    finally:
        (output / "environment.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print("Clean-room evidence:", output, flush=True)
        print("Temporary environment:", root, flush=True)


if __name__ == "__main__":
    main()
