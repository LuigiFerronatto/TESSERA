"""
Optional real-LLM bridges for TesseraOrchestrator.

By default, TesseraOrchestrator's 3 pipeline steps (Need / Planner / Inference)
use a deterministic offline string-template simulation (see
`TesseraOrchestrator._simulated_llm`) so the whole thing is runnable/testable
without any model or API key.

Two real `llm_fn` backends are provided here:

1. `azure_gateway_llm_fn()` (preferred/default) - calls Blip's internal
   Azure AI Gateway directly over HTTPS (OpenAI-compatible chat/completions
   endpoint), no subprocess involved. Configure via env vars (see below) or
   explicit kwargs.
2. `engine_router_llm_fn()` - delegates each step to LAO's own
   `lao_core/engine_router.py invoke` subprocess (multi-engine: claude /
   copilot / gemini, with health/cooldown failover already built in there).
   Kept as a fallback/alternative for environments where the Azure gateway
   isn't reachable but a local engine CLI is.

Usage:
    from tessera.llm_bridge import azure_gateway_llm_fn
    from tessera.orchestrator import TesseraOrchestrator

    llm_fn = azure_gateway_llm_fn()  # None if TESSERA_AZURE_GATEWAY_API_KEY unset
    orchestrator = TesseraOrchestrator(engine, llm_fn=llm_fn)  # falls back to
                                                             # simulation if
                                                             # llm_fn is None

Also wired into the CLI: `tessera start <dir> "<task>" --use-llm` (see cli.py),
which tries the Azure gateway first, then engine_router.py, then the offline
simulation - see `resolve_llm_fn()` below.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Azure AI Gateway backend (Blip internal - preferred)
# ---------------------------------------------------------------------------

# Never hardcode the api-key here - always read from env. Defaults below
# mirror the endpoint/deployment already used in LAO's own gateway calls; a
# `.env` entry (TESSERA_AZURE_GATEWAY_API_KEY) is the only required override.
AZURE_GATEWAY_URL_DEFAULT = (
    "https://ai-gateway-int.azure-api.net/llm/foundry-openai/gpt-5.2/"
    "openai/deployments/gpt-5.2/chat/completions?api-version=2025-01-01-preview"
)


class LlmBridgeError(RuntimeError):
    """Raised when a real-LLM backend call fails (network, auth, subprocess, etc)."""


def azure_gateway_llm_fn(
    *,
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    contact_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    temperature: float = 0,
    timeout: int = 60,
    system_name: str = "Tessera",
):
    """
    Returns a `(system_prompt, user_prompt) -> str` callable backed by Blip's
    internal Azure AI Gateway (OpenAI-compatible chat/completions), or None
    if no API key is configured (env var `TESSERA_AZURE_GATEWAY_API_KEY`, or
    pass `api_key` explicitly) - same "return None instead of raising" contract
    as `engine_router_llm_fn` below, so callers can try-then-fallback once at
    setup time.

    Env vars (all optional except the api key):
      TESSERA_AZURE_GATEWAY_API_KEY   - required to activate this backend
      TESSERA_AZURE_GATEWAY_URL       - overrides the default endpoint/deployment
      TESSERA_AZURE_GATEWAY_CONTACT_ID, _SUBSCRIPTION_ID, _TENANT_ID
                                    - default to 'innovation-labs-poc' each,
                                      matching the gateway's own PoC headers
    """
    api_key = api_key or os.environ.get("TESSERA_AZURE_GATEWAY_API_KEY")
    if not api_key:
        return None

    url = url or os.environ.get("TESSERA_AZURE_GATEWAY_URL", AZURE_GATEWAY_URL_DEFAULT)
    contact_id = contact_id or os.environ.get("TESSERA_AZURE_GATEWAY_CONTACT_ID", "innovation-labs-poc")
    subscription_id = subscription_id or os.environ.get("TESSERA_AZURE_GATEWAY_SUBSCRIPTION_ID", "innovation-labs-poc")
    tenant_id = tenant_id or os.environ.get("TESSERA_AZURE_GATEWAY_TENANT_ID", "innovation-labs-poc")

    def _llm_fn(system_prompt: str, user_prompt: str) -> str:
        try:
            import requests
        except ImportError as exc:
            raise LlmBridgeError(
                "the 'requests' package is required for azure_gateway_llm_fn - "
                "install it (already a transitive dep in most LAO envs) or use "
                "engine_router_llm_fn instead."
            ) from exc

        headers = {
            "Content-Type": "application/json",
            "X-Contact-Id": contact_id,
            "X-Subscription-Id": subscription_id,
            "X-Tenant-Id": tenant_id,
            "api-key": api_key,
            "traceparent": f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01",
        }
        payload = {
            "messages": [
                {"role": "system", "content": f"Your name is {system_name}. {system_prompt}"},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
        except requests.RequestException as exc:
            print(f"[tessera.llm_bridge] Azure gateway request failed, echoing raw prompt: {exc}", file=sys.stderr)
            return user_prompt

        if resp.status_code != 200:
            print(
                f"[tessera.llm_bridge] Azure gateway returned {resp.status_code}: "
                f"{resp.text[:300]} - echoing raw prompt",
                file=sys.stderr,
            )
            return user_prompt

        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as exc:
            print(f"[tessera.llm_bridge] unexpected Azure gateway response shape ({exc}), echoing raw prompt", file=sys.stderr)
            return user_prompt

    return _llm_fn


# ---------------------------------------------------------------------------
# engine_router.py backend (fallback / alternative)
# ---------------------------------------------------------------------------


def _find_engine_router(repo_root: Optional[str] = None) -> Optional[Path]:
    """
    Locate lao_core/engine_router.py by walking up from either an explicit
    repo_root, this file's own location, or the current working directory -
    Tessera is meant to be usable both from inside the LAO monorepo (this repo)
    and, once packaged/installed elsewhere, without it (hence returning None
    instead of raising when it can't be found).
    """
    candidates = []
    if repo_root:
        candidates.append(Path(repo_root))
    candidates.append(Path(__file__).resolve().parents[2])  # .../Tessera/tessera/llm_bridge.py -> repo root
    candidates.append(Path.cwd())

    for base in candidates:
        for probe in (base, *base.parents):
            path = probe / "lao_core" / "engine_router.py"
            if path.is_file():
                return path
    return None


def engine_router_invoke(
    prompt: str,
    *,
    engine: Optional[str] = None,
    task_type: Optional[str] = "planning",
    timeout: int = 120,
    repo_root: Optional[str] = None,
) -> str:
    """
    Runs `python3 lao_core/engine_router.py invoke --prompt ... [--engine ...]
    [--task-type ...] --timeout ...` and returns its stdout, stripped.
    Raises LlmBridgeError on any failure (missing script, missing engine CLI,
    timeout, non-zero exit) so callers can decide to fall back gracefully.
    """
    router_path = _find_engine_router(repo_root)
    if router_path is None:
        raise LlmBridgeError(
            "lao_core/engine_router.py not found - Tessera is likely running "
            "outside the LAO monorepo; pass repo_root explicitly or use the "
            "offline simulated llm_fn instead."
        )

    cmd = [sys.executable, str(router_path), "invoke", "--prompt", prompt, "--timeout", str(timeout)]
    if engine:
        cmd += ["--engine", engine]
    if task_type:
        cmd += ["--task-type", task_type]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired as exc:
        raise LlmBridgeError(f"engine_router invoke timed out after {timeout}s") from exc

    if result.returncode != 0:
        raise LlmBridgeError(
            f"engine_router invoke exited {result.returncode}: {(result.stderr or '')[:300]}"
        )

    return result.stdout.strip()


def engine_router_llm_fn(
    *,
    engine: Optional[str] = None,
    task_type: Optional[str] = "planning",
    timeout: int = 120,
    repo_root: Optional[str] = None,
):
    """
    Returns a `(system_prompt, user_prompt) -> str` callable suitable for
    `TesseraOrchestrator(engine, llm_fn=...)`, backed by engine_router.py. Each
    call concatenates system+user into a single prompt (engine_router's
    `invoke` takes one flat --prompt, no separate system/user split) and
    strips the response.

    Returns None (instead of raising) if engine_router.py can't be located at
    all - a clear, non-fatal "real LLM unavailable, use simulation" signal for
    callers that want to try-then-fallback once at setup time rather than on
    every single call.
    """
    if _find_engine_router(repo_root) is None:
        return None

    def _llm_fn(system_prompt: str, user_prompt: str) -> str:
        combined = f"{system_prompt}\n\n{user_prompt}"
        try:
            return engine_router_invoke(
                combined, engine=engine, task_type=task_type, timeout=timeout, repo_root=repo_root
            )
        except LlmBridgeError as exc:
            # Surface the failure to stderr but don't crash the whole
            # orchestrator run over one flaky LLM call - the caller (cli.py)
            # already warns the user real LLM mode is degraded.
            print(f"[tessera.llm_bridge] real LLM call failed, degrading to raw prompt echo: {exc}", file=sys.stderr)
            return user_prompt

    return _llm_fn


# ---------------------------------------------------------------------------
# Unified resolver - tries backends in priority order
# ---------------------------------------------------------------------------


def resolve_llm_fn(
    *,
    prefer: str = "azure",
    engine: Optional[str] = None,
    timeout: int = 60,
    repo_root: Optional[str] = None,
    return_backend_name: bool = False,
):
    """
    Tries real-LLM backends in order and returns the first one that's
    actually configured/available, or None if none are (caller should fall
    back to TesseraOrchestrator's offline simulation in that case).

    Benchmarked 2026-08-21 on a trivial single-turn prompt:
      - azure gateway (direct HTTPS call):        ~2.1s
      - engine_router.py invoke --engine opencode: ~9.2s
      - engine_router.py invoke --engine copilot:  ~13.4s
    So `prefer="azure"` (the default) is the fast path for TesseraOrchestrator's
    3-calls-per-run loop; `engine="opencode"` is the recommended
    engine_router fallback when Azure gateway creds aren't configured, ahead
    of copilot/claude/gemini on raw latency for this workload.

    `prefer`: "azure" (default) tries azure_gateway_llm_fn first, falling
    back to engine_router_llm_fn; "engine_router" reverses the order; "none"
    skips both and returns None (forces the offline simulation).

    `return_backend_name`: if True, returns a `(llm_fn_or_None, backend_name)`
    tuple instead of just `llm_fn_or_None` — `backend_name` is one of
    "azure", "engine_router", or None (no backend available). Added so the
    CLI can tell the user *which* backend actually got selected (important:
    if `TESSERA_AZURE_GATEWAY_API_KEY` isn't exported in the current shell —
    e.g. you forgot `source .env` — this silently degrades to the much
    slower engine_router subprocess fallback (~9-13s/call, sometimes longer
    if the picked engine CLI needs interactive auth) instead of erroring,
    which can look like a hang if you were expecting the ~2s Azure path).
    """
    if prefer == "none":
        return (None, None) if return_backend_name else None

    backend_order = (
        [("azure", azure_gateway_llm_fn), ("engine_router", lambda: engine_router_llm_fn(engine=engine, timeout=timeout, repo_root=repo_root))]
        if prefer == "azure"
        else [("engine_router", lambda: engine_router_llm_fn(engine=engine, timeout=timeout, repo_root=repo_root)), ("azure", azure_gateway_llm_fn)]
    )
    for name, make_llm_fn in backend_order:
        llm_fn = make_llm_fn()
        if llm_fn is not None:
            return (llm_fn, name) if return_backend_name else llm_fn
    return (None, None) if return_backend_name else None
