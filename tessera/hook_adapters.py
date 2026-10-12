"""Frozen, observational provider wire adapters for the experimental Hook Core.

Profiles are snapshots of official references on 2026-10-02, not claims about
all versions. Installation, shell commands, trust review and transcript reading
belong to #177/#190. Provider names appear here, never in lifecycle semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, Mapping, Optional, Tuple

from .lifecycle import (Capabilities, EventType, HookResult, Identities, LifecycleError,
                        LifecycleEvent, MAX_EVENT_BYTES, ProjectBinding,
                        canonical_json, digest, identifier, resolve_binding)

PROFILE_VERSION = "2026-10-02.v1"
SOURCES = {
    "claude": "https://code.claude.com/docs/en/hooks",
    "codex": "https://developers.openai.com/codex/hooks",
    "gemini": "https://geminicli.com/docs/hooks/reference/",
    "copilot": "https://docs.github.com/en/copilot/reference/hooks-reference",
}

_BASE = {
    "SessionStart": (EventType.SESSION_STARTED,),
    "SessionEnd": (EventType.SESSION_ENDED,),
    "UserPromptSubmit": (EventType.INPUT, EventType.BEFORE_REASONING),
    "PreToolUse": (EventType.TOOL_STARTED,),
    "PostToolUse": (EventType.TOOL_COMPLETED,),
    "Stop": (EventType.AFTER_REASONING, EventType.TURN_COMPLETED),
    "SubagentStart": (EventType.SUBAGENT_STARTED,),
    "SubagentStop": (EventType.SUBAGENT_COMPLETED,),
    "PreCompact": (EventType.COMPACTION_BEFORE,),
    "PostCompact": (EventType.COMPACTION_AFTER,),
}
_MAPS = {
    "claude": dict(_BASE, PostToolUseFailure=(EventType.TOOL_FAILED,), StopFailure=(EventType.ERROR,)),
    "codex": dict(_BASE, Interrupt=(EventType.ERROR,)),
    "gemini": {
        "SessionStart": _BASE["SessionStart"], "SessionEnd": _BASE["SessionEnd"],
        "BeforeAgent": _BASE["UserPromptSubmit"], "BeforeTool": _BASE["PreToolUse"],
        "AfterTool": _BASE["PostToolUse"], "AfterAgent": _BASE["Stop"],
        "PreCompress": _BASE["PreCompact"],
    },
    # Deliberately one format: camelCase CLI command hooks. No inferred cloud or
    # SDK compatibility, no conflation of agentName with a unique agent ID.
    "copilot": {
        "sessionStart": _BASE["SessionStart"], "sessionEnd": _BASE["SessionEnd"],
        "userPromptSubmitted": _BASE["UserPromptSubmit"], "preToolUse": _BASE["PreToolUse"],
        "postToolUse": _BASE["PostToolUse"], "postToolUseFailure": (EventType.TOOL_FAILED,),
        "agentStop": _BASE["Stop"], "subagentStart": _BASE["SubagentStart"],
        "subagentStop": _BASE["SubagentStop"], "errorOccurred": (EventType.ERROR,),
        "preCompact": _BASE["PreCompact"],
    },
}
_CONTEXT_EVENTS = {
    "claude": {"SessionStart", "UserPromptSubmit", "SubagentStart", "PostToolUse", "PostToolUseFailure"},
    "codex": {"SessionStart", "UserPromptSubmit", "SubagentStart", "PreToolUse", "PostToolUse"},
    "gemini": {"SessionStart", "BeforeAgent", "AfterTool"},
    "copilot": {"sessionStart", "subagentStart", "postToolUse"},
}
_BLOCK_EVENTS = {
    "claude": {"UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SubagentStop"},
    "codex": {"UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SubagentStop", "PreCompact", "PostCompact"},
    "gemini": {"BeforeAgent", "BeforeTool", "AfterTool", "AfterAgent"},
    "copilot": {"preToolUse", "agentStop", "subagentStop"},
}


@dataclass(frozen=True)
class Invocation:
    """Integration-owned correlation, never inferred from prompt text or cwd.

    Persist a delivery ID/sequence on retries. Give distinct submissions distinct
    IDs even when their text is identical. Missing native turn/tool/subagent IDs
    must be assigned by the integration; this core never equates them to session.
    """
    delivery_id: str
    sequence: int
    occurred_at: str
    tessera_run_id: str
    turn_id: Optional[str] = None
    provider_task_id: Optional[str] = None
    tessera_episode_id: Optional[str] = None
    tool_call_id: Optional[str] = None
    logical_tool_name: Optional[str] = None
    evidence_origin_id: Optional[str] = None
    subagent_id: Optional[str] = None
    child_run_id: Optional[str] = None
    parent_run_id: Optional[str] = None
    parent_turn_id: Optional[str] = None
    runtime_version: Optional[str] = None

    def __post_init__(self):
        for key, value in self.__dict__.items():
            if key not in ("occurred_at", "sequence", "runtime_version") and value is not None:
                identifier(value)
        if type(self.sequence) is not int or not 0 <= self.sequence <= 2**53 // 4:
            raise LifecycleError("invalid_sequence")


@dataclass(frozen=True)
class NormalizationResult:
    events: Tuple[LifecycleEvent, ...] = ()
    diagnostics: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderResponse:
    stdout: str
    stderr: str
    exit_code: int


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LifecycleError("duplicate_json_key")
        result[key] = value
    return result


def parse_provider_input(raw: bytes) -> Dict[str, Any]:
    if len(raw) > MAX_EVENT_BYTES:
        raise LifecycleError("provider_input_too_large")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError, RecursionError):
        raise LifecycleError("invalid_provider_json") from None
    if not isinstance(payload, dict):
        raise LifecycleError("provider_input_must_be_object")
    return payload


def _string(payload, key, *, optional=False):
    value = payload.get(key)
    if optional and value is None:
        return None
    if not isinstance(value, str) or (not optional and not value):
        raise LifecycleError("invalid_provider_field:" + key)
    return value


def _text_result(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Standard MCP content, not regexes over model-facing Bash output.
        content = value.get("content")
        if isinstance(content, list):
            return "\n".join(item["text"] for item in content
                             if isinstance(item, dict) and item.get("type") == "text"
                             and isinstance(item.get("text"), str))
    return value


class FrozenHookAdapter:
    def __init__(self, runtime: str):
        if runtime not in _MAPS:
            raise LifecycleError("unsupported_runtime")
        self.runtime = runtime

    def describe(self):
        return {"runtime": self.runtime, "adapter_version": PROFILE_VERSION,
                "reference": SOURCES[self.runtime], "verified_at": "2026-10-02",
                "installation": "not_implemented", "runtime_version": "caller_supplied",
                "events": {name: {"canonical_types": [t.value for t in kinds],
                                   "capabilities": self.capabilities(name).__dict__}
                           for name, kinds in _MAPS[self.runtime].items()},
                "capability_limits": {
                    "gemini": ["no_native_subagent_pair", "no_post_compaction_event", "no_native_turn_or_tool_call_id"],
                    "copilot": ["prompt_command_output_ignored", "agent_stop_has_no_inline_final_text",
                                "subagent_start_needs_external_identity", "no_post_compaction_event"],
                    "claude": ["prompt_id_version_dependent", "no_generic_tool_output_schema"],
                    "codex": ["tool_specific_output_requires_explicit_outcome", "no_generic_task_completion"],
                }[self.runtime]}

    def capabilities(self, name):
        return Capabilities(name in _CONTEXT_EVENTS[self.runtime], name in _BLOCK_EVENTS[self.runtime],
                            name in ("PreToolUse", "BeforeTool", "preToolUse"),
                            not (self.runtime == "gemini" and name in ("PreCompress", "SessionEnd")))

    def normalize(self, name: str, payload: Mapping[str, Any], invocation: Invocation,
                  scope: Optional[ProjectBinding]) -> NormalizationResult:
        if not isinstance(payload, dict):
            raise LifecycleError("provider_input_must_be_object")
        if len(canonical_json(payload).encode("utf-8")) > MAX_EVENT_BYTES:
            raise LifecycleError("provider_input_too_large")
        kinds = _MAPS[self.runtime].get(name)
        if kinds is None:
            return NormalizationResult(diagnostics=("unsupported_provider_event",))
        camel = self.runtime == "copilot"
        session = identifier(_string(payload, "sessionId" if camel else "session_id"))
        cwd = _string(payload, "cwd")
        if scope is not None:
            resolve_binding((scope,), cwd=cwd, explicit_scope=scope.scope_id)
        if not camel:
            if _string(payload, "hook_event_name") != name:
                raise LifecycleError("provider_event_mismatch")
            _string(payload, "transcript_path")
        if self.runtime == "gemini":
            _string(payload, "timestamp")
        if camel and (type(payload.get("timestamp")) is not int or payload["timestamp"] < 0):
            raise LifecycleError("invalid_provider_field:timestamp")
        turn = payload.get("turn_id") if self.runtime == "codex" else payload.get("prompt_id") if self.runtime == "claude" else None
        if turn is not None:
            identifier(turn)
            if invocation.turn_id is not None and turn != invocation.turn_id:
                raise LifecycleError("turn_identity_mismatch")
        turn = turn or invocation.turn_id
        turn_scoped = (EventType.INPUT, EventType.TOOL_STARTED, EventType.TOOL_COMPLETED,
                       EventType.TOOL_FAILED, EventType.AFTER_REASONING,
                       EventType.SUBAGENT_STARTED, EventType.SUBAGENT_COMPLETED)
        if kinds[0] in turn_scoped and turn is None:
            raise LifecycleError("turn_identity_required")
        if self.runtime == "codex" and kinds[0] not in (EventType.SESSION_STARTED, EventType.SESSION_ENDED) and "turn_id" not in payload:
            raise LifecycleError("invalid_provider_field:turn_id")
        data = {}
        diagnostics = []
        ids = Identities(session, invocation.tessera_run_id, turn, invocation.provider_task_id,
                         invocation.tessera_episode_id, invocation.subagent_id if not invocation.child_run_id else None,
                         invocation.parent_run_id, invocation.parent_turn_id)
        if kinds[0] == EventType.SESSION_STARTED:
            source = _string(payload, "source")
            allowed = {"startup", "resume", "clear", "compact", "fork"} if self.runtime == "claude" else {"startup", "resume", "clear", "compact"} if self.runtime == "codex" else {"startup", "resume", "clear"} if self.runtime == "gemini" else {"startup", "resume", "new"}
            if source not in allowed:
                raise LifecycleError("unknown_session_source")
            if source in ("resume", "compact"):
                kinds = (EventType.SESSION_RESUMED,)
            data["source"] = source
        elif kinds[0] == EventType.SESSION_ENDED:
            _string(payload, "reason")
            # Runtime exit reason is diagnostic; it is not task success.
            data["boundary"] = "session_end"
        elif kinds[0] == EventType.INPUT:
            data["text"] = _string(payload, "prompt")
        elif kinds[0] in (EventType.TOOL_STARTED, EventType.TOOL_COMPLETED, EventType.TOOL_FAILED):
            native_name = _string(payload, "toolName" if camel else "tool_name")
            data["tool_name"] = invocation.logical_tool_name or native_name
            call_id = _string(payload, "tool_use_id") if self.runtime in ("claude", "codex") else None
            if call_id is not None and invocation.tool_call_id and call_id != invocation.tool_call_id:
                raise LifecycleError("tool_identity_mismatch")
            call_id = call_id or invocation.tool_call_id
            if call_id is None:
                raise LifecycleError("tool_identity_required")
            data["tool_call_id"] = identifier(call_id)
            args_key = "toolArgs" if camel else "tool_input"
            if args_key not in payload:
                raise LifecycleError("invalid_provider_field:" + args_key)
            data["arguments"] = payload[args_key]
            if kinds[0] != EventType.TOOL_STARTED:
                if kinds[0] == EventType.TOOL_FAILED:
                    data["output"] = _string(payload, "error")
                    data["outcome"] = "failure"
                else:
                    response_key = "toolResult" if camel else "tool_response"
                    if response_key not in payload:
                        raise LifecycleError("invalid_provider_field:" + response_key)
                    response = payload[response_key]
                    if camel:
                        if not isinstance(response, dict) or response.get("resultType") != "success":
                            raise LifecycleError("unsupported_copilot_result")
                        data["output"] = _string(response, "textResultForLlm", optional=True)
                        data["outcome"] = "success"
                    elif self.runtime == "gemini":
                        if not isinstance(response, dict):
                            raise LifecycleError("invalid_provider_field:tool_response")
                        data["output"] = response.get("llmContent")
                        data["outcome"] = "failure" if response.get("error") else "success"
                    else:
                        data["output"] = _text_result(response)
                        data["outcome"] = "success" if self.runtime == "claude" else "unknown"
                        if self.runtime == "codex" and native_name.startswith("mcp__") and isinstance(response, dict):
                            if type(response.get("isError")) is bool:
                                data["outcome"] = "failure" if response["isError"] else "success"
                        if data["outcome"] == "unknown":
                            diagnostics.append("tool_outcome_unknown")
                    if data["outcome"] == "failure":
                        kinds = (EventType.TOOL_FAILED,)
        elif kinds[0] == EventType.AFTER_REASONING:
            if type(payload.get("stop_hook_active")) is not bool:
                raise LifecycleError("invalid_provider_field:stop_hook_active")
            if self.runtime == "gemini":
                data["text"] = _string(payload, "prompt_response")
            elif camel:
                if payload.get("stopReason") != "end_turn":
                    raise LifecycleError("unsupported_stop_reason")
                diagnostics.append("final_text_unavailable_without_transcript")
            else:
                data["text"] = _string(payload, "last_assistant_message", optional=True)
            data["boundary"] = "response_end"
        elif kinds[0] in (EventType.SUBAGENT_STARTED, EventType.SUBAGENT_COMPLETED):
            if not camel:
                _string(payload, "agent_type")
                agent_id = _string(payload, "agent_id")
            else:
                _string(payload, "agentName")
                agent_id = _string(payload, "agentId") if kinds[0] == EventType.SUBAGENT_COMPLETED else invocation.subagent_id
            if not agent_id or not invocation.child_run_id or not turn:
                raise LifecycleError("subagent_lineage_required")
            if invocation.subagent_id and agent_id != invocation.subagent_id:
                raise LifecycleError("subagent_identity_mismatch")
            ids = Identities(session, invocation.child_run_id, turn, invocation.provider_task_id,
                             invocation.tessera_episode_id, agent_id, invocation.tessera_run_id, turn)
            if kinds[0] == EventType.SUBAGENT_COMPLETED:
                data["text"] = _string(payload, "response" if camel else "last_assistant_message", optional=True)
        elif kinds[0] in (EventType.COMPACTION_BEFORE, EventType.COMPACTION_AFTER):
            trigger = payload.get("trigger")
            if trigger not in ("auto", "manual"):
                raise LifecycleError("invalid_compaction_trigger")
            data["trigger"] = trigger
            # compact_summary and transcript paths are deliberately never read/captured.
        elif kinds[0] == EventType.ERROR:
            data["outcome"] = "runtime_error"
        if invocation.evidence_origin_id:
            data["evidence_origin_id"] = invocation.evidence_origin_id
        events = []
        for index, kind in enumerate(kinds):
            event_data = data
            if kind == EventType.TURN_COMPLETED:
                event_data = {"boundary": "response_end"}
            event_id = "evt_" + digest([self.runtime, PROFILE_VERSION, session,
                                       invocation.tessera_run_id, invocation.delivery_id, index])[:32]
            events.append(LifecycleEvent(event_id, kind, ids, scope, invocation.sequence * 4 + index,
                                         invocation.occurred_at, self.runtime, name, PROFILE_VERSION,
                                         canonical_json(event_data), self.capabilities(name), invocation.runtime_version))
        return NormalizationResult(tuple(events), tuple(diagnostics))

    def render_response(self, result: HookResult, provider_event: str) -> ProviderResponse:
        if provider_event not in _MAPS[self.runtime]:
            return ProviderResponse("{}\n", "unsupported_provider_event\n", 1)
        diagnostics = list(result.diagnostics)
        output = {}
        if len(result.context.encode("utf-8")) > MAX_EVENT_BYTES:
            return ProviderResponse("{}\n", "provider_output_too_large\n", 1)
        if result.context:
            if provider_event not in _CONTEXT_EVENTS[self.runtime]:
                diagnostics.append("context_injection_unsupported")
            elif self.runtime == "copilot":
                output["additionalContext"] = result.context
            elif self.runtime == "gemini":
                output["hookSpecificOutput"] = {"additionalContext": result.context}
            else:
                output["hookSpecificOutput"] = {"hookEventName": provider_event,
                                                "additionalContext": result.context}
        # No exit 2 or policy decision: failed memory work must not block an agent.
        # Even provider fail-open behavior is still an explicit failed execution.
        failed = result.status == "degraded" or bool(diagnostics)
        safe_codes = [code if isinstance(code, str) and all(c.isalnum() or c in "_:" for c in code)
                      else "hook_error" for code in diagnostics]
        return ProviderResponse(canonical_json(output) + "\n", "\n".join(safe_codes) + ("\n" if safe_codes else ""),
                                1 if failed else 0)
