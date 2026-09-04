"""
Diagnostics & onboarding helpers for Tessera, shared by both the CLI
(`tessera doctor` / `tessera quickstart`) and the MCP server (`run_doctor` /
`run_quickstart` tools) — one implementation, two front-ends, so a check
added here is instantly available to a human on a terminal AND an agent
calling the MCP tool.

Implements the current project-neutral doctor and quickstart boundary:
  - `tessera doctor`: post-install smoke test (MCP config found? storage_dir
    writable? index builds without error? write+read round-trip works?)
  - `tessera quickstart`: detects the current project, proposes a storage_dir,
    generates a ready-to-paste MCP config block, and offers to run the
    first `init` + `index` automatically.

Both are read/inspect-first, mutate-only-with-explicit-consent — neither
function writes anything to disk unless the caller passes `apply=True`
(CLI: `--apply` flag; MCP: `apply=True` parameter).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import (
    CANONICAL_STORAGE_ENV,
    LEGACY_STORAGE_ENV,
    ResolvedConfiguration,
    resolve_storage_dir,
)


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    hint: Optional[str] = None  # actionable fix, shown only when ok=False
    required: bool = True  # if False, a failing check is informational only
                            # and does not affect DoctorReport.all_ok/exit code

    def to_dict(self) -> Dict[str, Any]:
        d = {"name": self.name, "ok": self.ok, "detail": self.detail, "required": self.required}
        if self.hint:
            d["hint"] = self.hint
        return d


@dataclass
class DoctorReport:
    storage_dir: str
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(c.ok for c in self.checks if c.required)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "storage_dir": self.storage_dir,
            "all_ok": self.all_ok,
            "checks": [c.to_dict() for c in self.checks],
        }


def run_doctor(
    storage_dir: str, *, configuration: Optional[ResolvedConfiguration] = None
) -> DoctorReport:
    """
    Runs a sequence of independent smoke tests against `storage_dir`.
    Never raises — every check catches its own exceptions and reports
    ok=False with a `hint`, so one broken check doesn't hide the others.
    """
    report = DoctorReport(storage_dir=storage_dir)

    # 1. storage_dir exists / is a directory / is writable
    try:
        abspath = os.path.abspath(storage_dir)
        exists = os.path.isdir(abspath)
        if not exists:
            report.checks.append(CheckResult(
                "storage_dir existe", False, f"'{abspath}' não existe ainda.",
                hint=f"Rode 'tessera init {storage_dir}' para criá-lo.",
            ))
        else:
            probe = os.path.join(abspath, f".tessera_doctor_probe_{uuid.uuid4().hex[:8]}.tmp")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("tessera doctor write probe")
            os.remove(probe)
            report.checks.append(CheckResult(
                "storage_dir existe e é gravável", True, abspath,
            ))
    except Exception as exc:  # noqa: BLE001 - deliberately broad, this is a diagnostic
        report.checks.append(CheckResult(
            "storage_dir existe e é gravável", False, str(exc),
            hint="Verifique permissões do diretório (chmod/chown) ou o caminho passado.",
        ))

    # 2. index builds without raising
    engine = None
    try:
        from .engine import TesseraEngine

        engine = (
            TesseraEngine(configuration=configuration)
            if configuration is not None
            else TesseraEngine(storage_dir=storage_dir)
        )
        engine.build_index()
        report.checks.append(CheckResult(
            "índice constrói sem erro", True,
            f"{engine.graph.number_of_nodes()} nós, {engine.graph.number_of_edges()} arestas",
        ))
    except Exception as exc:  # noqa: BLE001
        report.checks.append(CheckResult(
            "índice constrói sem erro", False, str(exc),
            hint="Verifique se algum .md tem frontmatter YAML malformado.",
        ))

    # 3. write + read round-trip (uses a real temp dir, never touches the
    #    user's actual storage_dir with throwaway probe notes)
    tmp_dir = None
    try:
        from .engine import TesseraEngine as _Engine

        tmp_dir = tempfile.mkdtemp(prefix="tessera_doctor_")
        probe_engine = _Engine(storage_dir=tmp_dir)
        # Domain-prefixed on purpose: write_memory_note() now warns on bare,
        # unprefixed mem_ids (see engine.py) - this internal probe write
        # shouldn't itself trip that warning on every `tessera doctor` run.
        probe_id = f"_doctor_probe/doctor-probe-{uuid.uuid4().hex[:8]}"
        filepath = probe_engine.write_memory_note(
            mem_id=probe_id, mem_type="factual", episode_id="doctor",
            content="Nota de teste gerada por `tessera doctor`.", tags=["doctor-probe"], entities=[],
        )
        probe_engine.build_index(use_cache=False)
        results = probe_engine.retrieve_context(query_text="nota de teste doctor", top_n=1)
        found = any(r["id"] == probe_id for r in results)
        report.checks.append(CheckResult(
            "escrita + leitura (round-trip) funciona", os.path.exists(filepath) and found,
            f"gravado em {filepath}, recuperável via query: {found}",
            hint=None if found else "write_memory_note gravou mas retrieve_context não achou a nota de volta.",
        ))
    except Exception as exc:  # noqa: BLE001
        report.checks.append(CheckResult(
            "escrita + leitura (round-trip) funciona", False, str(exc),
        ))
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # 4. rich available (optional, but degrades the CLI's TUI if missing)
    try:
        import importlib.metadata

        rich_version = importlib.metadata.version("rich")
        report.checks.append(CheckResult("rich instalado (saída colorida)", True, rich_version))
    except Exception:
        report.checks.append(CheckResult(
            "rich instalado (saída colorida)", False, "não instalado",
            hint="pip install 'rich>=13.0' (ou reinstale com 'pip install -e .')",
        ))

    # 5. MCP extra available (optional — only needed for `tessera-mcp`, not the CLI itself)
    try:
        import mcp  # noqa: F401

        report.checks.append(CheckResult("extra 'mcp' instalado", True, "mcp.server.fastmcp disponível", required=False))
    except ImportError:
        report.checks.append(CheckResult(
            "extra 'mcp' instalado", False, "não instalado",
            hint="pip install 'tessera[mcp]' se quiser rodar 'tessera-mcp'.",
            required=False,
        ))

    # 6. Optional assisted mode is deliberately unselected by default. Doctor
    #    does not inspect provider-specific credentials or project files.
    report.checks.append(CheckResult(
        "backend assistido opcional", True,
        "nenhum backend é sondado ou ativado pelo doctor; configure um llm_fn explicitamente",
        required=False,
    ))

    return report


@dataclass
class QuickstartPlan:
    storage_dir: str
    project_root: str
    detected_project_type: str
    mcp_config_block: Dict[str, Any]
    actions_taken: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "storage_dir": self.storage_dir,
            "project_root": self.project_root,
            "detected_project_type": self.detected_project_type,
            "mcp_config_block": self.mcp_config_block,
            "actions_taken": self.actions_taken,
        }


def _detect_project_type(project_root: str) -> str:
    markers = {
        "package.json": "node/javascript",
        "pyproject.toml": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
        ".git": "git repo (tipo genérico)",
    }
    for marker, label in markers.items():
        if os.path.exists(os.path.join(project_root, marker)):
            return label
    return "desconhecido"


def _suggest_storage_dir(project_root: str) -> str:
    """Return the generic project-local fallback without directory discovery."""
    return os.path.join(project_root, "memories")


def build_quickstart_plan(project_root: Optional[str] = None, storage_dir: Optional[str] = None) -> QuickstartPlan:
    """
    Read-only planning step: detects the project, proposes a storage_dir
    (unless one was given explicitly), and builds the MCP config block —
    does NOT touch disk. Call `apply_quickstart_plan()` separately to act
    on it.
    """
    project_root = os.path.abspath(project_root or os.getcwd())
    project_type = _detect_project_type(project_root)
    if storage_dir:
        resolved_storage_dir = os.path.abspath(resolve_storage_dir(storage_dir))
    elif os.environ.get(CANONICAL_STORAGE_ENV) or os.environ.get(LEGACY_STORAGE_ENV):
        resolved_storage_dir = os.path.abspath(resolve_storage_dir())
    else:
        resolved_storage_dir = _suggest_storage_dir(project_root)

    tessera_mcp_bin = shutil.which("tessera-mcp") or os.path.join(
        os.path.dirname(sys.executable), "tessera-mcp"
    )
    mcp_config_block = {
        "mcpServers": {
            "tessera": {
                "command": tessera_mcp_bin,
                "env": {"TESSERA_STORAGE_DIR": resolved_storage_dir},
            }
        }
    }

    return QuickstartPlan(
        storage_dir=resolved_storage_dir,
        project_root=project_root,
        detected_project_type=project_type,
        mcp_config_block=mcp_config_block,
    )


def apply_quickstart_plan(plan: QuickstartPlan) -> QuickstartPlan:
    """
    Executes the plan: creates storage_dir if missing, runs the first
    build_index(). Idempotent — safe to call again on an already-initialized
    directory (build_index() no-ops via its file fingerprint cache).
    """
    from .engine import TesseraEngine

    os.makedirs(plan.storage_dir, exist_ok=True)
    plan.actions_taken.append(f"mkdir -p {plan.storage_dir}")

    engine = TesseraEngine(storage_dir=plan.storage_dir)
    engine.build_index()
    plan.actions_taken.append(
        f"tessera index {plan.storage_dir}  ({engine.graph.number_of_nodes()} nós indexados)"
    )
    return plan


def mcp_config_block_as_json(plan: QuickstartPlan) -> str:
    return json.dumps(plan.mcp_config_block, indent=2, ensure_ascii=False)
