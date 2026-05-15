"""
WHO Global Health Observatory (GHO) OData Provider

This module provides interfaces to the World Health Organization's Global
Health Observatory (GHO) OData v4 API, which exposes thousands of health
indicators with country, region, sex and age-group dimensions.

Source: https://www.who.int/data/gho/info/gho-odata-api
License: WHO data is generally available under terms permitting reuse with
attribution; consult the WHO data policy at
https://www.who.int/about/policies/publishing/copyright for specifics.

Fair-use notes:
- The OData API does not require an API key.
- Use ``$top`` and ``$skip`` to paginate, and ``$filter`` to narrow result
  sizes when retrieving indicator time-series.

Features:
- Indicator catalogue (paginated)
- Per-indicator time-series data
- Dimension catalogue
- Dimension values (e.g. countries, SEX values, GHO topics)
- Convenience listing of countries

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
PROVIDER_ID = "global-who-gho"
BASE_URL = "https://ghoapi.azureedge.net/api"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# List Indicators
###################


class WhoGhoListIndicatorsParams(BaseModel):
    """Parameters for listing GHO indicators."""

    top: Optional[int] = Field(
        default=200,
        description="Maximum number of indicators to return ($top)",
    )
    skip: Optional[int] = Field(
        default=None,
        description="Number of indicators to skip for pagination ($skip)",
    )


def fetch_list_indicators(params: WhoGhoListIndicatorsParams) -> dict:
    """Fetch GHO indicators with OData pagination."""
    query_params: dict[str, Any] = {}
    if params.top is not None:
        query_params["$top"] = params.top
    if params.skip is not None:
        query_params["$skip"] = params.skip

    response = http_get(
        f"{BASE_URL}/Indicator",
        params=query_params or None,
        timeout=30.0,
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_list_indicators(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the who-gho-list-indicators tool call."""
    try:
        params = WhoGhoListIndicatorsParams(**(arguments or {}))
        data = fetch_list_indicators(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing WHO GHO indicators: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="who-gho-list-indicators",
        description=(
            "List WHO Global Health Observatory indicators with OData $top "
            "and $skip pagination."
        ),
        inputSchema=WhoGhoListIndicatorsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["who-gho-list-indicators"] = handle_list_indicators


###################
# Get Indicator Data
###################


class WhoGhoGetIndicatorDataParams(BaseModel):
    """Parameters for fetching indicator time-series data."""

    indicator_code: str = Field(
        ...,
        description="Indicator code (e.g. 'WHOSIS_000001' for life expectancy)",
    )
    top: Optional[int] = Field(
        default=500,
        description="Maximum number of rows to return ($top)",
    )
    filter: Optional[str] = Field(
        None,
        description="Optional OData $filter (e.g. \"SpatialDim eq 'USA'\")",
    )


def fetch_get_indicator_data(params: WhoGhoGetIndicatorDataParams) -> dict:
    """Fetch time-series data for a single indicator."""
    query_params: dict[str, Any] = {}
    if params.top is not None:
        query_params["$top"] = params.top
    if params.filter:
        query_params["$filter"] = params.filter

    response = http_get(
        f"{BASE_URL}/{params.indicator_code}",
        params=query_params or None,
        timeout=60.0,
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_get_indicator_data(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the who-gho-get-indicator-data tool call."""
    try:
        if not arguments or "indicator_code" not in arguments:
            raise ValueError("indicator_code is required")
        params = WhoGhoGetIndicatorDataParams(**arguments)
        data = fetch_get_indicator_data(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching WHO GHO indicator data: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="who-gho-get-indicator-data",
        description=(
            "Fetch time-series data for a WHO GHO indicator code (e.g. "
            "WHOSIS_000001). Supports OData $top and $filter."
        ),
        inputSchema=WhoGhoGetIndicatorDataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["who-gho-get-indicator-data"] = handle_get_indicator_data


###################
# List Dimensions
###################


class WhoGhoListDimensionsParams(BaseModel):
    """Parameters for listing GHO dimensions."""

    pass


def fetch_list_dimensions(_params: WhoGhoListDimensionsParams) -> dict:
    """Fetch the list of GHO dimensions."""
    response = http_get(f"{BASE_URL}/Dimension", timeout=30.0, provider=PROVIDER_ID)
    return response.json()


async def handle_list_dimensions(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the who-gho-list-dimensions tool call."""
    try:
        params = WhoGhoListDimensionsParams(**(arguments or {}))
        data = fetch_list_dimensions(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing WHO GHO dimensions: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="who-gho-list-dimensions",
        description="List the dimensions exposed by the WHO GHO OData API (e.g. SEX, COUNTRY, GHO).",
        inputSchema=WhoGhoListDimensionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["who-gho-list-dimensions"] = handle_list_dimensions


###################
# List Dimension Values
###################


class WhoGhoListDimensionValuesParams(BaseModel):
    """Parameters for listing values of a specific GHO dimension."""

    dim: str = Field(
        ...,
        description="Dimension code (e.g. 'COUNTRY', 'SEX', 'GHO')",
    )


def fetch_list_dimension_values(params: WhoGhoListDimensionValuesParams) -> dict:
    """Fetch the values for a specific GHO dimension."""
    response = http_get(
        f"{BASE_URL}/DIMENSION/{params.dim}/DimensionValues",
        timeout=30.0,
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_list_dimension_values(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the who-gho-list-dimension-values tool call."""
    try:
        if not arguments or "dim" not in arguments:
            raise ValueError("dim is required")
        params = WhoGhoListDimensionValuesParams(**arguments)
        data = fetch_list_dimension_values(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing WHO GHO dimension values: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="who-gho-list-dimension-values",
        description=(
            "List the values of a specific WHO GHO dimension (e.g. COUNTRY, SEX, GHO)."
        ),
        inputSchema=WhoGhoListDimensionValuesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["who-gho-list-dimension-values"] = handle_list_dimension_values


###################
# List Countries
###################


class WhoGhoListCountriesParams(BaseModel):
    """Parameters for listing GHO countries (COUNTRY dimension values)."""

    pass


def fetch_list_countries(_params: WhoGhoListCountriesParams) -> dict:
    """Fetch the COUNTRY dimension values."""
    response = http_get(
        f"{BASE_URL}/DIMENSION/COUNTRY/DimensionValues",
        timeout=30.0,
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_list_countries(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the who-gho-list-countries tool call."""
    try:
        params = WhoGhoListCountriesParams(**(arguments or {}))
        data = fetch_list_countries(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing WHO GHO countries: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="who-gho-list-countries",
        description="List the countries (COUNTRY dimension values) tracked by WHO GHO.",
        inputSchema=WhoGhoListCountriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["who-gho-list-countries"] = handle_list_countries


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-who-gho", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
