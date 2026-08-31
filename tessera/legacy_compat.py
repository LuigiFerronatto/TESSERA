"""Explicit, deprecated compatibility adapters for legacy LAO/Blip users.

Nothing here is imported or initialized by deterministic retrieval. Callers
must explicitly select an adapter and provide its endpoint or router path.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
import warnings
from pathlib import Path
from typing import Optional


class CompatibilityConfigurationError(RuntimeError):
    """Raised when an explicitly selected compatibility adapter is incomplete."""


class CompatibilityBackendError(RuntimeError):
    """Raised when an explicitly selected compatibility backend call fails."""


class LegacyBackendWarning(FutureWarning):
    """Warns that a project-specific compatibility adapter is deprecated."""


def blip_gateway_llm_fn(
    *, endpoint: str, api_key: str, contact_id: str, subscription_id: str,
    tenant_id: str, temperature: float = 0, timeout: int = 60,
    system_name: str = "TESSERA",
):
    """Create the explicit deprecated Blip gateway adapter."""

    if not endpoint or not api_key:
        raise CompatibilityConfigurationError(
            "The legacy Blip gateway adapter requires explicit endpoint and "
            "api_key values; select a generic custom llm_fn otherwise."
        )
    for name, value in (("contact_id", contact_id), ("subscription_id", subscription_id), ("tenant_id", tenant_id)):
        if not value:
            raise CompatibilityConfigurationError(
                f"The legacy Blip gateway adapter requires explicit {name}."
            )
    warnings.warn(
        "The Blip gateway adapter is deprecated compatibility behavior and "
        "must remain explicitly configured.", LegacyBackendWarning, stacklevel=2,
    )

    def _llm_fn(system_prompt: str, user_prompt: str) -> str:
        try:
            import requests
        except ImportError as exc:
            raise CompatibilityBackendError(
                "Install the optional 'llm' extra to use the legacy Blip gateway adapter."
            ) from exc
        headers = {
            "Content-Type": "application/json", "X-Contact-Id": contact_id,
            "X-Subscription-Id": subscription_id, "X-Tenant-Id": tenant_id,
            "api-key": api_key,
            "traceparent": f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01",
        }
        payload = {
            "messages": [
                {"role": "system", "content": f"Your name is {system_name}. {system_prompt}"},
                {"role": "user", "content": user_prompt},
            ], "temperature": temperature,
        }
        try:
            response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
        except requests.RequestException as exc:
            raise CompatibilityBackendError(f"Legacy Blip gateway request failed: {exc}") from exc
        if response.status_code != 200:
            raise CompatibilityBackendError(
                f"Legacy Blip gateway returned HTTP {response.status_code}: {response.text[:300]}"
            )
        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise CompatibilityBackendError(
                "Legacy Blip gateway returned an invalid response payload."
            ) from exc
    return _llm_fn


def lao_engine_router_llm_fn(
    *, router_path: str, engine: Optional[str] = None,
    task_type: Optional[str] = "planning", timeout: int = 120,
):
    """Create the explicit deprecated LAO engine-router adapter."""

    if not router_path:
        raise CompatibilityConfigurationError(
            "The legacy LAO engine-router adapter requires an explicit router_path."
        )
    path = Path(router_path).expanduser()
    if not path.is_file():
        raise CompatibilityConfigurationError(
            f"The configured legacy LAO engine router does not exist: {path}"
        )
    warnings.warn(
        "The LAO engine-router adapter is deprecated compatibility behavior "
        "and must remain explicitly configured.", LegacyBackendWarning, stacklevel=2,
    )

    def _llm_fn(system_prompt: str, user_prompt: str) -> str:
        prompt = f"{system_prompt}\n\n{user_prompt}"
        command = [sys.executable, str(path), "invoke", "--prompt", prompt, "--timeout", str(timeout)]
        if engine:
            command += ["--engine", engine]
        if task_type:
            command += ["--task-type", task_type]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CompatibilityBackendError(f"Legacy LAO engine router could not run: {exc}") from exc
        if result.returncode != 0:
            raise CompatibilityBackendError(
                f"Legacy LAO engine router exited {result.returncode}: {(result.stderr or '')[:300]}"
            )
        return result.stdout.strip()
    return _llm_fn
