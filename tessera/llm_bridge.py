"""Project-neutral optional LLM adapter resolution for TESSERA.

The default resolves no backend and inspects no provider credentials, files,
subprocesses, or repository parents. Applications may pass a custom ``llm_fn``
directly. Project-specific adapters live behind an explicit deprecated
compatibility boundary.
"""

from __future__ import annotations

import warnings
from typing import Optional


class LlmBridgeError(RuntimeError):
    """Raised when optional-backend configuration or execution fails."""


def resolve_llm_fn(
    *, backend: Optional[str] = None, endpoint: Optional[str] = None,
    api_key: Optional[str] = None, contact_id: Optional[str] = None,
    subscription_id: Optional[str] = None, tenant_id: Optional[str] = None,
    router_path: Optional[str] = None, engine: Optional[str] = None,
    task_type: Optional[str] = "planning", temperature: float = 0,
    system_name: str = "TESSERA", timeout: int = 60,
    return_backend_name: bool = False,
):
    """Resolve only an explicitly selected optional backend."""

    if backend in (None, "none"):
        return (None, None) if return_backend_name else None
    try:
        if backend == "legacy-blip-gateway":
            from .legacy_compat import blip_gateway_llm_fn
            llm_fn = blip_gateway_llm_fn(
                endpoint=endpoint or "", api_key=api_key or "",
                contact_id=contact_id or "", subscription_id=subscription_id or "",
                tenant_id=tenant_id or "", temperature=temperature,
                system_name=system_name, timeout=timeout,
            )
        elif backend == "legacy-lao-engine-router":
            from .legacy_compat import lao_engine_router_llm_fn
            llm_fn = lao_engine_router_llm_fn(
                router_path=router_path or "", engine=engine,
                task_type=task_type, timeout=timeout,
            )
        else:
            raise LlmBridgeError(
                f"Unknown optional backend {backend!r}; pass a custom llm_fn or "
                "select an explicitly supported compatibility backend."
            )
    except RuntimeError as exc:
        if isinstance(exc, LlmBridgeError):
            raise
        raise LlmBridgeError(str(exc)) from exc
    return (llm_fn, backend) if return_backend_name else llm_fn


def azure_gateway_llm_fn(*, url=None, api_key=None, **kwargs):
    """Deprecated shim for explicitly configured gateway users."""
    warnings.warn(
        "azure_gateway_llm_fn is deprecated; explicitly select "
        "backend='legacy-blip-gateway' via resolve_llm_fn.",
        FutureWarning, stacklevel=2,
    )
    return resolve_llm_fn(
        backend="legacy-blip-gateway", endpoint=url, api_key=api_key, **kwargs
    )


def engine_router_llm_fn(*, router_path=None, repo_root=None, **kwargs):
    """Deprecated shim; generic parent-directory discovery has ended."""
    warnings.warn(
        "engine_router_llm_fn is deprecated; pass an explicit router_path to "
        "backend='legacy-lao-engine-router'.", FutureWarning, stacklevel=2,
    )
    if router_path is None and repo_root is not None:
        raise LlmBridgeError(
            "repo_root discovery is no longer supported; pass the exact router_path."
        )
    return resolve_llm_fn(
        backend="legacy-lao-engine-router", router_path=router_path, **kwargs
    )
