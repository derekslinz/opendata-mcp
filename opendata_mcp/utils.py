import json
import logging
from typing import Any, Callable, Sequence

from mcp import types
from mcp.server import Server
from pydantic import AnyUrl

log = logging.getLogger(__name__)


def to_json_text(payload: Any, max_chars: int | None = None) -> str:
    """Serialize data to stable JSON text for MCP responses."""
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if max_chars is not None:
        return text[:max_chars]
    return text


def create_mcp_server(
    server_name: str,
    resources: list[types.Resource] | None = None,
    resources_handlers: dict[str, Callable[[AnyUrl], str | bytes]] | None = None,
    tools: list[types.Tool] | None = None,
    tools_handlers: dict[
        str,
        Callable[
            [dict[str, Any] | None],
            Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource],
        ],
    ]
    | None = None,
) -> Server:
    """
    Create a MCP server with the given tools and handlers.

    Args:
        server_name: The name of the server.
        tools: The list of tools to register.
        tools_handlers: The dictionary of tools handlers.

    Returns:
        The created MCP server.
    """
    _resources = resources or []
    _resources_handlers = resources_handlers or {}
    _tools = tools or []
    _tools_handlers = tools_handlers or {}

    # instantiate the server
    server = Server(server_name)

    # register resources
    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        return _resources

    # register resources handlers
    # TODO: handle better the resource handler we probably dont want to have a handler per URI...
    @server.read_resource()
    async def handle_read_resource(resource_uri: AnyUrl) -> str | bytes:
        resource_key = str(resource_uri)

        if resource_key not in _resources_handlers:
            log.error(f"Resource {resource_uri} not found")
            raise AttributeError(f"Resource {resource_uri} not found")

        return _resources_handlers[resource_key](resource_uri)

    # register the tools
    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return _tools

    # register the tools handlers
    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None = None
    ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name not in _tools_handlers:
            log.error(f"Tool {name} not found")
            raise AttributeError(f"Tool {name} not found")

        try:
            return await _tools_handlers[name](arguments)
        except Exception as e:
            log.error(f"Error calling tool {name}: {e}")
            raise

    return server
