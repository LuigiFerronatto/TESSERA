"""Explicit, hash-bound setup actions. No client is launched by this module.

Durable CLI receipts contain only the prior managed entry and ownership metadata,
not unrelated config or credential-bearing backups. CLI rollback is semantic;
the lower-level in-process receipt additionally supports byte-exact rollback.
"""
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import sys

from .integration_setup import (
    SCHEMA, OWNER_SCHEMA, JSON_ADAPTERS, SOURCES, DocumentState, IntegrationError,
    SetupPlan, SetupRequest, _encode, _hash, _parse, _read_state, _servers,
    build_plan, capabilities, config_path, detect_runtimes, ownership_path, preview_target,
)
from .integration_files import (
    FileSnapshot, _expect, _snapshot, apply_file_plan, bind_file_plan,
)

RECEIPT_SCHEMA = "tessera.integration-undo.v1"


def receipt_path(path, runtime, scope):
    return path.with_name(f".tessera-{runtime}-{scope}-undo.json")


def _managed_entry(entry, runtime):
    """Never copy arbitrary environment/header/credential fields into receipts."""
    if entry is None:
        return
    allowed = {"command", "args"} | ({"type", "tools"} if runtime == "copilot" else set())
    if not isinstance(entry, dict) or set(entry) != allowed:
        raise IntegrationError("rollback receipts accept only known TESSERA-owned launcher fields")
    if runtime == "copilot" and (entry["type"] != "local" or entry["tools"] != ["*"]):
        raise IntegrationError("unknown Copilot owned-entry shape")
    args = entry["args"]
    if not isinstance(args, list) or not all(isinstance(value, str) for value in args):
        raise IntegrationError("invalid owned launcher arguments")
    # A previous receipt from the original owned stdio launcher is safe to migrate.
    if entry["command"] == "python" and args == ["-m", "tessera.mcp_server"]:
        return
    if entry["command"] != "tessera-mcp" or not isinstance(args, list) or len(args) != 2:
        raise IntegrationError("unknown owned launcher; refusing to persist an undo receipt")
    binding = {"store_name": args[1]} if args[0] == "--global" else {"store_path": args[1]}
    if args[0] not in {"--global", "--store"}:
        raise IntegrationError("unknown owned launcher binding")
    SetupRequest(runtime, "user", **binding).descriptor()


def _safe_owner(owner, entry, request):
    if owner is None:
        if entry is not None:
            raise IntegrationError("undo receipt lacks prior ownership")
        return
    expected = {"schema_version", "runtime", "scope", "entry_sha256", "created_file", "created_servers"}
    if (not isinstance(owner, dict) or set(owner) != expected
            or owner["schema_version"] != OWNER_SCHEMA or owner["runtime"] != request.runtime
            or owner["scope"] != request.scope or entry is None
            or owner["entry_sha256"] != _hash(_encode(entry))
            or type(owner["created_file"]) is not bool or type(owner["created_servers"]) is not bool):
        raise IntegrationError("invalid prior ownership in undo receipt")


def _load_receipt(snapshot, request, path):
    if snapshot.data is None:
        raise IntegrationError("no last-action rollback receipt exists for this target")
    value = _parse(snapshot.data)
    fields = {"schema_version", "runtime", "scope", "config_path", "after", "prior_entry",
              "prior_owner", "config_existed", "servers_existed", "config_mode", "owner_mode", "format"}
    if (set(value) != fields or value["schema_version"] != RECEIPT_SCHEMA
            or value["runtime"] != request.runtime or value["scope"] != request.scope
            or value["config_path"] != str(path)):
        raise IntegrationError("rollback receipt is malformed or belongs to another target")
    if not isinstance(value["format"], str) or value["format"] not in {"wrapper", "bare"} or (value["format"] == "bare" and request.runtime != "copilot"):
        raise IntegrationError("invalid rollback config format")
    if type(value["config_existed"]) is not bool or type(value["servers_existed"]) is not bool:
        raise IntegrationError("invalid rollback receipt existence flags")
    for key in ("config_mode", "owner_mode"):
        if value[key] is not None and (type(value[key]) is not int or not 0 <= value[key] <= 0o777):
            raise IntegrationError("invalid rollback permission snapshot")
    if (value["prior_entry"] is not None and not value["servers_existed"]
            or value["servers_existed"] and not value["config_existed"]
            or value["config_existed"] != (value["config_mode"] is not None)
            or (value["prior_owner"] is not None) != (value["owner_mode"] is not None)):
        raise IntegrationError("inconsistent rollback receipt state")
    _managed_entry(value["prior_entry"], request.runtime)
    _safe_owner(value["prior_owner"], value["prior_entry"], request)
    return value


@dataclass
class PreparedTarget:
    preview: dict
    file_plan: object = field(default=None, repr=False)
    receipt_change: object = field(default=None, repr=False)
    guards: tuple = field(default=(), repr=False)
    restore_modes: tuple = field(default=(None, None), repr=False)


def _native_codex(request, root, home):
    """Current native CLI is user-scoped; project TOML rewriting is not guessed."""
    desired = request.descriptor()
    if os.environ.get("CODEX_HOME"):
        raise IntegrationError("custom CODEX_HOME is set; default-path native planning is disabled")
    if root == home:
        raise IntegrationError("project root equals home; project/user scope would overlap")
    if request.scope != "user":
        raise IntegrationError("Codex native MCP add/remove is user-scoped; no project-scope CLI flag exists in the pinned source")
    paths = [config_path("codex", scope, root, home) for scope in ("user", "project")]
    snapshots = [_snapshot(path) for path in paths]
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    documents = []
    for snapshot in snapshots:
        try:
            documents.append(tomllib.loads(snapshot.data.decode("utf-8")) if snapshot.data else {})
        except (ValueError, UnicodeError) as exc:
            raise IntegrationError("Codex config must be valid UTF-8 TOML; no source content is echoed") from exc
    for document in documents:
        if not isinstance(document.get("mcp_servers", {}), dict):
            raise IntegrationError("unknown Codex mcp_servers shape")
    entry = documents[0].get("mcp_servers", {}).get("tessera")
    if "tessera" in documents[1].get("mcp_servers", {}):
        raise IntegrationError("Codex project scope already contains tessera; resolve precedence explicitly")
    owner_path = ownership_path(paths[0], "codex", "user")
    owner_snapshot = _snapshot(owner_path)
    owner = _parse(owner_snapshot.data) if owner_snapshot.data is not None else None
    if entry is not None:
        _managed_entry(entry, "codex")
        _safe_owner(owner, entry, request)
    elif owner is not None:
        raise IntegrationError("Codex ownership is partial; inspect before planning native commands")
    action = "remove" if request.remove and entry is not None else (
        "noop" if request.remove or entry == desired else "update" if entry else "add")
    command = ["codex", "mcp", "remove", "tessera"] if request.remove else [
        "codex", "mcp", "add", "tessera", "--", desired["command"], *desired["args"]]
    undo = ["codex", "mcp", "remove", "tessera"] if entry is None else [
        "codex", "mcp", "add", "tessera", "--", entry["command"], *entry["args"]]
    return PreparedTarget({
        "schema_version": SCHEMA, "runtime": "codex", "scope": "user", "status": "planned",
        "operation": action, "strategy": "native-command-plan", "config_path": str(paths[0]),
        "project_root": str(root), "provider_source": SOURCES["codex"],
        "capabilities": capabilities("codex"), "native_cli_candidate": command if action != "noop" else None,
        "native_rollback_candidate": undo if action != "noop" else None,
        "planned_mutations": [] if action == "noop" else [{"path": "mcp_servers.tessera", "after": desired,
                                                                  "operation": action}],
        "current_state": {str(path): {"sha256": _hash(snapshot.data), "mode": snapshot.mode}
                          for path, snapshot in zip(paths + [owner_path], snapshots + [owner_snapshot])},
        "warnings": ["Native command plan only: no provider process is executed",
                     "The JSON file transaction executor does not execute native commands or rewrite TOML",
                     "Real native execution, ownership receipt capture and OS/version acceptance remain unverified"],
    })


def prepare_target(request, root, home, *, rollback=False):
    if request.runtime == "codex" and not rollback:
        return _native_codex(request, root, home)
    check = preview_target(request, root, home)
    if check["status"] == "blocked":
        raise IntegrationError(check["error"])
    path = config_path(request.runtime, request.scope, root, home)
    other_scope = "user" if request.scope == "project" else "project"
    other_path = config_path(request.runtime, other_scope, root, home)
    state = _read_state(path, request.runtime, request.scope)
    other = _read_state(other_path, request.runtime, other_scope)
    guards = []
    if request.runtime == "copilot":
        alternate = root / ".mcp.json"
        alternate_snapshot = _snapshot(alternate)
        if "tessera" in _servers(_parse(alternate_snapshot.data), "copilot"):
            raise IntegrationError("Copilot .mcp.json takes precedence over .github/mcp.json; existing tessera must be resolved explicitly")
        guards.append((alternate, alternate_snapshot))
    undo_path = receipt_path(path, request.runtime, request.scope)
    before_receipt = _snapshot(undo_path)
    existing_receipt = _load_receipt(before_receipt, request, path) if before_receipt.data is not None else None
    modes = (None, None)
    if rollback:
        receipt = existing_receipt or _load_receipt(before_receipt, request, path)
        if state.fingerprints() != receipt["after"]:
            raise IntegrationError("stale rollback receipt: config or ownership changed since apply")
        document = _parse(state.config)
        servers = _servers(document, request.runtime)
        prior = receipt["prior_entry"]
        if prior is None:
            servers.pop("tessera", None)
        else:
            if "tessera" in _servers(_parse(other.config), request.runtime):
                raise IntegrationError("rollback would conflict with the other scope")
            servers["tessera"] = prior
        if receipt["format"] == "bare":
            document = servers
        elif servers or receipt["servers_existed"]:
            document["mcpServers"] = servers
        else:
            document.pop("mcpServers", None)
        config = _encode(document) if document or receipt["config_existed"] else None
        prior_owner = receipt["prior_owner"]
        owner = _encode(prior_owner) if prior_owner is not None else None
        previous = _servers(_parse(state.config), request.runtime).get("tessera")
        plan = SetupPlan(request, state, DocumentState(config, owner), "rollback",
                         _encode(previous) if previous is not None else None,
                         _encode(prior) if prior is not None else None, other,
                         "/tessera" if receipt["format"] == "bare" else "/mcpServers/tessera")
        after_receipt = FileSnapshot(None, None)
        modes = (receipt["config_mode"], receipt["owner_mode"])
    else:
        plan = build_plan(request, state, other_scope=other)
        if plan.operation == "noop":
            after_receipt = before_receipt
        else:
            original = _parse(state.config)
            prior = _servers(original, request.runtime).get("tessera")
            _managed_entry(prior, request.runtime)
            owner = _parse(state.ownership) if state.ownership is not None else None
            _safe_owner(owner, prior, request)
            config_snapshot, owner_snapshot = _snapshot(path), _snapshot(ownership_path(path, request.runtime, request.scope))
            receipt = {
                "schema_version": RECEIPT_SCHEMA, "runtime": request.runtime, "scope": request.scope,
                "config_path": str(path), "after": plan.after.fingerprints(),
                "prior_entry": prior, "prior_owner": owner,
                "config_existed": state.config is not None,
                "servers_existed": plan.server_path == "/tessera" or "mcpServers" in original,
                "format": "bare" if plan.server_path == "/tessera" else "wrapper",
                "config_mode": config_snapshot.mode, "owner_mode": owner_snapshot.mode,
            }
            after_receipt = FileSnapshot(_encode(receipt), 0o600)
    file_plan = bind_file_plan(plan, path, other_path)
    preview = plan.to_dict()
    preview.update({"status": "planned", "config_path": str(path), "project_root": str(root),
                    "ownership_path": str(file_plan.owner_path), "receipt_path": str(undo_path),
                    "strategy": "reviewed-json-files", "mode_guards": {
                        "config": file_plan.before_config.mode, "ownership": file_plan.before_owner.mode,
                        "other_config": file_plan.other_config.mode, "other_ownership": file_plan.other_owner.mode},
                    "additional_guards": {str(p): {"sha256": _hash(s.data), "mode": s.mode} for p, s in guards},
                    "receipt_guard": {"sha256": _hash(before_receipt.data), "mode": before_receipt.mode},
                    "receipt_mutation": None if after_receipt == before_receipt else {
                        "operation": "remove" if after_receipt.data is None else "write",
                        "mode": after_receipt.mode,
                        "after": _parse(after_receipt.data) if after_receipt.data is not None else None,
                    }})
    preview["rollback"] = {"method": "--rollback previews the last owned-entry inverse; --apply --plan-hash applies it",
                           "scope": "semantic owned-entry/ownership reversal; unrelated values preserved",
                           "formatting": "CLI does not persist whole-config bytes or credentials; original formatting is not restored",
                           "stale_state": "refuse", "history_depth": 1}
    if request.runtime == "copilot":
        preview["warnings"].append("Copilot project configuration requires a trusted Git repository; runtime acceptance is unverified")
    if rollback:
        preview["native_cli_candidate"] = None
    return PreparedTarget(preview, file_plan, (undo_path, before_receipt, after_receipt), tuple(guards), modes)


def plan_hash(previews):
    payload = json.dumps({"schema_version": SCHEMA, "selected_integrations": previews},
                         sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_setup(args):
    root = Path(os.path.abspath(os.path.expanduser(args.project_root)))
    home = Path(os.path.abspath(os.path.expanduser(args.config_home))) if args.config_home else Path.home()
    detected = detect_runtimes(root, home)
    selected = [args.runtime] if isinstance(args.runtime, str) else list(dict.fromkeys(args.runtime or []))
    if not selected and not args.json and sys.stdin.isatty() and not args.apply:
        for runtime in detected:
            print(f"{runtime['runtime']}: executable {'found' if runtime['executable_on_path'] else 'not observed'}; version unverified")
        try:
            selected = list(dict.fromkeys(item.strip() for item in input("Targets (comma-separated; blank cancels): ").split(",") if item.strip()))
        except (EOFError, KeyboardInterrupt):
            selected = []
    prepared, previews = [], []
    for runtime in selected:
        try:
            request = SetupRequest(runtime, args.scope, args.store_name, args.store_path, args.remove or args.rollback)
            item = prepare_target(request, root, home, rollback=args.rollback)
            prepared.append(item)
            previews.append(item.preview)
        except (IntegrationError, OSError) as exc:
            previews.append({"runtime": runtime, "scope": args.scope, "status": "blocked",
                             "planned_mutations": [], "capabilities": capabilities(runtime),
                             "error": str(exc) if isinstance(exc, IntegrationError) else "configuration cannot be inspected"})
    if args.scope == "project":
        by_runtime = {item.preview["runtime"]: item for item in prepared}
        if {"claude", "copilot"}.issubset(by_runtime):
            if all("tessera" in _servers(_parse(by_runtime[name].file_plan.plan.after.config), name)
                   for name in ("claude", "copilot")):
                for name in ("claude", "copilot"):
                    by_runtime[name].preview.update({"status": "blocked", "error":
                        "Claude .mcp.json would shadow Copilot project registration; choose user scope or separate targets"})
    digest = plan_hash(previews)
    error, applied = None, []
    if not selected:
        error = "select targets explicitly with --runtime; discovery did not select or configure anything"
    elif args.apply and args.plan_hash != digest:
        error = "missing or stale --plan-hash; review the current preview and repeat with its exact hash"
    elif args.apply and any(item["status"] == "blocked" for item in previews):
        error = "blocked target; no mutations applied"
    elif args.apply and any(item.file_plan is None for item in prepared):
        error = "native-command plans are inspectable only; this executor never launches provider clients or rewrites TOML"
    elif args.apply:
        # Validate all targets/receipts before the first write. Runtime transactions
        # are sequential, not a multi-runtime atomic transaction; report partial success.
        try:
            for item in prepared:
                for path, snapshot in item.guards:
                    _expect(path, snapshot)
                fp = item.file_plan
                for path, snapshot in ((fp.config_path, fp.before_config), (fp.owner_path, fp.before_owner),
                                       (fp.other_config_path, fp.other_config), (fp.other_owner_path, fp.other_owner),
                                       (item.receipt_change[0], item.receipt_change[1])):
                    _expect(path, snapshot)
            for item in prepared:
                for path, snapshot in item.guards:
                    _expect(path, snapshot)
                change = item.receipt_change
                apply_file_plan(item.file_plan, extra_changes=() if change[1] == change[2] else (change,),
                                config_mode=item.restore_modes[0], owner_mode=item.restore_modes[1])
                applied.append(item.preview["runtime"])
        except (IntegrationError, OSError) as exc:
            error = str(exc) if isinstance(exc, IntegrationError) else "filesystem apply failed; inspect partial state"
    output = {"schema_version": SCHEMA, "mode": "apply" if args.apply else "dry-run",
              "plan_hash": digest, "applied": bool(applied), "applied_integrations": applied,
              "detected_runtimes": detected, "selected_integrations": previews, "error": error}
    if args.json:
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    else:
        print("TESSERA integration " + ("apply result" if args.apply else "preview (no files changed)"))
        print(f"Plan hash: {digest}")
        for result in previews:
            print(f"{result['runtime']} / {result['scope']}: {result['status']}")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if error:
            print(error)
    return 2 if error or any(item["status"] == "blocked" for item in previews) else 0
