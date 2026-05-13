"""
World Bank Open Data Provider

This module provides interfaces to the World Bank Open Data API, which exposes
development indicators (economic, demographic, environmental, social) for
countries and regions worldwide.

License: Most World Bank data is published under CC BY 4.0. See
https://datacatalog.worldbank.org/public-licenses for details.

Features:
- Country / income-level / topic / source catalogues
- Indicator discovery and metadata
- Time-series indicator data per country
- No API key required

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.worldbank.org/v2"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# List Countries
###################


class WorldBankListCountriesParams(BaseModel):
    """Parameters for listing World Bank countries."""

    page: int = Field(default=1, description="Page number (1-indexed)")
    per_page: int = Field(default=300, description="Number of results per page")


def fetch_list_countries(params: WorldBankListCountriesParams) -> list:
    """Fetch the list of countries from the World Bank API."""
    query_params = {
        "format": "json",
        "per_page": params.per_page,
        "page": params.page,
    }
    response = http_get(f"{BASE_URL}/country", params=query_params, timeout=30.0)
    return response.json()


async def handle_list_countries(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the world-bank-list-countries tool call."""
    try:
        params = WorldBankListCountriesParams(**(arguments or {}))
        data = fetch_list_countries(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching World Bank countries: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="world-bank-list-countries",
        description="List all countries and regions tracked by the World Bank. Returns a 2-element array [metadata, results].",
        inputSchema=WorldBankListCountriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["world-bank-list-countries"] = handle_list_countries


###################
# Get Country
###################


class WorldBankGetCountryParams(BaseModel):
    """Parameters for fetching a single country."""

    country: str = Field(
        ..., description="ISO2 or ISO3 country code (e.g. 'BR' or 'BRA')"
    )


def fetch_get_country(params: WorldBankGetCountryParams) -> list:
    """Fetch a single country record from the World Bank API."""
    query_params = {"format": "json"}
    response = http_get(
        f"{BASE_URL}/country/{params.country}", params=query_params, timeout=30.0
    )
    return response.json()


async def handle_get_country(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the world-bank-get-country tool call."""
    try:
        if not arguments or "country" not in arguments:
            raise ValueError("country is required")
        params = WorldBankGetCountryParams(**arguments)
        data = fetch_get_country(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching World Bank country: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="world-bank-get-country",
        description="Get details for a single country by ISO2 or ISO3 code.",
        inputSchema=WorldBankGetCountryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["world-bank-get-country"] = handle_get_country


###################
# List Indicators
###################


class WorldBankListIndicatorsParams(BaseModel):
    """Parameters for listing World Bank indicators."""

    page: int = Field(default=1, description="Page number (1-indexed)")
    per_page: int = Field(default=200, description="Number of indicators per page")


def fetch_list_indicators(params: WorldBankListIndicatorsParams) -> list:
    """Fetch the indicator catalogue from the World Bank API."""
    query_params = {
        "format": "json",
        "per_page": params.per_page,
        "page": params.page,
    }
    response = http_get(f"{BASE_URL}/indicator", params=query_params, timeout=30.0)
    return response.json()


async def handle_list_indicators(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the world-bank-list-indicators tool call."""
    try:
        params = WorldBankListIndicatorsParams(**(arguments or {}))
        data = fetch_list_indicators(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching World Bank indicators: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="world-bank-list-indicators",
        description="List World Bank indicators. Returns a 2-element array [metadata, results].",
        inputSchema=WorldBankListIndicatorsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["world-bank-list-indicators"] = handle_list_indicators


###################
# Search Indicators
###################


class WorldBankSearchIndicatorsParams(BaseModel):
    """Parameters for searching World Bank indicators by source or topic."""

    source: Optional[int] = Field(
        None, description="Filter by source ID (see world-bank-list-sources)"
    )
    topic: Optional[int] = Field(
        None, description="Filter by topic ID (see world-bank-list-topics)"
    )
    per_page: int = Field(default=200, description="Number of indicators per page")
    page: int = Field(default=1, description="Page number (1-indexed)")


def fetch_search_indicators(params: WorldBankSearchIndicatorsParams) -> list:
    """Search indicators filtered by source and/or topic."""
    query_params: dict[str, Any] = {
        "format": "json",
        "per_page": params.per_page,
        "page": params.page,
    }
    if params.source is not None:
        query_params["source"] = params.source
    if params.topic is not None:
        query_params["topic"] = params.topic

    response = http_get(f"{BASE_URL}/indicator", params=query_params, timeout=30.0)
    return response.json()


async def handle_search_indicators(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the world-bank-search-indicators tool call."""
    try:
        params = WorldBankSearchIndicatorsParams(**(arguments or {}))
        data = fetch_search_indicators(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching World Bank indicators: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="world-bank-search-indicators",
        description="Search World Bank indicators by source ID and/or topic ID.",
        inputSchema=WorldBankSearchIndicatorsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["world-bank-search-indicators"] = handle_search_indicators


###################
# Get Indicator Data
###################


class WorldBankIndicatorDataParams(BaseModel):
    """Parameters for fetching indicator time-series for a country."""

    country: str = Field(
        ...,
        description="ISO2 or ISO3 country code (e.g. 'US' or 'USA'); 'all' is allowed",
    )
    indicator: str = Field(..., description="Indicator code (e.g. 'NY.GDP.MKTP.CD')")
    start: Optional[int] = Field(
        None, description="Start year for the time-series (e.g. 2000)"
    )
    end: Optional[int] = Field(
        None, description="End year for the time-series (e.g. 2020)"
    )
    per_page: int = Field(default=100, description="Number of results per page")
    page: int = Field(default=1, description="Page number (1-indexed)")


def fetch_indicator_data(params: WorldBankIndicatorDataParams) -> list:
    """Fetch indicator time-series for a given country."""
    query_params: dict[str, Any] = {
        "format": "json",
        "per_page": params.per_page,
        "page": params.page,
    }
    if params.start is not None and params.end is not None:
        query_params["date"] = f"{params.start}:{params.end}"

    url = f"{BASE_URL}/country/{params.country}/indicator/{params.indicator}"
    response = http_get(url, params=query_params, timeout=30.0)
    return response.json()


async def handle_get_indicator_data(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the world-bank-get-indicator-data tool call."""
    try:
        if not arguments or "country" not in arguments or "indicator" not in arguments:
            raise ValueError("country and indicator are required")
        params = WorldBankIndicatorDataParams(**arguments)
        data = fetch_indicator_data(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching World Bank indicator data: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="world-bank-get-indicator-data",
        description="Fetch indicator time-series values for a country and indicator code. Returns a 2-element array [metadata, results].",
        inputSchema=WorldBankIndicatorDataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["world-bank-get-indicator-data"] = handle_get_indicator_data


###################
# List Topics
###################


class WorldBankListTopicsParams(BaseModel):
    """Parameters for listing World Bank topics."""

    pass


def fetch_list_topics(_params: WorldBankListTopicsParams) -> list:
    """Fetch the list of World Bank topics."""
    response = http_get(f"{BASE_URL}/topic", params={"format": "json"}, timeout=30.0)
    return response.json()


async def handle_list_topics(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the world-bank-list-topics tool call."""
    try:
        params = WorldBankListTopicsParams(**(arguments or {}))
        data = fetch_list_topics(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching World Bank topics: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="world-bank-list-topics",
        description="List the topic taxonomy used by the World Bank to classify indicators.",
        inputSchema=WorldBankListTopicsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["world-bank-list-topics"] = handle_list_topics


###################
# List Sources
###################


class WorldBankListSourcesParams(BaseModel):
    """Parameters for listing World Bank data sources."""

    pass


def fetch_list_sources(_params: WorldBankListSourcesParams) -> list:
    """Fetch the list of World Bank data sources."""
    response = http_get(f"{BASE_URL}/source", params={"format": "json"}, timeout=30.0)
    return response.json()


async def handle_list_sources(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the world-bank-list-sources tool call."""
    try:
        params = WorldBankListSourcesParams(**(arguments or {}))
        data = fetch_list_sources(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching World Bank sources: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="world-bank-list-sources",
        description="List the data sources powering World Bank indicators.",
        inputSchema=WorldBankListSourcesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["world-bank-list-sources"] = handle_list_sources


###################
# List Income Levels
###################


class WorldBankListIncomeLevelsParams(BaseModel):
    """Parameters for listing World Bank income-level classifications."""

    pass


def fetch_list_income_levels(_params: WorldBankListIncomeLevelsParams) -> list:
    """Fetch the World Bank income-level classifications."""
    response = http_get(
        f"{BASE_URL}/incomeLevel", params={"format": "json"}, timeout=30.0
    )
    return response.json()


async def handle_list_income_levels(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the world-bank-list-income-levels tool call."""
    try:
        params = WorldBankListIncomeLevelsParams(**(arguments or {}))
        data = fetch_list_income_levels(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching World Bank income levels: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="world-bank-list-income-levels",
        description="List World Bank income-level classifications (e.g. low, lower-middle, upper-middle, high).",
        inputSchema=WorldBankListIncomeLevelsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["world-bank-list-income-levels"] = handle_list_income_levels


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-world-bank", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
