"""
Federal Reserve Economic Data (FRED) Provider

This module provides interfaces to the FRED API hosted by the Federal Reserve
Bank of St. Louis, exposing hundreds of thousands of US and international
economic time series (GDP, CPI, unemployment, interest rates, etc.).

License: FRED data is generally free to use; some series carry source-specific
restrictions. See https://fred.stlouisfed.org/legal/ for terms.

API key:
    Requires the FRED_API_KEY environment variable. Obtain a free key at
    https://fred.stlouisfed.org/docs/api/api_key.html. There is no demo
    fallback; handlers raise ValueError if the key is missing.

Features:
- Series search and metadata lookup
- Time-series observation retrieval
- Category / release / source catalogues

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
import os
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.stlouisfed.org/fred"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _require_key() -> str:
    """Return the FRED API key from the environment, or raise.

    Raises:
        ValueError: If FRED_API_KEY is not set.
    """
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError(
            "FRED_API_KEY environment variable is required for the us_fred provider"
        )
    return api_key


###################
# Search Series
###################


class FREDSearchSeriesParams(BaseModel):
    """Parameters for searching FRED series."""

    search_text: str = Field(..., description="Free-text query (e.g. 'unemployment')")
    limit: int = Field(default=20, description="Maximum number of results")
    order_by: Optional[str] = Field(
        None,
        description="Sort field (e.g. 'search_rank', 'popularity', 'last_updated')",
    )


def fetch_search_series(params: FREDSearchSeriesParams) -> dict:
    """Search FRED series by free-text query."""
    api_key = _require_key()
    query_params: dict[str, Any] = {
        "search_text": params.search_text,
        "limit": params.limit,
        "api_key": api_key,
        "file_type": "json",
    }
    if params.order_by is not None:
        query_params["order_by"] = params.order_by

    response = http_get(f"{BASE_URL}/series/search", params=query_params, timeout=30.0)
    return response.json()


async def handle_search_series(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fred-search-series tool call."""
    try:
        if not arguments or "search_text" not in arguments:
            raise ValueError("search_text is required")
        params = FREDSearchSeriesParams(**arguments)
        data = fetch_search_series(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching FRED series: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fred-search-series",
        description="Search FRED series by free-text query (e.g. 'unemployment').",
        inputSchema=FREDSearchSeriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fred-search-series"] = handle_search_series


###################
# Get Series
###################


class FREDGetSeriesParams(BaseModel):
    """Parameters for fetching a single FRED series."""

    series_id: str = Field(..., description="FRED series ID (e.g. 'GDP', 'UNRATE')")


def fetch_get_series(params: FREDGetSeriesParams) -> dict:
    """Fetch metadata for a single FRED series."""
    api_key = _require_key()
    query_params = {
        "series_id": params.series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    response = http_get(f"{BASE_URL}/series", params=query_params, timeout=30.0)
    return response.json()


async def handle_get_series(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fred-get-series tool call."""
    try:
        if not arguments or "series_id" not in arguments:
            raise ValueError("series_id is required")
        params = FREDGetSeriesParams(**arguments)
        data = fetch_get_series(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching FRED series: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fred-get-series",
        description="Get metadata for a single FRED series by ID.",
        inputSchema=FREDGetSeriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fred-get-series"] = handle_get_series


###################
# Get Series Observations
###################


class FREDGetSeriesObservationsParams(BaseModel):
    """Parameters for fetching observations of a FRED series."""

    series_id: str = Field(..., description="FRED series ID (e.g. 'GDP', 'UNRATE')")
    observation_start: Optional[str] = Field(
        None, description="Start date (YYYY-MM-DD)"
    )
    observation_end: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    limit: int = Field(default=100, description="Maximum number of observations")


def fetch_get_series_observations(params: FREDGetSeriesObservationsParams) -> dict:
    """Fetch observations (data points) for a FRED series."""
    api_key = _require_key()
    query_params: dict[str, Any] = {
        "series_id": params.series_id,
        "limit": params.limit,
        "api_key": api_key,
        "file_type": "json",
    }
    if params.observation_start is not None:
        query_params["observation_start"] = params.observation_start
    if params.observation_end is not None:
        query_params["observation_end"] = params.observation_end

    response = http_get(
        f"{BASE_URL}/series/observations", params=query_params, timeout=30.0
    )
    return response.json()


async def handle_get_series_observations(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fred-get-series-observations tool call."""
    try:
        if not arguments or "series_id" not in arguments:
            raise ValueError("series_id is required")
        params = FREDGetSeriesObservationsParams(**arguments)
        data = fetch_get_series_observations(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching FRED series observations: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fred-get-series-observations",
        description="Fetch the time-series observations of a FRED series, optionally filtered by date range.",
        inputSchema=FREDGetSeriesObservationsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fred-get-series-observations"] = handle_get_series_observations


###################
# List Categories
###################


class FREDListCategoriesParams(BaseModel):
    """Parameters for listing FRED child categories."""

    category_id: int = Field(
        default=0, description="Parent category ID (0 is the root)"
    )


def fetch_list_categories(params: FREDListCategoriesParams) -> dict:
    """List the child categories of a FRED category."""
    api_key = _require_key()
    query_params = {
        "category_id": params.category_id,
        "api_key": api_key,
        "file_type": "json",
    }
    response = http_get(
        f"{BASE_URL}/category/children", params=query_params, timeout=30.0
    )
    return response.json()


async def handle_list_categories(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fred-list-categories tool call."""
    try:
        params = FREDListCategoriesParams(**(arguments or {}))
        data = fetch_list_categories(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing FRED categories: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fred-list-categories",
        description="List the child categories of a FRED category (default root, ID 0).",
        inputSchema=FREDListCategoriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fred-list-categories"] = handle_list_categories


###################
# Get Category
###################


class FREDGetCategoryParams(BaseModel):
    """Parameters for fetching a single FRED category."""

    category_id: int = Field(..., description="FRED category ID")


def fetch_get_category(params: FREDGetCategoryParams) -> dict:
    """Fetch metadata for a single FRED category."""
    api_key = _require_key()
    query_params = {
        "category_id": params.category_id,
        "api_key": api_key,
        "file_type": "json",
    }
    response = http_get(f"{BASE_URL}/category", params=query_params, timeout=30.0)
    return response.json()


async def handle_get_category(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fred-get-category tool call."""
    try:
        if not arguments or "category_id" not in arguments:
            raise ValueError("category_id is required")
        params = FREDGetCategoryParams(**arguments)
        data = fetch_get_category(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching FRED category: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fred-get-category",
        description="Get metadata for a single FRED category by ID.",
        inputSchema=FREDGetCategoryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fred-get-category"] = handle_get_category


###################
# List Releases
###################


class FREDListReleasesParams(BaseModel):
    """Parameters for listing FRED releases."""

    limit: int = Field(default=100, description="Maximum number of releases to return")


def fetch_list_releases(params: FREDListReleasesParams) -> dict:
    """List the FRED data releases."""
    api_key = _require_key()
    query_params = {
        "limit": params.limit,
        "api_key": api_key,
        "file_type": "json",
    }
    response = http_get(f"{BASE_URL}/releases", params=query_params, timeout=30.0)
    return response.json()


async def handle_list_releases(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fred-list-releases tool call."""
    try:
        params = FREDListReleasesParams(**(arguments or {}))
        data = fetch_list_releases(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing FRED releases: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fred-list-releases",
        description="List FRED data releases.",
        inputSchema=FREDListReleasesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fred-list-releases"] = handle_list_releases


###################
# Get Release
###################


class FREDGetReleaseParams(BaseModel):
    """Parameters for fetching a single FRED release."""

    release_id: int = Field(..., description="FRED release ID")


def fetch_get_release(params: FREDGetReleaseParams) -> dict:
    """Fetch metadata for a single FRED release."""
    api_key = _require_key()
    query_params = {
        "release_id": params.release_id,
        "api_key": api_key,
        "file_type": "json",
    }
    response = http_get(f"{BASE_URL}/release", params=query_params, timeout=30.0)
    return response.json()


async def handle_get_release(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fred-get-release tool call."""
    try:
        if not arguments or "release_id" not in arguments:
            raise ValueError("release_id is required")
        params = FREDGetReleaseParams(**arguments)
        data = fetch_get_release(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching FRED release: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fred-get-release",
        description="Get metadata for a single FRED release by ID.",
        inputSchema=FREDGetReleaseParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fred-get-release"] = handle_get_release


###################
# List Sources
###################


class FREDListSourcesParams(BaseModel):
    """Parameters for listing FRED data sources."""

    pass


def fetch_list_sources(_params: FREDListSourcesParams) -> dict:
    """List the FRED data sources."""
    api_key = _require_key()
    query_params = {"api_key": api_key, "file_type": "json"}
    response = http_get(f"{BASE_URL}/sources", params=query_params, timeout=30.0)
    return response.json()


async def handle_list_sources(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fred-list-sources tool call."""
    try:
        params = FREDListSourcesParams(**(arguments or {}))
        data = fetch_list_sources(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing FRED sources: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fred-list-sources",
        description="List FRED data sources (institutions that publish series).",
        inputSchema=FREDListSourcesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fred-list-sources"] = handle_list_sources


async def main():
    from mcp.server.stdio import stdio_server

    from opendata_mcp.utils import create_mcp_server

    server = create_mcp_server(
        "us-fred", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
