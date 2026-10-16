"""Single import boundary for the optional MCP Python SDK, majors 1 and 2.

The MCP wire protocol is identical across both majors; only Python names
differ. SDK 2.x renamed ``FastMCP`` to ``MCPServer`` and ``McpError`` to
``MCPError``, moved the server version into the constructor, and exposes model
fields in snake_case (``input_schema``) while still accepting the camelCase
protocol names as constructor keywords. Everything else in TESSERA imports the
SDK through this module so the transport contract stays version-neutral.
"""
import importlib.metadata

SUPPORTED_RANGE = "mcp>=1.30.0,<3.0.0"
INSTALL_HINT = "Install the MCP extra: pip install 'tessera-agent-memory[mcp]'"

try:
    SDK_VERSION = importlib.metadata.version("mcp")
except importlib.metadata.PackageNotFoundError:
    SDK_VERSION = None

try:
    from mcp import types  # noqa: F401  (re-exported)
except ImportError as exc:  # pragma: no cover - exercised by installed base artifact
    raise ImportError(INSTALL_HINT) from exc


def _unsupported(exc):
    return ImportError(
        f"Installed MCP SDK {SDK_VERSION or 'of unknown version'} is not supported by "
        f"TESSERA's transport; supported: {SUPPORTED_RANGE}."
    )


_major = int(SDK_VERSION.split(".")[0]) if SDK_VERSION and SDK_VERSION[0].isdigit() else None
if _major is not None and _major not in {1, 2}:
    raise _unsupported(None)

try:
    from mcp.server.mcpserver import MCPServer as ServerBase
    from mcp.server.mcpserver.server import ReadResourceContents
    from mcp.shared.exceptions import MCPError as _ProtocolError

    SDK_MAJOR = 2
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as ServerBase
        from mcp.server.fastmcp.server import ReadResourceContents
        from mcp.shared.exceptions import McpError as _ProtocolError

        SDK_MAJOR = 1
    except ImportError as exc:
        raise _unsupported(exc) from exc

__all__ = [
    "SDK_MAJOR", "SDK_VERSION", "SUPPORTED_RANGE", "ReadResourceContents", "ServerBase",
    "is_error", "protocol_error", "server_options", "set_server_version", "set_tool_input_schema",
    "set_tool_output_schema", "structured_content", "tool_input_schema", "tool_output_schema", "types",
]

_SNAKE = SDK_MAJOR >= 2


def server_options(version):
    """Constructor keywords that differ between majors."""
    return {"version": version} if _SNAKE else {}


def set_server_version(server, version):
    """SDK 1.x has no constructor keyword for the advertised server version."""
    if not _SNAKE:
        server._mcp_server.version = version


def tool_input_schema(tool):
    return tool.input_schema if _SNAKE else tool.inputSchema


def set_tool_input_schema(tool, schema):
    if _SNAKE:
        tool.input_schema = schema
    else:
        tool.inputSchema = schema


def tool_output_schema(tool):
    return tool.output_schema if _SNAKE else tool.outputSchema


def set_tool_output_schema(tool, schema):
    if _SNAKE:
        tool.output_schema = schema
    else:
        tool.outputSchema = schema


def structured_content(result):
    return result.structured_content if _SNAKE else result.structuredContent


def is_error(result):
    return result.is_error if _SNAKE else result.isError


def protocol_error(code, message, data=None):
    """A JSON-RPC error exception the SDK forwards to the client unchanged."""
    if _SNAKE:
        return _ProtocolError(code, message, data)
    return _ProtocolError(types.ErrorData(code=code, message=message, data=data))
