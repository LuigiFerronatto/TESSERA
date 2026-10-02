"""Experimental, read-only setup UX and pure reversible document planning.

No function in this module writes files, launches a provider, or grants access.
``apply_plan`` and ``rollback_plan`` transform immutable snapshots in memory;
the explicit experimental ``integration_files`` adapter can materialize them.
Public CLI apply is gated off pending real-client acceptance.
"""
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
from typing import Optional

SCHEMA = "tessera.integration-plan.v1"
OWNER_SCHEMA = "tessera.integration-owner.v1"
RUNTIMES = ("claude", "codex", "gemini", "copilot", "generic-mcp")
JSON_ADAPTERS = ("claude", "gemini")
MAX_BYTES = 1024 * 1024
SOURCES = {
    "claude": {
        "url": "https://code.claude.com/docs/en/mcp",
        "revision": "52c76441cae91f6891e4712306bffb057ff6fec5 (stdio shape); live scope docs observed 2026-10-02",
        "shape_source": "https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/plugins/plugin-dev/skills/mcp-integration/examples/stdio-server.json",
    },
    "gemini": {
        "url": "https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/commands/mcp/add.ts",
        "revision": "fb972b2f87fe7d5b06d37eac711490162d98de2c",
    },
    "codex": {
        "url": "https://github.com/openai/codex/blob/4dd51f4a5f2037f8aa322fe7807315e6530a4ec8/codex-rs/cli/src/mcp_cmd.rs",
        "revision": "4dd51f4a5f2037f8aa322fe7807315e6530a4ec8",
    },
    "copilot": {
        "url": "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers",
        "revision": "documentation observed 2026-10-02; diagnostic only",
    },
}


class IntegrationError(ValueError):
    """An unsupported, conflicting, malformed, or stale setup request."""


def _encode(value):
    try:
        return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise IntegrationError("configuration cannot be represented as finite UTF-8 JSON") from exc


def _hash(value):
    return None if value is None else hashlib.sha256(value).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IntegrationError("duplicate JSON keys are unsupported")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise IntegrationError("non-finite JSON values are unsupported")


def _parse(raw):
    if raw is None:
        return {}
    if len(raw) > MAX_BYTES:
        raise IntegrationError("configuration exceeds the 1 MiB planning limit")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        # Never echo a provider's source content (it may contain credentials).
        raise IntegrationError("configuration must be an unambiguous UTF-8 JSON object") from exc
    if not isinstance(value, dict):
        raise IntegrationError("configuration must be a JSON object")
    return value


@dataclass(frozen=True)
class DocumentState:
    """Private snapshots; never serialize these into a plan, log, or sidecar."""

    config: Optional[bytes] = field(default=None, repr=False)
    ownership: Optional[bytes] = field(default=None, repr=False)

    def fingerprints(self):
        return {"config_sha256": _hash(self.config), "ownership_sha256": _hash(self.ownership)}


@dataclass(frozen=True)
class SetupRequest:
    runtime: str
    scope: str
    store_name: Optional[str] = None
    store_path: Optional[str] = None
    remove: bool = False

    def descriptor(self):
        if self.runtime not in RUNTIMES or self.scope not in {"project", "user"}:
            raise IntegrationError("choose a supported runtime and explicit project/user scope")
        if self.remove:
            if self.store_name or self.store_path:
                raise IntegrationError("removal does not accept a store binding")
            return None
        if bool(self.store_name) == bool(self.store_path):
            raise IntegrationError("choose exactly one of --store-name or --store-path")
        if self.store_name:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.store_name):
                raise IntegrationError("store name must be a simple registry name, not a path")
            args = ["--global", self.store_name]
        else:
            if self.scope != "user":
                raise IntegrationError("absolute store bindings are user-local; project scope needs --store-name")
            if not Path(self.store_path).is_absolute():
                raise IntegrationError("user-local --store-path must be absolute")
            if any(ord(char) < 32 for char in self.store_path):
                raise IntegrationError("store path must not contain control characters")
            args = ["--store", self.store_path]
        return {"command": "tessera-mcp", "args": args}


@dataclass(frozen=True)
class SetupPlan:
    request: SetupRequest
    before: DocumentState = field(repr=False)
    after: DocumentState = field(repr=False)
    operation: str
    previous_entry: Optional[bytes] = field(default=None, repr=False)
    desired_entry: Optional[bytes] = field(default=None, repr=False)
    other_scope: DocumentState = field(default=DocumentState(), repr=False)

    def to_dict(self):
        request = self.request
        entry = None if self.desired_entry is None else _parse(self.desired_entry)
        native = None
        if request.runtime in JSON_ADAPTERS:
            native = [request.runtime, "mcp", "remove", "tessera", "--scope", request.scope]
            if not request.remove:
                native = [request.runtime, "mcp", "add", "--scope", request.scope,
                          "--transport", "stdio", "tessera"]
                if request.runtime == "claude":
                    native.append("--")
                native += [entry["command"], *entry["args"]]
        return {
            "schema_version": SCHEMA, "runtime": request.runtime, "scope": request.scope,
            "operation": self.operation, "current_state": self.before.fingerprints(),
            "desired_state": self.after.fingerprints(),
            "other_scope_guard": self.other_scope.fingerprints(),
            "planned_mutations": [] if self.operation == "noop" else [{
                "path": "/mcpServers/tessera", "operation": self.operation,
                "before_sha256": _hash(self.previous_entry), "after": entry,
                "config_file_action": ("delete" if self.after.config is None else
                                       "create" if self.before.config is None else "rewrite"),
                "serialization": "strict JSON rewritten with 2-space indentation; unrelated values preserved",
            }, {
                "path": "ownership-sidecar",
                "operation": ("remove" if self.after.ownership is None else
                              "add" if self.before.ownership is None else "update"),
                "before_sha256": _hash(self.before.ownership),
                "after": _parse(self.after.ownership) if self.after.ownership is not None else None,
            }],
            "native_cli_candidate": native,
            "native_cli_execution": "unavailable: version/OS and rollback acceptance gates pending",
            "rollback": {
                "method": "rollback_plan(plan, current_snapshot) restores exact original bytes in memory",
                "requires": self.after.fingerprints(), "stale_state": "refuse",
                "disk_backup_created": False,
            },
            "capabilities": capabilities(request.runtime),
            "binding": {
                "kind": "named-global-store" if request.store_name else "user-local-path",
                "value": request.store_name or request.store_path,
                "registration_reach": "this project" if request.scope == "project" else "all client projects",
                "store_reach": "explicit shared store; no automatic project-identity isolation",
            } if not request.remove else None,
            "warnings": [
                "Preview only: no runtime registration, permission, client launch, or filesystem apply",
                "Install tessera-agent-memory[mcp] separately; executable/version/store readiness is unverified",
                "Named stores must be registered on each machine; no absolute source-checkout path is generated",
                "Runtime policy/trust approval remains with the client; setup does not change it",
            ],
            "provider_source": SOURCES.get(request.runtime),
        }


def capabilities(runtime):
    return {
        "mcp_transport": "existing #120 stdio tools; not semantic #171 tools",
        "document_adapter": "experimental-json" if runtime in JSON_ADAPTERS else "unavailable",
        "runtime_version": None, "runtime_compatibility": "unverified",
        "semantic_agent_api": "unavailable: #171",
        "lifecycle_hooks": "unavailable: #177 and canonical #196 dependency",
        "before_reasoning_context": False, "tool_pre_post_hooks": False,
        "subagent_events": False, "compaction_events": False, "async_hooks": False,
        "filesystem_apply": "experimental Python API; public CLI unavailable",
    }


def _servers(document):
    servers = document.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise IntegrationError("mcpServers must be an object; unknown formats are not rewritten")
    return servers


def build_plan(request, state=DocumentState(), *, other_scope=DocumentState()):
    """Plan one entry. Snapshots and request are explicit; no environment or I/O."""
    desired = request.descriptor()
    if request.runtime not in JSON_ADAPTERS:
        raise IntegrationError("no validated document adapter for this runtime; no mutations planned")
    document = _parse(state.config)
    servers = _servers(document)
    present = "tessera" in servers
    previous = _encode(servers["tessera"]) if present else None
    owner = _parse(state.ownership)
    if owner:
        expected_keys = {"schema_version", "runtime", "scope", "entry_sha256", "created_file", "created_servers"}
        if (set(owner) != expected_keys or owner.get("schema_version") != OWNER_SCHEMA
                or owner.get("runtime") != request.runtime or owner.get("scope") != request.scope
                or type(owner.get("created_file")) is not bool
                or type(owner.get("created_servers")) is not bool):
            raise IntegrationError("ownership sidecar is malformed or belongs to another target")
        if not present or owner.get("entry_sha256") != _hash(previous):
            raise IntegrationError("TESSERA entry changed since ownership was recorded; refusing overwrite/removal")
    elif present:
        raise IntegrationError("tessera entry is not owned by this installer; refusing takeover/removal")
    elif state.ownership is not None:
        raise IntegrationError("empty ownership sidecar is invalid")
    if not request.remove and "tessera" in _servers(_parse(other_scope.config)):
        raise IntegrationError("tessera exists in the other scope; resolve the scope conflict explicitly")
    if request.remove:
        if not present:
            return SetupPlan(request, state, state, "noop")
        del servers["tessera"]
        if not servers and owner["created_servers"]:
            document.pop("mcpServers", None)
        after = DocumentState(None if not document and owner["created_file"] else _encode(document))
        return SetupPlan(request, state, after, "remove", previous)
    wanted = _encode(desired)
    if present and previous == wanted:
        return SetupPlan(request, state, state, "noop", previous, wanted, other_scope)
    new_owner = {
        "schema_version": OWNER_SCHEMA, "runtime": request.runtime, "scope": request.scope,
        "entry_sha256": _hash(wanted),
        "created_file": owner.get("created_file", state.config is None),
        "created_servers": owner.get("created_servers", "mcpServers" not in document),
    }
    servers["tessera"] = desired
    document["mcpServers"] = servers
    after = DocumentState(_encode(document), _encode(new_owner))
    return SetupPlan(request, state, after, "update" if present else "add", previous, wanted, other_scope)


def apply_plan(plan, current, *, other_scope=DocumentState()):
    """Explicit in-memory apply only. Caller retains both snapshots for rollback."""
    if current != plan.before:
        raise IntegrationError("stale plan: configuration or ownership changed; rebuild the plan")
    if not plan.request.remove and other_scope != plan.other_scope:
        raise IntegrationError("stale plan: other scope changed; rebuild the plan")
    return plan.after


def rollback_plan(plan, current):
    """Never overwrite a post-apply edit, including unrelated config or formatting."""
    if current != plan.after:
        raise IntegrationError("stale rollback: configuration or ownership changed; inspect manually")
    return plan.before


def config_path(runtime, scope, project_root, home):
    if runtime == "claude":
        return project_root / ".mcp.json" if scope == "project" else home / ".claude.json"
    if runtime == "gemini":
        return (project_root if scope == "project" else home) / ".gemini" / "settings.json"
    if runtime == "codex":
        return (project_root if scope == "project" else home) / ".codex" / "config.toml"
    return None


def ownership_path(path, runtime, scope):
    return path.with_name(f".tessera-{runtime}-{scope}-owner.json")


def _read(path):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise IntegrationError("symlinked configuration paths are unsupported")
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise IntegrationError("configuration must be a regular file")
        descriptor = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise IntegrationError("configuration must be a regular file")
            raw = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino, opened.st_mtime_ns, opened.st_size) != (
                    after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size):
                raise IntegrationError("configuration changed while being read")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise IntegrationError("configuration cannot be read") from exc
    if len(raw) > MAX_BYTES:
        raise IntegrationError("configuration exceeds the 1 MiB planning limit")
    return raw


def _read_state(path, runtime, scope):
    return DocumentState(_read(path), _read(ownership_path(path, runtime, scope)))


def detect_runtimes(project_root, home, *, which=shutil.which):
    """PATH lookup and file existence only; no executable/version probes."""
    return [{
        "runtime": runtime, "executable_on_path": which(runtime) if runtime != "generic-mcp" else None,
        "config_evidence": [str(path) for scope in ("project", "user")
                            for path in [config_path(runtime, scope, project_root, home)]
                            if path is not None and path.is_file()],
        "version": None, "version_probed": False,
        "capabilities": capabilities(runtime),
    } for runtime in RUNTIMES]


def preview_target(request, project_root, home, *, environ=None):
    """Read standard paths only; custom provider roots need a future adapter."""
    env = os.environ if environ is None else environ
    output = {"runtime": request.runtime, "scope": request.scope,
              "capabilities": capabilities(request.runtime), "planned_mutations": []}
    try:
        request.descriptor()
        override = {"claude": "CLAUDE_CONFIG_DIR", "codex": "CODEX_HOME",
                    "gemini": "GEMINI_CLI_HOME", "copilot": "COPILOT_HOME"}.get(request.runtime)
        if override and env.get(override):
            raise IntegrationError("custom provider home is set; default-path planning is disabled")
        if project_root == home:
            raise IntegrationError("project root equals home; project/user scope would overlap")
        if request.runtime not in JSON_ADAPTERS:
            raise IntegrationError("runtime document adapter unavailable; no config or hooks are generated")
        path = config_path(request.runtime, request.scope, project_root, home)
        opposite = "user" if request.scope == "project" else "project"
        other_path = config_path(request.runtime, opposite, project_root, home)
        state = _read_state(path, request.runtime, request.scope)
        other = _read_state(other_path, request.runtime, opposite)
        # Claude also supports a local per-project scope inside ~/.claude.json.
        claude_user = state if request.scope == "user" else other
        if request.runtime == "claude" and not request.remove:
            local = _parse(claude_user.config).get("projects", {})
            if not isinstance(local, dict):
                raise IntegrationError("unknown Claude local-scope format")
            project = local.get(str(project_root), {})
            if not isinstance(project, dict) or "tessera" in _servers(project):
                raise IntegrationError("Claude local scope conflicts with this project; inspect manually")
        plan = build_plan(request, state, other_scope=other)
        output = plan.to_dict()
        output.update({"config_path": str(path), "ownership_path": str(ownership_path(path, request.runtime, request.scope)),
                       "status": "planned", "project_root": str(project_root)})
    except IntegrationError as exc:
        output.update({"status": "blocked", "error": str(exc)})
    return output


def add_setup_parsers(sub):
    direct = sub.add_parser("integrate", help="Experimental read-only runtime setup plan")
    direct.add_argument("runtime", choices=RUNTIMES)
    mcp = sub.add_parser("mcp", help="MCP setup discovery (experimental preview only)")
    guided = mcp.add_subparsers(dest="mcp_command", required=True).add_parser("setup")
    guided.add_argument("--runtime", action="append", choices=RUNTIMES, help="Explicit target; repeatable")
    for parser in (direct, guided):
        parser.add_argument("--scope", choices=("project", "user"), required=True)
        parser.add_argument("--project-root", default=".")
        binding = parser.add_mutually_exclusive_group()
        binding.add_argument("--store-name", help="Logical named store registered separately on each machine")
        binding.add_argument("--store-path", help="Absolute user-local store path (user scope only)")
        parser.add_argument("--remove", action="store_true")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", action="store_true", help="Explicit preview; also the default")
        mode.add_argument("--apply", action="store_true", help="Unavailable until real-client acceptance passes")
        parser.add_argument("--json", action="store_true")
        parser.set_defaults(func=cmd_setup)


def cmd_setup(args):
    root = Path(os.path.abspath(os.path.expanduser(args.project_root)))
    home = Path.home()
    detected = detect_runtimes(root, home)
    selected = [args.runtime] if isinstance(args.runtime, str) else list(dict.fromkeys(args.runtime or []))
    if not selected and not args.json and sys.stdin.isatty() and not args.apply:
        for runtime in detected:
            print(f"{runtime['runtime']}: executable {'found' if runtime['executable_on_path'] else 'not observed'}; version unverified")
        try:
            selected = list(dict.fromkeys(input("Targets (comma-separated; blank cancels): ").strip().split(",")))
            selected = [item.strip() for item in selected if item.strip()]
        except (EOFError, KeyboardInterrupt):
            selected = []
    results = [preview_target(SetupRequest(runtime, args.scope, args.store_name, args.store_path, args.remove), root, home)
               for runtime in selected]
    error = None
    if args.apply:
        error = "CLI apply is unavailable pending provider/version/OS acceptance; the experimental filesystem API is fixture-tested"
    elif not selected:
        error = "select targets explicitly with --runtime; discovery did not select or configure anything"
    output = {"schema_version": SCHEMA, "mode": "dry-run", "applied": False,
              "detected_runtimes": detected, "selected_integrations": results, "error": error}
    if args.json:
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    else:
        print("TESSERA experimental integration preview (no files changed)")
        for result in results:
            print(f"{result['runtime']} / {result['scope']}: {result['status']}")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if error:
            print(error)
    return 2 if error or any(item["status"] == "blocked" for item in results) else 0
