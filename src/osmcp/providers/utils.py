import logging
from typing import Any, Callable, Sequence

from mcp import types
from mcp.server import Server

log = logging.getLogger(__name__)


def create_mcp_server(
    server_name: str,
    tools: list[types.Tool],
    tools_handlers: dict[
        str,
        Callable[
            [dict[str, Any] | None],
            Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource],
        ],
    ],
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
    # instantiate the server
    server = Server(server_name)

    # register the tools
    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return tools

    # register the tools handlers
    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None = None
    ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name not in tools_handlers:
            log.error(f"Tool {name} not found")
            raise AttributeError(f"Tool {name} not found")

        try:
            return await tools_handlers[name](arguments)
        except Exception as e:
            log.error(f"Error calling tool {name}: {e}")
            raise

    return server
