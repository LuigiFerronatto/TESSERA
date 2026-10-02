"""Versioned CLI presentation boundary; no storage, retrieval or provider decisions.

CommandResult.data is the command's existing machine contract. It is deliberately
not re-enveloped: query results must remain identical to Engine/MCP retrieval.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import os
import re
import shutil
import sys
from typing import Any, Dict, Iterable, Optional

CONTRACT_VERSION = 1
# Existing command-specific status codes remain compatible (see CLI_OUTPUT.md).
EXIT_SUCCESS = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_CONFIGURATION = 2
EXIT_PARTIAL = 3
EXIT_FILESYSTEM = 4
EXIT_PROVIDER = 5
EXIT_INTERNAL = 70
EXIT_CANCELLED = 130

# English is the supported catalog for v1. Never silently promise a translation.
MESSAGES = {
    "progress.index": "Updating index",
    "progress.discovery": "Discovering sources",
    "progress.reason": "Generating assisted context",
    "progress.decompose": "Extracting memories",
    "cancelled": "Operation cancelled.",
}


@dataclass(frozen=True)
class OutputPolicy:
    mode: str = "plain"
    color: bool = False
    unicode: bool = True
    width: int = 80
    interactive: bool = False
    quiet: bool = False
    verbose: bool = False
    debug: bool = False
    full: bool = False
    explain: bool = False
    show_related: bool = False
    no_body: bool = False
    paths_only: bool = False
    table: bool = False
    language: str = "en"

    @classmethod
    def detect(cls, args=None):
        def flag(name):
            return bool(getattr(args, name, False))
        tty = bool(sys.stdout.isatty())
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        try:
            "✔─".encode(encoding)
            unicode = True
        except (UnicodeError, LookupError):
            unicode = False
        mode = "json" if flag("json") else (
            "rich" if tty and not flag("plain") and unicode and os.environ.get("TERM") != "dumb" else "plain"
        )
        no_color = flag("no_color") or any(key in os.environ for key in ("NO_COLOR", "TESSERA_NO_COLOR"))
        return cls(
            mode=mode, color=tty and not no_color and mode == "rich",
            unicode=unicode, width=max(20, shutil.get_terminal_size((80, 24)).columns),
            # Prompts belong to stdin; redirected stdout never enables animation.
            interactive=bool(sys.stdin.isatty()) and not flag("json") and not flag("non_interactive"),
            quiet=flag("quiet"), verbose=flag("verbose"), debug=flag("debug"),
            full=flag("full"), explain=flag("explain") or flag("debug"),
            show_related=flag("show_related"), no_body=flag("no_body"),
            paths_only=flag("paths_only"), table=flag("table"),
            language=getattr(args, "lang", "en"),
        )


_POLICY: ContextVar[Optional[OutputPolicy]] = ContextVar("tessera_output_policy", default=None)


def policy() -> OutputPolicy:
    return _POLICY.get() or OutputPolicy.detect()


@contextmanager
def output_policy(value):
    token = _POLICY.set(value)
    try:
        yield
    finally:
        _POLICY.reset(token)


@dataclass(frozen=True)
class CommandResult:
    kind: str
    data: Any
    exit_code: int = 0


@dataclass(frozen=True)
class UiEvent:
    code: str
    level: str = "information"
    fields: Dict[str, Any] = field(default_factory=dict)


class CliFailure(Exception):
    def __init__(self, code, reason, *, exit_code=EXIT_FAILED, suggested_command=None, context=None):
        super().__init__(reason)
        self.code = code
        self.exit_code = exit_code
        self.suggested_command = suggested_command
        self.context = context or {}

    def to_dict(self):
        return {
            "schema_version": CONTRACT_VERSION,
            "error": {
                "code": self.code, "message": str(self),
                "suggested_command": self.suggested_command,
                "context": self.context,
            },
            "exit_code": self.exit_code,
        }


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CliFailure("invalid_usage", message, exit_code=EXIT_USAGE, suggested_command="tessera --help")

    def print_help(self, file=None):
        if policy().mode == "json":
            JsonRenderer().render(CommandResult("help", {"schema_version": 1, "help": self.format_help()}))
        else:
            super().print_help(file)


# Strip terminal control sequences from untrusted source text for human output.
# JSON serialization preserves original evidence, escaped by json.dumps.
_TERMINAL = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]|\x1b[@-_]|[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def safe_text(value, output=None):
    value = _TERMINAL.sub("", str(value))
    if not (output or policy()).unicode:
        value = value.encode("ascii", "backslashreplace").decode("ascii")
    return value


def _fields(data, indent=""):
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        yield f"{indent}{key}: {value if value is not None else '-'}"


def english_label(value):
    # Compatibility domain diagnostics predate the v1 English presentation catalog.
    # Do not mutate their JSON/API names while rendering one human language.
    return {
        "storage_dir existe": "storage_dir exists",
        "backend assistido opcional": "optional assisted backend",
        "Verifique se algum .md tem frontmatter YAML malformado.": "Check source Markdown for malformed YAML frontmatter.",
        "pip install 'tessera[mcp]' se quiser rodar 'tessera-mcp'.": "Install 'tessera-agent-memory[mcp]' to run tessera-mcp.",
    }.get(value, value)


def human_lines(result: CommandResult, output: OutputPolicy) -> Iterable[str]:
    """One message source shared by the Rich and plain renderers."""
    data, kind = result.data, result.kind
    if kind == "error":
        error = data["error"]
        yield f"Error [{error['code']}]: {error['message']}"
        if error.get("suggested_command"):
            yield f"How to fix: {error['suggested_command']}"
        yield from _fields(error.get("context", {}), "  ")
    elif kind == "query":
        if output.paths_only:
            for hit in data:
                yield hit.get("filepath") or hit.get("filename") or hit["id"]
            return
        yield f"{len(data)} result(s) found" if data else "No relevant memories found for this query."
        for index, hit in enumerate(data, 1):
            yield f"\n{index}. {hit['id']} ({hit['type']})"
            yield f"   Source: {hit.get('filepath') or hit.get('filename') or '-'}"
            if not output.no_body:
                body = hit.get("body") or ""
                evidence = hit.get("relevant_evidence") or body
                if output.full:
                    yield body
                else:
                    excerpt = " ".join(evidence.split())
                    yield "   " + (excerpt[:237] + "..." if len(excerpt) > 240 else excerpt)
            if output.show_related and hit.get("related_ids"):
                yield "   Related: " + ", ".join(hit["related_ids"])
            if output.verbose or output.explain:
                yield f"   Relevance score: {hit['score']:.4f} (not confidence)"
            if output.explain and hit.get("score_explain"):
                yield from _fields(hit["score_explain"], "     ")
    elif kind == "list":
        for row in data:
            if output.paths_only:
                yield row["filepath"]
            else:
                yield f"{row['id']}\t{row['type']}\t{row['filepath'] if output.table else row['filename']}"
        if not data and not output.paths_only:
            yield "No memory notes found."
    elif kind == "index":
        yield f"Index rebuilt: {data['nodes']} nodes, {data['edges']} edges. (source: {data['storage_dir']})"
        if not output.quiet:
            yield "  sources: " + ", ".join(f"{k}={v}" for k, v in data["stats"].items())
        if output.verbose:
            yield from _fields(data["artifacts"], "  ")
        for warning in data["warnings"]:
            yield f"Warning: {warning}"
    elif kind == "dashboard":
        yield "TESSERA" + (f" - {data['project']}" if data.get("project") else "")
        if not data["configured"]:
            yield "TESSERA is not configured in this project."
            yield "Run: tessera init"
        else:
            yield f"Memory store: {data['storage_dir']}"
            yield f"Selected by: {data['configuration_source']}"
            yield f"Sources: {data['sources']} selected files"
            yield f"Index: {data['index_status']}"
            yield "Find information: Fast local search"
            yield "Organize / extract memories: optional, explicitly selected per command"
            yield "Generate / reason: optional, explicitly selected per command"
            if output.verbose:
                yield f"Configuration: {data['config_path']}"
                yield f"Derived index: {data['index_dir']}"
                yield from _fields(data['counts'], "  ")
            if not output.quiet:
                yield 'Next: tessera query "what is this project?"'
                yield "Next: tessera index"
                yield "Inspect: tessera corpus doctor --verbose"
    elif kind == "stats":
        yield f"Store: {data['storage_dir']}"
        yield from _fields(data["type_counts"])
        yield f"Connections: {data['edges']}"
    elif kind in {"doctor", "config.doctor"}:
        if data.get("storage_dir"):
            yield f"Store: {data['storage_dir']}"
        for check in data["checks"]:
            if not output.quiet or not check["ok"]:
                yield f"{'OK' if check['ok'] else 'PROBLEM'} {english_label(check['name'])}: {check['detail']}"
                if check.get("hint"):
                    yield f"  How to fix: {english_label(check['hint'])}"
        if output.quiet:
            yield "Healthy" if data.get("healthy", data.get("all_ok")) else "Problems found"
    elif kind == "corpus.doctor":
        yield f"tessera corpus doctor — {data['status']}"
        yield "source files modified: 0"
        yield f"Store: {data['storage_dir']}"
        yield from _fields(data["counts"], "  ")
        for finding in data["findings"]:
            yield f"{finding['severity'].upper()} {finding['code']}: {finding['message']}"
            if finding.get("path"):
                yield f"  Source: {finding['path']}"
            if finding.get("hint"):
                yield f"  How to fix: {finding['hint']}"
        if output.verbose:
            for source in data["sources"]:
                yield json.dumps(source, ensure_ascii=False, sort_keys=True)
    elif kind == "write":
        if data["persisted"]:
            yield f"Memory note written to: {data.get('filepath')}"
        else:
            yield "Note not written"
        yield from _fields({key: data[key] for key in ("admission", "reasons", "content_changed", "is_sanitized") if key in data}, "  ")
    elif kind == "skills.list":
        yield from data
    elif kind == "skills.install":
        yield f"{len(data['paths'])} procedural anchors installed at {data['storage_dir']}:"
        yield from data['paths']
    elif kind == "start":
        yield f"Information need: {data['information_need']}"
        yield f"Planned search: {data['retrieval_query']}"
        yield "Stores queried: " + ", ".join(data['stores_queried'])
        yield f"Raw memories retrieved: {len(data['raw_memories'])}"
        yield "Assisted context:"
        yield data['consolidated_context']
    elif kind == "config.show":
        yield from _fields(data['storage_selection'])
    elif kind == "config.list":
        for store in data['stores']:
            yield f"{store['name']}\t{store['store_id']}\t{store['storage_dir']}"
        if not data['stores']:
            yield "No global stores are registered."
    elif kind == "config.unregister":
        yield f"Unregistered {data['removed_registry_name']!r}; only registry metadata was removed."
        yield f"Store retained: {data['storage_dir']}"
    elif kind == "version":
        yield f"tessera {data['version']}"
    elif kind == "banner":
        yield f"Tessera — {data['tagline']}"
    elif kind == "update":
        yield f"Update available: {data['installed']} -> {data['latest']}" if data['latest'] else "No newer release found (update check is best-effort)."
    elif kind == "decompose":
        yield f"{len(data['filepaths'])} atomic memory/memories extracted and written:"
        yield from data['filepaths']
        if output.verbose:
            yield from _fields(data['decomposition'])
    elif kind == "init.cancelled":
        yield "Initialization cancelled; no files were changed."
    elif kind == "init":
        if data.get('applied'):
            r = data['result']
            yield f"TESSERA configured {r['storage_selection']['storage_dir']}"
            yield f"{r['indexed_nodes']} nodes indexed from {len(r['indexed_sources'])} selected files"
            for warning in r.get('processing_warnings', []):
                yield f"Warning: {warning}"
            yield "Source files modified: 0"
            yield 'Next: tessera doctor, tessera index, or tessera query "..."'
        else:
            yield from _fields(data)
    elif kind == "quickstart":
        yield f"Project: {data['project_root']}"
        yield f"Store: {data['storage_dir']}"
        yield "MCP configuration (not installed automatically):"
        yield json.dumps(data['mcp_config_block'], indent=2, ensure_ascii=False)
        yield from (line.replace('nodes indexados', 'nodes indexed') for line in data['actions_taken'])
    else:
        yield from _fields(data) if isinstance(data, dict) else (str(data),)


class PlainRenderer:
    def __init__(self, output=None):
        self.output = output or policy()

    def render(self, result):
        stream = sys.stderr if result.kind == "error" or (result.kind == "write" and result.exit_code) else sys.stdout
        for line in human_lines(result, self.output):
            print(safe_text(line, self.output), file=stream)


class RichRenderer(PlainRenderer):
    def render(self, result):
        try:
            from rich.console import Console
            from rich.text import Text
        except ImportError:
            return super().render(result)
        stream = sys.stderr if result.kind == "error" or (result.kind == "write" and result.exit_code) else sys.stdout
        console = Console(file=stream, width=self.output.width, no_color=not self.output.color, force_terminal=self.output.color)
        for index, line in enumerate(human_lines(result, self.output)):
            console.print(Text(safe_text(line, self.output), style=("bold red" if result.kind == "error" else "bold cyan") if index == 0 else None))


class JsonRenderer:
    def render(self, result):
        # ASCII escapes keep JSON safe even in ASCII-only terminals, with lossless decoding.
        print(json.dumps(result.data, ensure_ascii=True, sort_keys=True, allow_nan=False))


def emit(args, kind, data, exit_code=0):
    output = OutputPolicy.detect(args)
    renderer = JsonRenderer() if output.mode == "json" else RichRenderer(output) if output.mode == "rich" else PlainRenderer(output)
    renderer.render(CommandResult(kind, data, exit_code))
    return exit_code


def event(value: UiEvent):
    output = policy()
    if value.level == "information" and (output.quiet or not output.verbose):
        return
    message = MESSAGES.get(value.code, value.code)
    fields = "; ".join(f"{key}={value}" for key, value in value.fields.items())
    print(safe_text(f"{value.level}: {message}" + (f" ({fields})" if fields else "")), file=sys.stderr)


def say(message="", *, file=None):
    """Human interaction adapter: safe text, width-aware in Rich, no markup."""
    output = policy()
    stream = file or sys.stdout
    if output.mode == "rich":
        try:
            from rich.console import Console
            from rich.text import Text
            Console(file=stream, width=output.width, no_color=not output.color,
                    force_terminal=output.color).print(Text(safe_text(message, output)))
            return
        except ImportError:
            pass
    print(safe_text(message, output), file=stream)


def prompt_input(message):
    if not policy().interactive:
        raise CliFailure("interaction_required", "This operation needs an interactive terminal.", exit_code=2)
    return input(safe_text(message))


@contextmanager
def stage(code, *, delay=0.3):
    """One delayed, stable progress line; no live region or cursor manipulation.

    Fast operations stay silent. A completed/cancelled stage cannot leave a
    timer printing into the next command. JSON diagnostics require --verbose.
    """
    import threading
    current = policy()
    if current.quiet or (current.mode == "json" and not current.verbose):
        yield
        return
    def report():
        with output_policy(current):
            event(UiEvent(code, level="progress"))
    timer = threading.Timer(delay, report)
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
        timer.join()


class SafeDiagnostics:
    """Sanitize legacy domain diagnostics without changing their destination."""
    def __init__(self, stream, output):
        self.stream, self.output = stream, output

    def write(self, text):
        self.stream.write(safe_text(text, self.output))
        return len(text)

    def flush(self):
        return self.stream.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)
