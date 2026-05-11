"""
DBnomics Provider

This module provides interfaces to the DBnomics API, which aggregates economic data
from over 100 providers worldwide (IMF, World Bank, ECB, Fed, etc.).

License: DBnomics data is usually open, but specific provider licenses apply.
See https://db.nomics.world/ for details.

API Documentation: https://api.db.nomics.world/apidocs
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.db.nomics.world/v22"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# DBnomics Search
###################

class DBnomicsSearchParams(BaseModel):
    """Parameters for searching DBnomics datasets and series."""
    query: str = Field(..., description="Search query string")
    limit: int = Field(default=10, description="Number of results to return (max 50)")
    offset: int = Field(default=0, description="Number of results to skip")

def search_dbnomics(params: DBnomicsSearchParams) -> Any:
    """Search for datasets and series on DBnomics."""
    query_params = {
        "q": params.query,
        "limit": params.limit,
        "offset": params.offset
    }
    response = http_get(f"{BASE_URL}/search", params=query_params)
    return response.json()

async def handle_dbnomics_search(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the dbnomics-search tool call."""
    try:
        params = DBnomicsSearchParams(**(arguments or {}))
        data = search_dbnomics(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching DBnomics: {e}")
        raise

TOOLS.append(
    types.Tool(
        name="dbnomics-search",
        description="Search for economic datasets and series on DBnomics.",
        inputSchema=DBnomicsSearchParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["dbnomics-search"] = handle_dbnomics_search

###################
# DBnomics Providers
###################

def list_dbnomics_providers() -> Any:
    """List all data providers available on DBnomics."""
    response = http_get(f"{BASE_URL}/providers")
    return response.json()

async def handle_dbnomics_list_providers(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the dbnomics-list-providers tool call."""
    try:
        data = list_dbnomics_providers()
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing DBnomics providers: {e}")
        raise

TOOLS.append(
    types.Tool(
        name="dbnomics-list-providers",
        description="List all economic data providers aggregated by DBnomics.",
        inputSchema={"type": "object", "properties": {}},
    )
)
TOOLS_HANDLERS["dbnomics-list-providers"] = handle_dbnomics_list_providers

###################
# DBnomics Series
###################

class DBnomicsSeriesParams(BaseModel):
    """Parameters for fetching DBnomics series data."""
    series_ids: str = Field(..., description="Comma-separated list of series IDs (e.g. 'IMF/WEO:2024-04/ABW.NGDP_RPCH')")

def fetch_dbnomics_series(params: DBnomicsSeriesParams) -> Any:
    """Fetch data for specific series from DBnomics."""
    query_params = {"series_ids": params.series_ids}
    response = http_get(f"{BASE_URL}/series", params=query_params)
    return response.json()

async def handle_dbnomics_series(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the dbnomics-series tool call."""
    try:
        params = DBnomicsSeriesParams(**(arguments or {}))
        data = fetch_dbnomics_series(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching DBnomics series: {e}")
        raise

TOOLS.append(
    types.Tool(
        name="dbnomics-series",
        description="Fetch data for specific economic series from DBnomics.",
        inputSchema=DBnomicsSeriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["dbnomics-series"] = handle_dbnomics_series

async def main(transport: str = "stdio", port: int = 8000):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-dbnomics", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port)

if __name__ == "__main__":
    import anyio
    anyio.run(main)
