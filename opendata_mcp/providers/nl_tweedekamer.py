"""
Tweedekamer OData v4 Data Provider

This module provides an MCP interface for the Dutch House of Representatives'
OData v4 Gegevensmagazijn API.

Features:
- Discovery of entity sets (Persoon, Fractie, etc.)
- Flexible OData queries using $filter, $select, $top, $skip, $expand

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# Tweedekamer Discovery
###################


def list_tk_entities() -> List[str]:
    """Return a hardcoded list of available entities from Tweedekamer Gegevensmagazijn."""
    # This list is distilled from the $metadata document
    return [
        "Persoon",
        "Commissie",
        "Fractie",
        "Activiteit",
        "Agendapunt",
        "Besluit",
        "Stemming",
        "Zaak",
        "Zaal",
        "Reservering",
        "Document",
        "DocumentActor",
        "DocumentVersie",
        "DocumentPublicatie",
        "Kamerstukdossier",
        "Vergadering",
        "Verslag",
        "Toezegging",
    ]


async def handle_tk_list_entities(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the tk-list-entities tool call."""
    try:
        entities = list_tk_entities()
        return [types.TextContent(type="text", text=str(entities))]
    except Exception as e:
        log.error(f"Error listing TK entities: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="tk-list-entities",
        description="List all available OData entity sets in the Tweedekamer Gegevensmagazijn.",
        inputSchema={"type": "object", "properties": {}},
    )
)
TOOLS_HANDLERS["tk-list-entities"] = handle_tk_list_entities

###################
# Tweedekamer Querying
###################


class TkQueryEntityParams(BaseModel):
    """Parameters for querying a Tweedekamer entity set using OData v4."""

    entity: str = Field(
        ..., description="The name of the entity set (e.g. 'Persoon', 'Fractie')"
    )
    filter: Optional[str] = Field(
        None, description="OData $filter string (e.g., \"Achternaam eq 'Dijkhoff'\")"
    )
    select: Optional[str] = Field(
        None, description="OData $select string (e.g., 'Id,Voornamen,Achternaam')"
    )
    expand: Optional[str] = Field(
        None,
        description="OData $expand string for related entities (e.g., 'FractieZetelPersoon')",
    )
    top: int = Field(default=20, description="OData $top (limit results)")
    skip: int = Field(default=0, description="OData $skip (offset results)")


def query_tk_entity(params: TkQueryEntityParams) -> dict:
    """Execute an OData v4 query against the Tweedekamer API."""
    # Validate entity against the known whitelist to prevent URL path traversal
    known_entities = set(list_tk_entities())
    if params.entity not in known_entities:
        raise ValueError(
            f"Unknown entity '{params.entity}'. Valid entities: {sorted(known_entities)}"
        )
    url = f"{BASE_URL}/{params.entity}"
    query_params = {
        "$top": params.top,
        "$skip": params.skip,
    }
    if params.filter:
        query_params["$filter"] = params.filter
    if params.select:
        query_params["$select"] = params.select
    if params.expand:
        query_params["$expand"] = params.expand

    headers = {"Accept": "application/json"}
    response = httpx.get(url, params=query_params, headers=headers, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def handle_tk_query(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the tk-query tool call."""
    try:
        if not arguments or "entity" not in arguments:
            raise ValueError("entity name is required")

        params = TkQueryEntityParams(**arguments)
        result = query_tk_entity(params)
        return [types.TextContent(type="text", text=serialize_for_llm(result))]
    except Exception as e:
        log.error(
            f"Error querying TK entity {arguments.get('entity') if arguments else ''}: {e}"
        )
        raise


TOOLS.append(
    types.Tool(
        name="tk-query",
        description="Query a Tweedekamer entity set using OData v4 parameters.",
        inputSchema=TkQueryEntityParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["tk-query"] = handle_tk_query


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "nl-tweedekamer", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


# Server initialization
if __name__ == "__main__":
    import anyio

    anyio.run(main)
