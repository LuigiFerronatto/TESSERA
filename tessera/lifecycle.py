"""Experimental provider-neutral lifecycle boundary (#196).

No Engine, provider, filesystem writer, model or admission dependency belongs here.
A context catalog is an explicitly supplied, already-built read snapshot, not the
future Working Context / Context Compiler. Capture and boundaries never save LTM.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

SCHEMA_VERSION = 1
MAX_EVENT_BYTES = 131072
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}$")


class LifecycleError(ValueError):
    """A stable diagnostic code, never raw provider text or exception details."""


def identifier(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise LifecycleError("invalid_identifier")
    return value


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise LifecycleError("invalid_json") from None


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class EventType(str, Enum):
    SESSION_STARTED = "runtime_session_started"
    SESSION_RESUMED = "runtime_session_resumed"
    SESSION_ENDED = "runtime_session_ended"
    INPUT = "task_input_received"
    BEFORE_REASONING = "before_reasoning"
    TOOL_STARTED = "tool_call_started"
    TOOL_COMPLETED = "tool_call_completed"
    TOOL_FAILED = "tool_call_failed"
    AFTER_REASONING = "after_reasoning"
    TURN_COMPLETED = "turn_completed"
    SUBAGENT_STARTED = "subagent_started"
    SUBAGENT_COMPLETED = "subagent_completed"
    COMPACTION_BEFORE = "context_compaction_before"
    COMPACTION_AFTER = "context_compaction_after"
    ERROR = "runtime_error"


@dataclass(frozen=True)
class ProjectBinding:
    """An explicit configured scope. Constructing/resolving it creates no files."""
    scope_id: str
    root: Optional[str] = None
    global_scope: bool = False

    def __post_init__(self):
        identifier(self.scope_id)
        if type(self.global_scope) is not bool:
            raise LifecycleError("invalid_scope_binding")
        if self.global_scope != (self.root is None):
            raise LifecycleError("invalid_scope_binding")
        if self.root is not None and not Path(self.root).is_absolute():
            raise LifecycleError("project_root_must_be_absolute")


def resolve_binding(bindings: Iterable[ProjectBinding], *, cwd: str,
                    explicit_scope: Optional[str] = None,
                    provider_root: Optional[str] = None,
                    global_scope: Optional[str] = None) -> Optional[ProjectBinding]:
    """Resolve only an explicit allow-list; never discover stores or scan home.

    Explicit scope, exact provider root, then nearest configured enclosing root.
    A named global scope is opt-in and only used without a project match. Resolve
    real paths on this host so symlink/.. escapes cannot join an unrelated scope.
    The #117 resolver may prepare these bindings; no environment fallback occurs.
    """
    choices = tuple(bindings)
    if len(choices) > 64 or len({b.scope_id for b in choices}) != len(choices):
        raise LifecycleError("invalid_binding_registry")
    if not Path(cwd).is_absolute():
        raise LifecycleError("cwd_must_be_absolute")
    current = Path(cwd).resolve()
    roots = {b.scope_id: Path(b.root).resolve() for b in choices if b.root}

    def contained(binding):
        root = roots.get(binding.scope_id)
        return root is not None and (current == root or root in current.parents)

    if explicit_scope is not None:
        selected = next((b for b in choices if b.scope_id == explicit_scope), None)
        if selected is None or (not selected.global_scope and not contained(selected)):
            raise LifecycleError("explicit_scope_mismatch")
        return selected
    if provider_root is not None:
        if not Path(provider_root).is_absolute():
            raise LifecycleError("provider_root_must_be_absolute")
        root = Path(provider_root).resolve()
        matches = [b for b in choices if roots.get(b.scope_id) == root and contained(b)]
        if len(matches) > 1:
            raise LifecycleError("ambiguous_scope")
        # An unmatched provider root must not silently fall back to another store.
        return matches[0] if matches else None
    matches = sorted((b for b in choices if contained(b)),
                     key=lambda b: len(roots[b.scope_id].parts), reverse=True)
    if len(matches) > 1 and roots[matches[0].scope_id] == roots[matches[1].scope_id]:
        raise LifecycleError("ambiguous_scope")
    if matches:
        return matches[0]
    if global_scope is not None:
        for b in choices:
            if b.scope_id == global_scope and b.global_scope:
                return b
        raise LifecycleError("unknown_global_scope")
    return None


@dataclass(frozen=True)
class Identities:
    runtime_session_id: str
    tessera_run_id: str
    turn_id: Optional[str] = None
    provider_task_id: Optional[str] = None
    tessera_episode_id: Optional[str] = None
    subagent_id: Optional[str] = None
    parent_run_id: Optional[str] = None
    parent_turn_id: Optional[str] = None

    def __post_init__(self):
        identifier(self.runtime_session_id)
        identifier(self.tessera_run_id)
        for value in asdict(self).values():
            if value is not None:
                identifier(value)
        if bool(self.parent_run_id) != bool(self.parent_turn_id):
            raise LifecycleError("incomplete_parent_lineage")
        if self.parent_run_id == self.tessera_run_id:
            raise LifecycleError("self_parent_run")
        if self.subagent_id is not None and self.parent_run_id is None:
            raise LifecycleError("missing_parent_lineage")


@dataclass(frozen=True)
class Capabilities:
    can_inject_context: bool = False
    can_block: bool = False
    can_rewrite: bool = False
    synchronous: bool = True

    def __post_init__(self):
        if any(type(v) is not bool for v in asdict(self).values()):
            raise LifecycleError("invalid_capabilities")


@dataclass(frozen=True)
class LifecycleEvent:
    event_id: str
    canonical_type: EventType
    identities: Identities
    scope: Optional[ProjectBinding]
    sequence: int
    occurred_at: str
    runtime: str
    provider_event: str
    adapter_version: str
    payload_json: str = "{}"
    capabilities: Capabilities = field(default_factory=Capabilities)
    runtime_version: Optional[str] = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        if not isinstance(self.identities, Identities) or not isinstance(self.capabilities, Capabilities):
            raise LifecycleError("invalid_event_envelope")
        if self.scope is not None and not isinstance(self.scope, ProjectBinding):
            raise LifecycleError("invalid_event_envelope")
        if self.runtime_version is not None and (not isinstance(self.runtime_version, str) or len(self.runtime_version) > 128):
            raise LifecycleError("invalid_runtime_version")
        for value in (self.event_id, self.runtime, self.provider_event, self.adapter_version):
            identifier(value)
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION or not isinstance(self.canonical_type, EventType):
            raise LifecycleError("unsupported_event_schema")
        if type(self.sequence) is not int or self.sequence < 0:
            raise LifecycleError("invalid_sequence")
        try:
            stamp = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
            if stamp.utcoffset() is None:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise LifecycleError("invalid_timestamp") from None
        try:
            value = json.loads(self.payload_json)
        except (TypeError, ValueError, RecursionError):
            raise LifecycleError("invalid_payload") from None
        if not isinstance(value, dict) or canonical_json(value) != self.payload_json:
            raise LifecycleError("payload_must_be_canonical_object")
        allowed = {"text", "tool_name", "tool_call_id", "arguments", "output", "outcome",
                   "evidence_origin_id", "trigger", "source", "boundary"}
        if set(value) - allowed:
            raise LifecycleError("unknown_payload_field")
        for key in ("tool_name", "tool_call_id", "evidence_origin_id"):
            if key in value:
                identifier(value[key])
        if "outcome" in value and value["outcome"] not in ("success", "failure", "unknown", "runtime_error"):
            raise LifecycleError("invalid_outcome")
        if "trigger" in value and value["trigger"] not in ("auto", "manual"):
            raise LifecycleError("invalid_compaction_trigger")
        if "boundary" in value and value["boundary"] not in ("response_end", "session_end"):
            raise LifecycleError("invalid_boundary")
        if "text" in value and value["text"] is not None and not isinstance(value["text"], str):
            raise LifecycleError("invalid_evidence_text")
        if len(canonical_json(self.to_dict()).encode("utf-8")) > MAX_EVENT_BYTES:
            raise LifecycleError("event_too_large")

    @property
    def payload(self) -> Dict[str, Any]:
        # A new object prevents consumers from mutating append-only evidence.
        return json.loads(self.payload_json)

    def to_dict(self):
        data = asdict(self)
        data["canonical_type"] = self.canonical_type.value
        data["payload"] = json.loads(data.pop("payload_json"))
        return data

    @classmethod
    def from_dict(cls, data):
        values = dict(data)
        values["canonical_type"] = EventType(values["canonical_type"])
        values["identities"] = Identities(**values["identities"])
        values["scope"] = ProjectBinding(**values["scope"]) if values["scope"] else None
        values["capabilities"] = Capabilities(**values["capabilities"])
        values["payload_json"] = canonical_json(values.pop("payload"))
        return cls(**values)


# Text capture is disabled by default. Opt-in capture applies best-effort
# credential scrubbing; it is not a universal secret-detection guarantee.
_SECRET_KEY = re.compile(r"password|secret|token|authorization|cookie|api.?key|credential", re.I)
_SECRET_VALUE = re.compile(
    r"(?i)(?:bearer\s+[a-z0-9._~+/=-]+|(?:api[_-]?key|password|secret|token)\s*[:=]\s*[^\s,;]+|"
    r"sk-[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9]{8,})")
_TEXT_FIELDS = {"text", "input", "output", "summary", "error", "arguments"}


@dataclass(frozen=True)
class CapturePolicy:
    include_content: bool = False
    max_depth: int = 12

    def __post_init__(self):
        if type(self.include_content) is not bool or type(self.max_depth) is not int or not 1 <= self.max_depth <= 32:
            raise LifecycleError("invalid_capture_policy")

    def sanitize(self, value, key="", depth=0):
        if depth > self.max_depth:
            return "[omitted:depth]"
        if _SECRET_KEY.search(key):
            return "[redacted]"
        if key in _TEXT_FIELDS and not self.include_content:
            return "[omitted:content-policy]"
        if isinstance(value, dict):
            return {k: self.sanitize(v, k, depth + 1) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize(v, key, depth + 1) for v in value]
        if isinstance(value, str):
            if "PRIVATE KEY-----" in value:
                return "[redacted]"
            return _SECRET_VALUE.sub("[redacted]", value)
        return value

    def redact(self, event: LifecycleEvent) -> LifecycleEvent:
        return replace(event, payload_json=canonical_json(self.sanitize(event.payload)))


class RunBuffer:
    """Bounded append-only, in-memory evidence; snapshots are derived, not LTM.

    The caller owns one serialized buffer per run. On overflow reject the new
    event, keep previous evidence and report degradation; never silently evict.
    No raw event or raw digest is retained. A checkpoint is returned as bytes,
    not written anywhere. Consumers must explicitly choose its storage policy.
    """
    def __init__(self, run_id: str, scope: ProjectBinding, *, max_events=256,
                 max_bytes=1048576, capture_policy=None):
        self.run_id = identifier(run_id)
        self.scope = scope
        if type(max_events) is not int or not 1 <= max_events <= 4096:
            raise LifecycleError("invalid_event_budget")
        if type(max_bytes) is not int or not 1024 <= max_bytes <= 16777216:
            raise LifecycleError("invalid_byte_budget")
        self.max_events, self.max_bytes = max_events, max_bytes
        self.capture_policy = capture_policy or CapturePolicy()
        self._events = []
        self._seen = {}
        self._bytes = 0
        self.state = "open"
        self._session = None

    @property
    def events(self) -> Tuple[LifecycleEvent, ...]:
        return tuple(self._events)

    def append(self, event: LifecycleEvent) -> str:
        # Policy is applied before IDs/digests enter any journal state.
        safe = self.capture_policy.redact(event)
        if (safe.identities.tessera_run_id != self.run_id and safe.identities.parent_run_id != self.run_id) or safe.scope != self.scope:
            raise LifecycleError("run_scope_mismatch")
        session = (safe.runtime, safe.identities.runtime_session_id)
        if self._session is not None and session != self._session:
            raise LifecycleError("session_identity_mismatch")
        encoded = canonical_json(safe.to_dict()).encode("utf-8")
        fingerprint = hashlib.sha256(encoded).hexdigest()
        if safe.event_id in self._seen:
            if self._seen[safe.event_id] != fingerprint:
                raise LifecycleError("event_id_collision")
            return "duplicate"
        if self.state == "closed":
            raise LifecycleError("run_closed")
        if self._events and safe.sequence <= self._events[-1].sequence:
            raise LifecycleError("out_of_order")
        if len(self._events) >= self.max_events or self._bytes + len(encoded) > self.max_bytes:
            raise LifecycleError("capture_budget_exceeded")
        self._session = session
        self._events.append(safe)
        self._seen[safe.event_id] = fingerprint
        self._bytes += len(encoded)
        if safe.canonical_type == EventType.TURN_COMPLETED:
            self.state = "quiescent"
        elif safe.canonical_type == EventType.SESSION_ENDED and safe.identities.tessera_run_id == self.run_id:
            self.state = "closed"
        elif safe.canonical_type == EventType.ERROR:
            self.state = "failed"
        elif safe.canonical_type in (EventType.INPUT, EventType.SESSION_RESUMED):
            self.state = "open"
        return "appended"

    def checkpoint(self) -> bytes:
        return canonical_json({"schema_version": SCHEMA_VERSION, "run_id": self.run_id,
                               "scope": asdict(self.scope), "state": self.state,
                               "events": [e.to_dict() for e in self.events]}).encode("utf-8")

    @classmethod
    def restore(cls, checkpoint: bytes, *, capture_policy=None, **budgets):
        # Check serialized input before JSON parsing. No unbounded replay.
        if len(checkpoint) > budgets.get("max_bytes", 1048576) + budgets.get("max_events", 256) + 2048:
            raise LifecycleError("checkpoint_too_large")
        try:
            data = json.loads(checkpoint)
            if data["schema_version"] != SCHEMA_VERSION:
                raise LifecycleError("unsupported_checkpoint_schema")
            result = cls(data["run_id"], ProjectBinding(**data["scope"]),
                         capture_policy=capture_policy, **budgets)
            for item in data["events"]:
                result.append(LifecycleEvent.from_dict(item))
            if result.state != data["state"]:
                raise LifecycleError("checkpoint_state_mismatch")
            return result
        except (KeyError, TypeError, ValueError, RecursionError):
            raise LifecycleError("invalid_checkpoint") from None

    def episode_inputs(self):
        """Evidence groups for #138/#137, not constructed/admitted episodes.

        Only explicit origin IDs coalesce child evidence and a parent echo.
        Equal text alone is never proof of shared lineage. All event references
        survive; an omitted origin gets its own event-specific evidence group.
        """
        groups = {}
        for event in self.events:
            if event.canonical_type not in (EventType.INPUT, EventType.TOOL_COMPLETED,
                                            EventType.TOOL_FAILED, EventType.AFTER_REASONING,
                                            EventType.SUBAGENT_COMPLETED):
                continue
            key = event.payload.get("evidence_origin_id") or event.event_id
            entry = groups.setdefault(key, {"origin_id": key, "event_ids": [],
                                            "observations": [], "lineage": []})
            entry["event_ids"].append(event.event_id)
            observation = {k: v for k, v in event.payload.items() if k != "evidence_origin_id"}
            if observation not in entry["observations"]:
                entry["observations"].append(observation)
            lineage = asdict(event.identities)
            if lineage not in entry["lineage"]:
                entry["lineage"].append(lineage)
        return tuple(groups.values())


@dataclass(frozen=True)
class ContextSection:
    section_id: str
    text: str
    evidence_pointer: Optional[str] = None

    def __post_init__(self):
        identifier(self.section_id)
        if not isinstance(self.text, str) or len(self.text.encode("utf-8")) > MAX_EVENT_BYTES:
            raise LifecycleError("invalid_context_section")
        if self.evidence_pointer is not None:
            identifier(self.evidence_pointer)


@dataclass(frozen=True)
class ContextCatalog:
    """Precomputed bounded context. No synchronous AI, Engine or arbitrary callback."""
    scope_id: str
    sections: Tuple[ContextSection, ...]

    def __post_init__(self):
        identifier(self.scope_id)
        object.__setattr__(self, "sections", tuple(self.sections))
        if len(self.sections) > 64 or len({s.section_id for s in self.sections}) != len(self.sections):
            raise LifecycleError("invalid_context_catalog")
        if sum(len(s.text.encode("utf-8")) for s in self.sections) > 1048576:
            raise LifecycleError("context_catalog_too_large")


@dataclass(frozen=True)
class ExecutionPolicy:
    latency_budget_ms: int = 50
    max_context_bytes: int = 8192
    max_context_token_bound: int = 8192
    capture_failure: str = "continue"
    context_failure: str = "continue"

    def __post_init__(self):
        if type(self.latency_budget_ms) is not int or not 1 <= self.latency_budget_ms <= 1000:
            raise LifecycleError("invalid_latency_budget")
        if type(self.max_context_bytes) is not int or not 0 <= self.max_context_bytes <= MAX_EVENT_BYTES:
            raise LifecycleError("invalid_context_budget")
        if type(self.max_context_token_bound) is not int or not 0 <= self.max_context_token_bound <= MAX_EVENT_BYTES:
            raise LifecycleError("invalid_token_budget")
        if self.capture_failure not in ("continue", "raise") or self.context_failure not in ("continue", "raise"):
            raise LifecycleError("invalid_degradation_policy")


@dataclass(frozen=True)
class HookResult:
    status: str
    milestones: Tuple[str, ...] = ()
    context: str = ""
    context_bytes: int = 0
    # UTF-8 bytes are a conservative token upper bound, not provider billing.
    context_token_upper_bound: int = 0
    omitted_sections: Tuple[str, ...] = ()
    pointer_sections: Tuple[str, ...] = ()
    diagnostics: Tuple[str, ...] = ()
    deferred_effects: Tuple[str, ...] = ()
    learning_boundary: Optional[str] = None
    checkpoint: Optional[bytes] = None
    persisted: bool = False

    def __post_init__(self):
        if self.status not in ("ok", "degraded", "no_project", "duplicate") or self.persisted is not False:
            raise LifecycleError("invalid_hook_result")


class HookCore:
    """Only canonical types drive memory milestones. Provider wire rules stay out."""
    def __init__(self, buffer: RunBuffer, *, catalog=None, policy=None, clock=time.monotonic):
        self.buffer, self.catalog = buffer, catalog
        self.policy = policy or ExecutionPolicy()
        self.clock = clock

    def receive(self, event: LifecycleEvent) -> HookResult:
        started = self.clock()
        deadline = started + self.policy.latency_budget_ms / 1000
        if event.scope is None:
            return HookResult("no_project", diagnostics=("unbound_event_not_captured",))
        try:
            capture = self.buffer.append(event)
        except LifecycleError as exc:
            if self.policy.capture_failure == "raise":
                raise
            return HookResult("degraded", diagnostics=(str(exc),))
        if capture == "duplicate":
            return HookResult("duplicate")
        milestones = ["CAPTURE_EXPERIENCE"]
        diagnostics, deferred = [], []
        context, omitted, pointers = "", [], []
        checkpoint = None
        boundary = None
        kind = event.canonical_type
        if kind in (EventType.SESSION_STARTED, EventType.SESSION_RESUMED):
            deferred.append("index_health_refresh_unimplemented")
        if kind in (EventType.BEFORE_REASONING, EventType.SESSION_STARTED, EventType.SESSION_RESUMED):
            milestones.append("READ_BEFORE_REASONING")
            if not event.capabilities.can_inject_context:
                diagnostics.append("context_injection_unsupported")
            elif self.catalog is None:
                diagnostics.append("context_catalog_unavailable")
            elif self.catalog.scope_id != event.scope.scope_id:
                diagnostics.append("context_scope_mismatch")
            else:
                budget = min(self.policy.max_context_bytes, self.policy.max_context_token_bound)
                for section in self.catalog.sections:
                    if self.clock() >= deadline:
                        omitted.append(section.section_id)
                        diagnostics.append("context_deadline_exceeded")
                        continue
                    text = self.buffer.capture_policy.sanitize(section.text)
                    separator = "\n\n" if context else ""
                    if len((context + separator + text).encode("utf-8")) <= budget:
                        context += separator + text
                    else:
                        omitted.append(section.section_id)
                        if section.evidence_pointer:
                            pointer = "Evidence: " + section.evidence_pointer
                            if len((context + separator + pointer).encode("utf-8")) <= budget:
                                context += separator + pointer
                                pointers.append(section.section_id)
                if omitted:
                    diagnostics.append("context_sections_omitted")
            if diagnostics and self.policy.context_failure == "raise":
                raise LifecycleError(diagnostics[0])
        if kind == EventType.COMPACTION_BEFORE:
            checkpoint = self.buffer.checkpoint()
        if kind == EventType.COMPACTION_AFTER:
            deferred.append("context_refresh_unimplemented")
        if kind == EventType.TOOL_COMPLETED:
            deferred.append("relevant_write_validation_unimplemented")
        if kind in (EventType.TURN_COMPLETED, EventType.SESSION_ENDED):
            # This is only a signal; #138 decides if learning has occurred.
            boundary = kind.value
            deferred.extend(("episode_boundary_decision_unimplemented", "hygiene_drift_unimplemented"))
        if self.clock() > deadline:
            diagnostics.append("execution_budget_exceeded")
            context = ""  # Never inject a late packet.
            if self.catalog is not None and "READ_BEFORE_REASONING" in milestones:
                omitted = [s.section_id for s in self.catalog.sections]
                pointers = []
        count = len(context.encode("utf-8"))
        return HookResult("degraded" if diagnostics else "ok", tuple(milestones), context,
                          count, count, tuple(omitted), tuple(pointers),
                          tuple(dict.fromkeys(diagnostics)), tuple(deferred), boundary, checkpoint)
