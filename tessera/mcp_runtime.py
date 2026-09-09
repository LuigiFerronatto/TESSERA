"""SDK-independent configuration and request ownership for the MCP adapter.

The canonical Engine remains synchronous. Only the transport schedules it;
provider work uses isolated, disposable inputs and cannot commit after timeout.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from functools import partial
import math
from pathlib import Path
import threading
import time

from .config import resolve_runtime_configuration

SCHEMA_VERSION = "1.0"
_binding = ContextVar("tessera_mcp_runtime", default=None)


class _QueueTimeout(TimeoutError):
    pass


class RuntimeFailure(ValueError):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def current_runtime(default):
    binding = _binding.get()
    return binding[0] if binding is not None else default


class EngineProxy:
    def __init__(self, default):
        self.default = default

    def __getattr__(self, name):
        binding = _binding.get()
        engine = binding[1] if binding is not None else self.default.get_engine()
        return getattr(engine, name)


class MCPRuntime:
    def __init__(self, configuration=None, *, provider=None, provider_options=None,
                 request_timeout=60.0):
        if not math.isfinite(request_timeout) or request_timeout <= 0:
            raise ValueError("request_timeout must be a finite positive number")
        if provider is not None and not callable(provider):
            raise ValueError("provider must be an application-owned callable")
        if provider is not None and provider_options:
            raise ValueError("select provider or provider_options, not both")
        self.configuration = configuration
        self.provider = provider
        self.provider_options = dict(provider_options or {})
        if self.provider_options and not self.provider_options.get("backend"):
            raise ValueError("provider_options requires an explicit backend")
        self.request_timeout = request_timeout
        self.engine = None
        self.state = "created"
        self._initialization_lock = threading.Lock()
        self._lock = None
        # A timed-out provider keeps its slot until its actual thread exits.
        self._provider_slot = threading.BoundedSemaphore(1)

    def get_engine(self):
        with self._initialization_lock:
            if self.engine is None:
                from .engine import TesseraEngine

                self.configuration = self.configuration or resolve_runtime_configuration()
                storage = Path(self.configuration.storage_dir)
                if storage.exists() and not storage.is_dir():
                    raise RuntimeFailure("STARTUP_FAILED", "Configured store must be a directory.")
                engine = TesseraEngine(configuration=self.configuration)
                engine.build_index()
                self.engine = engine
                self.state = "ready"
            return self.engine

    @contextmanager
    def bind(self, engine=None):
        token = _binding.set((self, engine if engine is not None else self.get_engine()))
        try:
            yield
        finally:
            _binding.reset(token)

    def resolve_provider(self):
        if self.provider is not None:
            provider, name = self.provider, "application_callable"
        else:
            from .llm_bridge import resolve_llm_fn

            provider, name = resolve_llm_fn(**self.provider_options, return_backend_name=True)
        if provider is None:
            raise RuntimeFailure("PROVIDER_NOT_CONFIGURED", "Select an explicit provider for this assisted tool.")
        def checked_provider(*args):
            result = provider(*args)
            if not isinstance(result, str) or not result.strip():
                raise RuntimeFailure("PROVIDER_FAILED", "Provider returned no usable text; no notes were written.")
            return result

        return checked_provider, name

    def health(self):
        from . import __version__

        return {
            "schema_version": SCHEMA_VERSION, "server_version": __version__,
            "state": self.state, "transport": "stdio",
            "configuration": self.configuration.to_dict() if self.configuration else None,
            "provider_selected": bool(self.provider or self.provider_options),
            "request_timeout_seconds": self.request_timeout,
            "engine_concurrency": 1, "provider_concurrency": 1,
            "write_cancellation": "queued_only; started writes complete",
        }

    async def start(self):
        import anyio

        if self.state != "created":
            raise RuntimeError("A server runtime supports one lifespan")
        self._lock = anyio.Lock()
        try:
            await anyio.to_thread.run_sync(self.get_engine)
        except Exception:
            self.state = "failed"
            raise

    def _bound_call(self, function, engine=None):
        with self.bind(engine):
            return function()

    async def _serialized(self, function, deadline, *, mutating=False):
        import anyio

        # The deadline covers waiting to start. Once entered, Engine calls are
        # shielded and drained so no timed-out background writer outlives the lock.
        with anyio.fail_after(max(0, deadline - time.monotonic())):
            await self._lock.acquire()
        try:
            await anyio.lowlevel.checkpoint()
            if time.monotonic() >= deadline:
                raise TimeoutError
            try:
                def run_owned():
                    if time.monotonic() >= deadline:
                        raise _QueueTimeout
                    return self._bound_call(function)

                result = await anyio.to_thread.run_sync(run_owned)
                # The SDK already acknowledges cancellation. Deliver pending
                # cancellation after draining the worker, before it can emit a
                # second response for the same request.
                await anyio.lowlevel.checkpoint()
                return result
            except _QueueTimeout:
                raise TimeoutError from None
            except Exception:
                if mutating:
                    raise RuntimeFailure(
                        "WRITE_FAILED", "Write failed after starting; earlier changes may persist. Inspect storage before retrying.",
                    ) from None
                raise
        finally:
            self._lock.release()

    async def _assisted(self, function, deadline, engine=None):
        import anyio

        def run():
            if not self._provider_slot.acquire(blocking=False):
                raise RuntimeFailure("PROVIDER_BUSY", "The selected provider is still handling another request.")
            try:
                return self._bound_call(function, engine)
            except RuntimeFailure:
                raise
            except Exception:
                raise RuntimeFailure("PROVIDER_FAILED", "The selected provider failed; no notes were written.") from None
            finally:
                self._provider_slot.release()

        with anyio.fail_after(max(0, deadline - time.monotonic())):
            return await anyio.to_thread.run_sync(run, abandon_on_cancel=True)

    async def invoke(self, name, arguments):
        import anyio
        from . import mcp_server as handlers

        if self.state != "ready":
            raise RuntimeFailure("NOT_READY", "Server startup has not completed.")
        deadline = time.monotonic() + self.request_timeout
        functions = {function.__name__: function for function in handlers.TOOLS}
        functions.update({function.__name__: function for function in handlers.RESOURCES.values()})
        functions["get_memory"] = handlers.get_memory
        if name not in functions:
            raise RuntimeFailure("UNKNOWN_TOOL", "Unknown tool name.")
        if name == "get_server_health":
            return self.health()
        if name == "decompose_episode":
            prepared = await self._assisted(partial(handlers.prepare_decomposition, arguments), deadline)
            return await self._serialized(partial(handlers.persist_decomposition, arguments, prepared), deadline, mutating=True)
        if name == "query_memories_pipeline":
            snapshot = await self._serialized(lambda: deepcopy(self.engine), deadline)
            return await self._assisted(partial(functions[name], **arguments), deadline, snapshot)
        result = await self._serialized(
            partial(functions[name], **arguments), deadline,
            mutating=name in {"write_memory", "rebuild_index", "run_doctor"}
            or (name == "run_quickstart" and arguments.get("apply", False)),
        )
        # Pure reads may discard an overdue result. Mutating operations report
        # their completed outcome, never a false timeout implying no persistence.
        if name in {"query_memories", "query_store", "get_memory", "get_index_stats",
                    "get_index_composition"} and time.monotonic() >= deadline:
            raise TimeoutError
        return result
