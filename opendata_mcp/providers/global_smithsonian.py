"""
Smithsonian Open Access Provider

This module exposes the Smithsonian Institution's Open Access API, which
provides programmatic access to millions of CC0 collection items spanning
museums, archives, libraries, and research centers.

License note:
    Items returned by Open Access are released under CC0. Always inspect
    the per-record fields (e.g. ``content.descriptiveNonRepeating.metadata_usage``)
    before redistribution; non-CC0 items may appear in some endpoints.

Authentication:
    Requires ``SMITHSONIAN_API_KEY`` to be set in the environment. Free
    keys can be obtained at https://api.data.gov/signup/.

Features:
- Full-text search across the catalog
- Single-record retrieval
- Controlled vocabulary listings (culture, topic, geo, date)
- Per-category search (e.g. art_design)
- Aggregate statistics

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.
"""

import logging
import os
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.si.edu/openaccess/api/v1.0"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _require_api_key() -> str:
    """Read the Smithsonian API key from the environment.

    Raises:
        ValueError: If ``SMITHSONIAN_API_KEY`` is not configured.
    """
    api_key = os.getenv("SMITHSONIAN_API_KEY")
    if not api_key:
        raise ValueError(
            "SMITHSONIAN_API_KEY environment variable is required. "
            "Sign up for a free key at https://api.data.gov/signup/."
        )
    return api_key


###################
# Search
###################


class SmithsonianSearchParams(BaseModel):
    """Parameters for searching the Smithsonian Open Access catalog."""

    q: str = Field(..., description="Free-text search query.")
    rows: int = Field(
        default=10, description="Number of records to return per page (max 1000)."
    )
    start: int = Field(default=0, description="Offset into the result set.")
    sort: Optional[str] = Field(
        None,
        description="Sort order (e.g. 'relevancy', 'newest', 'updated', 'random').",
    )


def fetch_smithsonian_search(params: SmithsonianSearchParams) -> dict:
    """Call the Smithsonian /search endpoint."""
    query_params: dict[str, Any] = {
        "q": params.q,
        "rows": params.rows,
        "start": params.start,
        "api_key": _require_api_key(),
    }
    if params.sort:
        query_params["sort"] = params.sort
    response = http_get(f"{BASE_URL}/search", params=query_params)
    return response.json()


async def handle_smithsonian_search(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the smithsonian-search tool call."""
    try:
        if not arguments or "q" not in arguments:
            raise ValueError("q is required")
        params = SmithsonianSearchParams(**arguments)
        data = fetch_smithsonian_search(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error searching Smithsonian: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="smithsonian-search",
        description="Full-text search across the Smithsonian Open Access catalog. Requires SMITHSONIAN_API_KEY.",
        inputSchema=SmithsonianSearchParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["smithsonian-search"] = handle_smithsonian_search


###################
# Get Content
###################


class SmithsonianGetContentParams(BaseModel):
    """Parameters for retrieving a single Smithsonian record."""

    id: str = Field(
        ...,
        description="Smithsonian Open Access record identifier (e.g. 'ld1-1623427820028-1623427826871-0').",
    )


def fetch_smithsonian_get_content(params: SmithsonianGetContentParams) -> dict:
    """Call the Smithsonian /content/{id} endpoint."""
    query_params: dict[str, Any] = {"api_key": _require_api_key()}
    response = http_get(f"{BASE_URL}/content/{params.id}", params=query_params)
    return response.json()


async def handle_smithsonian_get_content(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the smithsonian-get-content tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = SmithsonianGetContentParams(**arguments)
        data = fetch_smithsonian_get_content(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching Smithsonian content: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="smithsonian-get-content",
        description="Fetch a single Smithsonian Open Access record by ID. Requires SMITHSONIAN_API_KEY.",
        inputSchema=SmithsonianGetContentParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["smithsonian-get-content"] = handle_smithsonian_get_content


###################
# List Terms
###################


class SmithsonianListTermsParams(BaseModel):
    """Parameters for listing controlled-vocabulary terms."""

    category: str = Field(
        ...,
        description="Term category (culture, topic, geo_location, date, name, place, object_type, etc.).",
    )
    rows: int = Field(default=10, description="Number of terms to return.")
    starts_with: Optional[str] = Field(
        None, description="Filter terms whose values start with this string."
    )


def fetch_smithsonian_list_terms(params: SmithsonianListTermsParams) -> dict:
    """Call the Smithsonian /terms/{category} endpoint."""
    query_params: dict[str, Any] = {
        "api_key": _require_api_key(),
        "rows": params.rows,
    }
    if params.starts_with:
        query_params["starts_with"] = params.starts_with
    response = http_get(f"{BASE_URL}/terms/{params.category}", params=query_params)
    return response.json()


async def handle_smithsonian_list_terms(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the smithsonian-list-terms tool call."""
    try:
        if not arguments or "category" not in arguments:
            raise ValueError("category is required")
        params = SmithsonianListTermsParams(**arguments)
        data = fetch_smithsonian_list_terms(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error listing Smithsonian terms: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="smithsonian-list-terms",
        description="List controlled vocabulary terms (culture, topic, geo_location, date, etc.). Requires SMITHSONIAN_API_KEY.",
        inputSchema=SmithsonianListTermsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["smithsonian-list-terms"] = handle_smithsonian_list_terms


###################
# Search by Category
###################


class SmithsonianSearchCategoryParams(BaseModel):
    """Parameters for category-scoped search."""

    category: str = Field(
        ..., description="Category slug (e.g. 'art_design', 'history_culture')."
    )
    q: str = Field(..., description="Free-text search query.")
    rows: int = Field(default=10, description="Number of records per page.")
    start: int = Field(default=0, description="Offset into the result set.")


def fetch_smithsonian_search_category(
    params: SmithsonianSearchCategoryParams,
) -> dict:
    """Call the Smithsonian /category/{category}/search endpoint."""
    query_params: dict[str, Any] = {
        "q": params.q,
        "rows": params.rows,
        "start": params.start,
        "api_key": _require_api_key(),
    }
    response = http_get(
        f"{BASE_URL}/category/{params.category}/search", params=query_params
    )
    return response.json()


async def handle_smithsonian_search_category(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the smithsonian-search-category tool call."""
    try:
        if not arguments or "category" not in arguments or "q" not in arguments:
            raise ValueError("category and q are required")
        params = SmithsonianSearchCategoryParams(**arguments)
        data = fetch_smithsonian_search_category(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error searching Smithsonian category: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="smithsonian-search-category",
        description="Search within a specific Smithsonian category (e.g. 'art_design'). Requires SMITHSONIAN_API_KEY.",
        inputSchema=SmithsonianSearchCategoryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["smithsonian-search-category"] = handle_smithsonian_search_category


###################
# Stats
###################


class SmithsonianStatsParams(BaseModel):
    """Parameters for retrieving aggregate stats (no inputs)."""


def fetch_smithsonian_stats(params: SmithsonianStatsParams) -> dict:
    """Call the Smithsonian /stats endpoint."""
    query_params: dict[str, Any] = {"api_key": _require_api_key()}
    response = http_get(f"{BASE_URL}/stats", params=query_params)
    return response.json()


async def handle_smithsonian_stats(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the smithsonian-stats tool call."""
    try:
        params = SmithsonianStatsParams(**(arguments or {}))
        data = fetch_smithsonian_stats(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching Smithsonian stats: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="smithsonian-stats",
        description="Return aggregate statistics for the Smithsonian Open Access catalog. Requires SMITHSONIAN_API_KEY.",
        inputSchema=SmithsonianStatsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["smithsonian-stats"] = handle_smithsonian_stats


async def main():
    from mcp.server.stdio import stdio_server

    from opendata_mcp.utils import create_mcp_server

    server = create_mcp_server(
        "global-smithsonian", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
