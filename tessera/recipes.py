"""Opt-in, read-only composition experiment (#258); not a semantic API.

Only the fixed operations below are executable. No discovery, provider, plugin,
write, index-build, persisted checkpoint, or user-defined callable is supported.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

import yaml

from . import __version__


class RecipeError(ValueError):
    """Safe machine code, never source content or an underlying exception."""


@dataclass(frozen=True)
class Field:
    kind: str
    choices: Tuple[str, ...] = ()

    def validate(self, value: Any) -> None:
        valid = {
            "text": type(value) is str and 0 < len(value) <= 4096,
            "integer": type(value) is int and 1 <= value <= 50,
            "boolean": type(value) is bool,
            "drawer": type(value) is str and value in self.choices,
        }.get(self.kind, False)
        if not valid:
            raise RecipeError("INVALID_FIELD")


TEXT = Field("text")
INTEGER = Field("integer")
BOOLEAN = Field("boolean")
DRAWER = Field("drawer", ("facts", "preferences", "insights"))
_FIELDS = {field.kind: field for field in (TEXT, INTEGER, BOOLEAN, DRAWER)}
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")


@dataclass(frozen=True)
class PrimitiveDescriptor:
    name: str
    version: int
    owner: str
    operation: str
    input_schema: Tuple[Tuple[str, Field], ...]
    output_schema: str
    effects: Tuple[str, ...]
    deterministic: bool = True  # Given the same Engine/source state.
    network: bool = False
    writes_canonical_state: bool = False


_QUERY_FIELDS = (("query", TEXT), ("top_n", INTEGER), ("resolve_conflicts", BOOLEAN))
_DESCRIPTORS = (
    PrimitiveDescriptor("query", 1, "issue-68", "TesseraEngine.retrieve_context_contract",
                        _QUERY_FIELDS, "retrieval_hits.v1", ("read_memory", "read_source"), deterministic=False),
    PrimitiveDescriptor("query_store", 1, "issue-120", "TesseraEngine.retrieve_from_store",
                        _QUERY_FIELDS + (("store", DRAWER),), "retrieval_hits.v1",
                        ("read_memory", "read_source"), deterministic=False),
    PrimitiveDescriptor("ledger_for_memory", 1, "issue-11", "EvidenceLedger.for_memory",
                        (("memory_id", TEXT),), "evidence_records.v1", ("read_memory",)),
)
_EFFECTS = frozenset({"read_memory", "read_source"})


class PrimitiveRegistry:
    """A closed catalogue, deliberately without a registration/import method."""

    def descriptors(self) -> Tuple[PrimitiveDescriptor, ...]:
        return _DESCRIPTORS

    def resolve(self, name: str, version: int) -> PrimitiveDescriptor:
        for descriptor in _DESCRIPTORS:
            if descriptor.name == name and type(version) is int and version == descriptor.version:
                return descriptor
        raise RecipeError("UNAVAILABLE_PRIMITIVE_VERSION")


def _json(value: Any, *, output: bool = False) -> bytes:
    def encode_extra(item):
        # Current source frontmatter may contain SafeLoader date values. Keep
        # the Python payload untouched and hash the CLI/MCP string convention.
        if output and isinstance(item, (dt.date, dt.datetime)):
            return str(item)
        raise TypeError("unsupported value")
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False, default=encode_extra).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise RecipeError("NON_JSON_VALUE") from exc


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value)).hexdigest()


def _keys(value: Any, required: set) -> None:
    if type(value) is not dict or set(value) != required:
        raise RecipeError("INVALID_SCHEMA")


def _identifier(value: Any) -> None:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise RecipeError("INVALID_IDENTIFIER")


class _Loader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if type(key) is not str or key in result:
            raise RecipeError("INVALID_OR_DUPLICATE_KEY")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


@dataclass(frozen=True)
class RecipeDefinition:
    # Immutable bytes prevent mutating a previously approved definition in place.
    document: bytes
    source: str

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.document).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.document)


def load_recipe(text: str) -> RecipeDefinition:
    """Parse supplied YAML bytes; never load a filename, URL, or discovered repo.

    Returns an untrusted definition. Execution requires approval of its exact
    normalized-definition fingerprint; planning remains available before approval.
    """
    if type(text) is not str:
        raise RecipeError("INVALID_YAML")
    try:
        raw = text.encode("utf-8")
    except UnicodeError as exc:
        raise RecipeError("INVALID_YAML") from exc
    if len(raw) > 32768:
        raise RecipeError("DEFINITION_BUDGET_EXCEEDED")
    try:
        depth = 0
        for count, event in enumerate(yaml.parse(text)):
            if count >= 2048:
                raise RecipeError("DEFINITION_BUDGET_EXCEEDED")
            if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None):
                raise RecipeError("YAML_ALIASES_UNSUPPORTED")
            if getattr(event, "tag", None):
                raise RecipeError("YAML_TAGS_UNSUPPORTED")
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                if depth > 12:
                    raise RecipeError("DEFINITION_BUDGET_EXCEEDED")
            if isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        value = yaml.load(text, Loader=_Loader)
    except RecipeError:
        raise
    except (yaml.YAMLError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise RecipeError("INVALID_YAML") from exc
    definition = RecipeDefinition(_json(value), "external")
    _validate(definition)
    return definition


def _ref_type(value: Any, inputs: Mapping[str, Field], steps: Mapping[str, str]) -> Field:
    _keys(value, {"ref"})
    ref = value["ref"]
    if type(ref) is not str:
        raise RecipeError("INVALID_REFERENCE")
    parts = ref.split(".")
    if len(parts) == 2 and parts[0] == "inputs" and parts[1] in inputs:
        return inputs[parts[1]]
    # Only the documented typed ID field is wireable from retrieval outputs.
    # No attribute access, arbitrary JSON traversal, forward edges, or cycles.
    if (len(parts) == 5 and parts[0] == "steps" and
            steps.get(parts[1]) == "retrieval_hits.v1" and parts[2] == "hits" and
            re.fullmatch(r"0|[1-9][0-9]?", parts[3]) and int(parts[3]) < 50 and parts[4] == "id"):
        return TEXT
    raise RecipeError("INVALID_REFERENCE")


def _validate(definition: RecipeDefinition) -> Dict[str, Any]:
    value = definition.to_dict()
    _keys(value, {"name", "version", "inputs", "requires", "budgets", "steps", "outputs"})
    _identifier(value["name"])
    if type(value["version"]) is not int or value["version"] != 1:
        raise RecipeError("UNSUPPORTED_RECIPE_VERSION")
    if type(value["inputs"]) is not dict or len(value["inputs"]) > 16:
        raise RecipeError("INVALID_SCHEMA")
    fields = {}
    for name, kind in value["inputs"].items():
        _identifier(name)
        if type(kind) is not str or kind not in _FIELDS:
            raise RecipeError("INVALID_SCHEMA")
        fields[name] = _FIELDS[kind]
    required = value["requires"]
    if (type(required) is not list or any(type(x) is not str for x in required) or
            len(set(required)) != len(required) or not set(required) <= _EFFECTS):
        raise RecipeError("UNKNOWN_EFFECT")
    budgets = value["budgets"]
    _keys(budgets, {"max_steps", "max_seconds", "max_output_bytes"})
    for name, maximum in (("max_steps", 16), ("max_seconds", 30), ("max_output_bytes", 262144)):
        if type(budgets[name]) is not int or not 1 <= budgets[name] <= maximum:
            raise RecipeError("INVALID_BUDGET")
    if type(value["steps"]) is not list or not 1 <= len(value["steps"]) <= budgets["max_steps"]:
        raise RecipeError("STEP_BUDGET_EXCEEDED")
    schemas = {}
    effects = set()
    for step in value["steps"]:
        _keys(step, {"id", "use", "version", "with", "on_error"})
        _identifier(step["id"])
        if step["id"] in schemas or step["on_error"] != "stop":
            raise RecipeError("INVALID_STEP")
        descriptor = PrimitiveRegistry().resolve(step["use"], step["version"])
        fields_for_step = dict(descriptor.input_schema)
        _keys(step["with"], set(fields_for_step))
        for key, field in fields_for_step.items():
            argument = step["with"][key]
            if type(argument) is dict:
                if _ref_type(argument, fields, schemas) != field:
                    raise RecipeError("REFERENCE_TYPE_MISMATCH")
            else:
                field.validate(argument)
        effects.update(descriptor.effects)
        schemas[step["id"]] = descriptor.output_schema
    if effects != set(required):
        raise RecipeError("EFFECT_DECLARATION_MISMATCH")
    if (type(value["outputs"]) is not list or not value["outputs"] or
            any(type(item) is not str or item not in schemas for item in value["outputs"]) or
            len(value["outputs"]) != len(set(value["outputs"]))):
        raise RecipeError("INVALID_OUTPUTS")
    return value


def builtin_recipe(name: str) -> RecipeDefinition:
    """Two testable compositions, not new relevance or evidence semantics."""
    common = {"version": 1, "inputs": {"query": "text"},
              "requires": ["read_memory", "read_source"],
              "budgets": {"max_steps": 2, "max_seconds": 30, "max_output_bytes": 262144}}
    args = {"query": {"ref": "inputs.query"}, "top_n": 1, "resolve_conflicts": True}
    def step(identifier, operation, arguments):
        return {"id": identifier, "use": operation, "version": 1,
                "with": arguments, "on_error": "stop"}
    if name == "search_and_provenance":
        steps = [step("search", "query", args), step("provenance", "ledger_for_memory",
                 {"memory_id": {"ref": "steps.search.hits.0.id"}})]
    elif name == "compare_drawers":
        steps = [step(store, "query_store", dict(args, store=store)) for store in ("facts", "preferences")]
    else:
        raise RecipeError("UNKNOWN_BUILTIN")
    value = dict(common, name=name, steps=steps, outputs=[step["id"] for step in steps])
    raw = _json(value)
    definition = RecipeDefinition(raw, "builtin")
    _validate(definition)
    return definition


def _resolve(argument: Any, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> Any:
    if type(argument) is not dict:
        return argument
    parts = argument["ref"].split(".")
    if parts[0] == "inputs":
        return inputs[parts[1]]
    try:
        return outputs[parts[1]]["hits"][int(parts[3])]["id"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RecipeError("REFERENCE_UNAVAILABLE") from exc


class RecipeRunner:
    """Binds to one explicitly initialized Engine. It never constructs one.

    Cancellation and timeouts are cooperative, checked at step boundaries.
    An in-flight synchronous read cannot be preempted or rolled back. Callers
    must serialize access to the bound Engine, as with its direct public API.
    """

    def __init__(self, engine, *, capabilities=("read_memory", "read_source")):
        if not set(capabilities) <= _EFFECTS:
            raise RecipeError("UNKNOWN_EFFECT")
        self.engine = engine
        self.capabilities = frozenset(capabilities)
        self._roots = tuple(Path(root.path).resolve() for root in engine.source_roots) or (Path(engine.storage_dir).resolve(),)
        self._store = Path(engine.storage_dir).resolve()

    def plan(self, definition: RecipeDefinition, inputs: Dict[str, Any]) -> Dict[str, Any]:
        recipe = _validate(definition)
        if definition.source == "builtin" and definition != builtin_recipe(recipe["name"]):
            raise RecipeError("BUILTIN_DEFINITION_MISMATCH")
        _keys(inputs, set(recipe["inputs"]))
        for key, kind in recipe["inputs"].items():
            _FIELDS[kind].validate(inputs[key])
        if not set(recipe["requires"]) <= self.capabilities:
            raise RecipeError("MISSING_CAPABILITY")
        return {
            "schema_version": 1, "recipe": recipe["name"], "recipe_version": recipe["version"],
            "definition_hash": _hash(recipe), "source": definition.source,
            "source_fingerprint": definition.fingerprint, "input_hash": _hash(inputs),
            "tessera_version": __version__,
            "registry_hash": _hash([asdict(item) for item in _DESCRIPTORS]),
            "primitive_versions": [{"name": step["use"], "version": step["version"]} for step in recipe["steps"]],
            "effects": recipe["requires"], "canonical_state_affected": [],
            "source_roots": [str(root) for root in self._roots], "network": False,
            "provider": None, "source_preflight_max_bytes": 8 * 1024 * 1024,
            "budgets": recipe["budgets"], "max_primitive_calls": len(recipe["steps"]),
            "confirmation_gates": ["exact_external_fingerprint"] if definition.source != "builtin" else [],
            "timeout_policy": "cooperative_between_reads", "resume_policy": "unsupported_replay_read_only",
        }

    def _check_scope(self) -> None:
        roots = tuple(Path(root.path).resolve() for root in self.engine.source_roots) or (Path(self.engine.storage_dir).resolve(),)
        if roots != self._roots or Path(self.engine.storage_dir).resolve() != self._store:
            raise RecipeError("SCOPE_CHANGED")
        # Validate every path retrieval may read, including segment parents.
        total = 0
        counted = set()
        for _, node in self.engine.graph.nodes(data=True):
            if not node.get("filepath"):
                continue
            path = Path(node["filepath"])
            if any(parent.is_symlink() for parent in (path, *path.parents)):
                raise RecipeError("UNSAFE_SOURCE_PATH")
            resolved = path.resolve()
            if not any(resolved == root or root in resolved.parents for root in self._roots):
                raise RecipeError("UNSAFE_SOURCE_PATH")
            if path.exists():
                if not path.is_file():
                    raise RecipeError("UNSAFE_SOURCE_PATH")
                if resolved in counted:
                    continue
                counted.add(resolved)
                total += path.stat().st_size
                if total > 8 * 1024 * 1024:
                    raise RecipeError("SOURCE_READ_BUDGET_EXCEEDED")

    def _invoke(self, descriptor: PrimitiveDescriptor, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if descriptor.name == "query":
            return {"hits": self.engine.retrieve_context_contract(
                query_text=arguments["query"], top_n=arguments["top_n"],
                resolve_conflicts=arguments["resolve_conflicts"])}
        if descriptor.name == "query_store":
            return {"hits": self.engine.retrieve_from_store(
                query_text=arguments["query"], top_n=arguments["top_n"],
                resolve_conflicts=arguments["resolve_conflicts"], store=arguments["store"])}
        return {"records": [record.to_dict() for record in
                            self.engine.evidence_ledger.for_memory(arguments["memory_id"])]}

    def run(self, definition: RecipeDefinition, inputs: Dict[str, Any], *,
            approved_fingerprint: Optional[str] = None, cancelled: Optional[Callable[[], bool]] = None,
            resume: Any = None) -> Dict[str, Any]:
        _keys(inputs, set(_validate(definition)["inputs"]))
        inputs = dict(inputs)  # Scalar values: caller changes cannot invalidate the input hash.
        plan = self.plan(definition, inputs)
        if resume is not None:
            raise RecipeError("RESUME_UNSUPPORTED")
        if definition.source != "builtin" and approved_fingerprint != definition.fingerprint:
            raise RecipeError("UNTRUSTED_RECIPE")
        recipe = definition.to_dict()
        outputs, journal = {}, []
        started, total_bytes = time.monotonic(), 0
        status, error = "completed", None
        def interruption():
            nonlocal error
            try:
                if cancelled and cancelled():
                    return "cancelled"
            except Exception:
                error = "CANCEL_CHECK_FAILED"
                return "failed"
            if time.monotonic() - started >= recipe["budgets"]["max_seconds"]:
                return "timed_out"
            return None

        for step in recipe["steps"]:
            stopped = interruption()
            if stopped:
                status = stopped
                break
            entry = {"step": step["id"], "primitive": step["use"], "version": step["version"], "status": "failed",
                     "invoked": False, "returned": False}
            try:
                self._check_scope()
                descriptor = PrimitiveRegistry().resolve(step["use"], step["version"])
                args = {key: _resolve(value, inputs, outputs) for key, value in step["with"].items()}
                for key, field in descriptor.input_schema:
                    field.validate(args[key])
                entry["invoked"] = True
                result = self._invoke(descriptor, args)
                entry["returned"] = True
                key = "hits" if descriptor.output_schema == "retrieval_hits.v1" else "records"
                _keys(result, {key})
                if type(result[key]) is not list or any(type(item) is not dict for item in result[key]):
                    raise RecipeError("INVALID_PRIMITIVE_OUTPUT")
                if key == "hits":
                    if len(result[key]) > args["top_n"] or any(
                        type(item.get("id")) is not str or type(item.get("body")) is not str or
                        type(item.get("score")) not in (int, float) for item in result[key]
                    ):
                        raise RecipeError("INVALID_PRIMITIVE_OUTPUT")
                elif any(type(item.get("evidence_id")) is not str or
                         type(item.get("memory_id")) is not str or
                         type(item.get("source")) is not dict or
                         type(item.get("schema_version")) is not int or
                         item["schema_version"] != 1 for item in result[key]):
                    raise RecipeError("INVALID_PRIMITIVE_OUTPUT")
                encoded = _json(result, output=True)
                total_bytes += len(encoded)
                if total_bytes > recipe["budgets"]["max_output_bytes"]:
                    raise RecipeError("OUTPUT_BUDGET_EXCEEDED")
                outputs[step["id"]] = result
                entry.update(status="completed", output_hash=hashlib.sha256(encoded).hexdigest(), output_bytes=len(encoded))
            except RecipeError as exc:
                error = str(exc)
                entry["error"] = error
                status = "failed"
            except Exception:
                # Provider/source/exception content must not leak into the journal.
                error = "PRIMITIVE_FAILED"
                entry["error"] = error
                status = "failed"
            journal.append(entry)
            if status == "failed":
                break
            stopped = interruption()
            if stopped:
                status = stopped
                break
        return {"schema_version": 1, "plan": plan, "status": status, "error": error,
                "journal": journal, "outputs": {key: outputs[key] for key in recipe["outputs"] if key in outputs},
                "completed_steps": len(outputs), "canonical_mutations": 0, "resumable": False}
