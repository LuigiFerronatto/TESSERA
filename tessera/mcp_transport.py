"""Versioned stdio transport over the optional MCP Python SDK (v1)."""
from contextlib import asynccontextmanager
from copy import deepcopy
import json
from urllib.parse import unquote

try:
    import jsonschema
    from mcp import types
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.server import ReadResourceContents
    from mcp.shared.exceptions import McpError
except ImportError as exc:  # pragma: no cover - exercised by installed base artifact
    raise ImportError("Install the MCP extra: pip install 'tessera[mcp]'") from exc

from . import __version__
from .mcp_runtime import SCHEMA_VERSION, RuntimeFailure

ENVELOPE_SCHEMA = {
    "$id": "urn:tessera:mcp:1.0:response",
    "type": "object", "additionalProperties": False,
    "required": ["schema_version", "operation", "data", "error"],
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "operation": {"type": "string"},
        "data": {},
        "error": {"anyOf": [{"type": "null"}, {
            "type": "object", "additionalProperties": False,
            "required": ["code", "message"],
            "properties": {"code": {"type": "string"}, "message": {"type": "string"}},
        }]},
    },
}


def envelope(operation, data=None, error=None):
    return {"schema_version": SCHEMA_VERSION, "operation": operation,
            "data": data, "error": error}


def failure(exc):
    if isinstance(exc, RuntimeFailure):
        return {"code": exc.code, "message": exc.message}
    if isinstance(exc, TimeoutError):
        return {"code": "TIMEOUT", "message": "Request deadline exceeded before completion; no pending commit will run."}
    if isinstance(exc, (ValueError, TypeError)):
        return {"code": "INVALID_ARGUMENT", "message": "Arguments do not satisfy the operation contract."}
    if isinstance(exc, OSError):
        return {"code": "STORAGE_ERROR", "message": "Storage operation failed; inspect local permissions and index health."}
    return {"code": "INTERNAL_ERROR", "message": "Operation failed; inspect server health before retrying."}


class TesseraMCP(FastMCP):
    """Keep SDK handshake/cancellation; own only TESSERA's transport contracts."""

    def __init__(self, runtime):
        self.runtime = runtime

        @asynccontextmanager
        async def lifespan(_server):
            await runtime.start()
            try:
                yield runtime
            finally:
                runtime.state = "closed"

        super().__init__("tessera", lifespan=lifespan, log_level="WARNING",
                         instructions="TESSERA MCP runtime contract 1.0; stdio; see server://health.")
        self._mcp_server.version = __version__

    def run(self, transport="stdio", **kwargs):
        if transport != "stdio":
            raise ValueError("This runtime certifies stdio only")
        return super().run(transport=transport, **kwargs)

    async def list_tools(self):
        tools = await super().list_tools()
        for tool in tools:
            tool.inputSchema = deepcopy(tool.inputSchema)
            tool.inputSchema["$id"] = f"urn:tessera:mcp:1.0:{tool.name}:request"
            tool.inputSchema["additionalProperties"] = False
            properties = tool.inputSchema.get("properties", {})
            if "top_n" in properties:
                properties["top_n"].update(minimum=1, maximum=100)
            if tool.name == "query_store":
                properties["store"]["enum"] = ["facts", "preferences", "insights"]
            tool.outputSchema = deepcopy(ENVELOPE_SCHEMA)
            tool.outputSchema["oneOf"] = [
                {"properties": {"error": {"type": "null"}, "data": {
                    "type": "array" if tool.name in {"query_memories", "query_store"} else "object",
                }}},
                {"properties": {"error": {"type": "object"}, "data": {"type": "null"}}},
            ]
            tool.meta = {"tessera/schema_version": SCHEMA_VERSION}
            read_only = tool.name in {"query_memories", "query_store", "query_memories_pipeline",
                                      "get_index_composition", "get_server_health"}
            tool.annotations = types.ToolAnnotations(
                readOnlyHint=read_only, destructiveHint=not read_only,
                idempotentHint=read_only, openWorldHint=tool.name in {
                    "query_memories_pipeline", "decompose_episode"},
            )
        return tools

    async def call_tool(self, name, arguments):
        try:
            definitions = {tool.name: tool for tool in await self.list_tools()}
            if name not in definitions:
                raise RuntimeFailure("UNKNOWN_TOOL", "Unknown tool name.")
            if not jsonschema.Draft202012Validator(definitions[name].inputSchema).is_valid(arguments):
                raise RuntimeFailure("INVALID_ARGUMENT", "Arguments do not match the advertised request schema.")
            # Validation above is strict (no coercion); the SDK model supplies defaults.
            tool = self._tool_manager.get_tool(name)
            values = tool.fn_metadata.arg_model.model_validate(arguments).model_dump()
            data = await self.runtime.invoke(name, values)
            # Normalize dates/other canonical display values once so the two
            # MCP result channels cannot serialize the same value differently.
            payload = json.loads(json.dumps(envelope(name, data=data), default=str))
        except Exception as exc:
            payload = envelope(name, error=failure(exc))
        # Both channels carry the same versioned object; Engine data is untouched.
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, default=str))],
            structuredContent=payload, isError=payload["error"] is not None,
        )

    async def read_resource(self, uri):
        from . import mcp_server as handlers

        address = str(uri)
        try:
            if address.startswith("memories://"):
                data = await self.runtime.invoke("get_memory", {"memory_id": unquote(address[len("memories://"):])})
                return [ReadResourceContents(content=data, mime_type="text/markdown")]
            if address not in handlers.RESOURCES:
                raise RuntimeFailure("NOT_FOUND", "Unknown resource URI.")
            name = handlers.RESOURCES[address].__name__
            data = await self.runtime.invoke(name, {})
            return [ReadResourceContents(content=json.dumps(envelope(name, data=data)), mime_type="application/json")]
        except Exception as exc:
            raise McpError(types.ErrorData(
                code=-32002, message="Resource request failed", data=envelope("resources/read", error=failure(exc)),
            )) from None


def build_server(runtime):
    from . import mcp_server as handlers

    server = TesseraMCP(runtime)
    for function in handlers.TOOLS:
        server.add_tool(function, structured_output=False)
    for uri, function in handlers.RESOURCES.items():
        server.resource(uri)(function)
    server.resource("memories://{memory_id}")(handlers.get_memory)
    return server
