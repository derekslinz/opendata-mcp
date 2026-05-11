"""
disease.sh Open API Provider

This module provides interfaces to the disease.sh open API, which aggregates
COVID-19 data from Johns Hopkins University, Worldometers and other sources,
plus influenza and vaccine coverage endpoints.

Source: https://disease.sh
License: disease.sh data is made available for free public use under the
upstream providers' terms (Johns Hopkins CSSE, Worldometers, etc.). Always
attribute the upstream source where required.

Fair-use notes:
- No API key is required.
- The endpoints aggregate large public datasets; please cache responses
  client-side rather than polling at high frequency.

Features:
- Global COVID-19 aggregates
- All-countries COVID-19 data (sorted)
- Country-level COVID-19 data
- Historical (global and per-country) COVID-19 time-series
- Vaccine coverage time-series

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://disease.sh/v3/covid-19"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Global Aggregate
###################


class DiseaseShGlobalParams(BaseModel):
    """Parameters for fetching worldwide COVID-19 aggregate."""

    pass


def fetch_global(_params: DiseaseShGlobalParams) -> dict:
    """Fetch worldwide aggregate COVID-19 totals from /all."""
    response = http_get(f"{BASE_URL}/all", timeout=30.0)
    return response.json()


async def handle_global(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the disease-sh-global tool call."""
    try:
        params = DiseaseShGlobalParams(**(arguments or {}))
        data = fetch_global(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching disease.sh global aggregate: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="disease-sh-global",
        description="Get worldwide aggregate COVID-19 totals (cases, deaths, recovered, tests).",
        inputSchema=DiseaseShGlobalParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["disease-sh-global"] = handle_global


###################
# Countries (sorted)
###################


class DiseaseShCountriesParams(BaseModel):
    """Parameters for listing COVID-19 totals across all countries."""

    sort: Optional[str] = Field(
        default="cases",
        description="Sort field (e.g. 'cases', 'deaths', 'recovered')",
    )


def fetch_countries(params: DiseaseShCountriesParams) -> list:
    """Fetch COVID-19 totals for all countries."""
    query_params: dict[str, Any] = {}
    if params.sort:
        query_params["sort"] = params.sort

    response = http_get(
        f"{BASE_URL}/countries",
        params=query_params or None,
        timeout=30.0,
    )
    return response.json()


async def handle_countries(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the disease-sh-countries tool call."""
    try:
        params = DiseaseShCountriesParams(**(arguments or {}))
        data = fetch_countries(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching disease.sh countries: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="disease-sh-countries",
        description="Get COVID-19 totals across all countries, sorted (default: by cases).",
        inputSchema=DiseaseShCountriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["disease-sh-countries"] = handle_countries


###################
# Single Country
###################


class DiseaseShCountryParams(BaseModel):
    """Parameters for fetching COVID-19 totals for a single country."""

    country: str = Field(
        ..., description="Country name or ISO2/ISO3 code (e.g. 'USA', 'France')"
    )


def fetch_country(params: DiseaseShCountryParams) -> dict:
    """Fetch COVID-19 totals for a single country."""
    response = http_get(
        f"{BASE_URL}/countries/{params.country}",
        timeout=30.0,
    )
    return response.json()


async def handle_country(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the disease-sh-country tool call."""
    try:
        if not arguments or "country" not in arguments:
            raise ValueError("country is required")
        params = DiseaseShCountryParams(**arguments)
        data = fetch_country(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching disease.sh country: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="disease-sh-country",
        description="Get COVID-19 totals for a single country (name or ISO2/ISO3 code).",
        inputSchema=DiseaseShCountryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["disease-sh-country"] = handle_country


###################
# Historical (All)
###################


class DiseaseShHistoricalAllParams(BaseModel):
    """Parameters for global historical COVID-19 data."""

    lastdays: Optional[int] = Field(
        default=30,
        description="Number of days of history to return (use a large value or 'all' upstream)",
    )


def fetch_historical_all(params: DiseaseShHistoricalAllParams) -> dict:
    """Fetch worldwide historical COVID-19 data."""
    query_params: dict[str, Any] = {}
    if params.lastdays is not None:
        query_params["lastdays"] = params.lastdays

    response = http_get(
        f"{BASE_URL}/historical/all",
        params=query_params or None,
        timeout=30.0,
    )
    return response.json()


async def handle_historical_all(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the disease-sh-historical-all tool call."""
    try:
        params = DiseaseShHistoricalAllParams(**(arguments or {}))
        data = fetch_historical_all(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching disease.sh historical all: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="disease-sh-historical-all",
        description="Get worldwide historical COVID-19 data over the last N days.",
        inputSchema=DiseaseShHistoricalAllParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["disease-sh-historical-all"] = handle_historical_all


###################
# Historical (Country)
###################


class DiseaseShHistoricalCountryParams(BaseModel):
    """Parameters for per-country historical COVID-19 data."""

    country: str = Field(..., description="Country name or ISO2/ISO3 code")
    lastdays: Optional[int] = Field(
        default=30,
        description="Number of days of history to return",
    )


def fetch_historical_country(params: DiseaseShHistoricalCountryParams) -> dict:
    """Fetch per-country historical COVID-19 data."""
    query_params: dict[str, Any] = {}
    if params.lastdays is not None:
        query_params["lastdays"] = params.lastdays

    response = http_get(
        f"{BASE_URL}/historical/{params.country}",
        params=query_params or None,
        timeout=30.0,
    )
    return response.json()


async def handle_historical_country(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the disease-sh-historical-country tool call."""
    try:
        if not arguments or "country" not in arguments:
            raise ValueError("country is required")
        params = DiseaseShHistoricalCountryParams(**arguments)
        data = fetch_historical_country(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching disease.sh historical country: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="disease-sh-historical-country",
        description="Get historical COVID-19 data for a single country.",
        inputSchema=DiseaseShHistoricalCountryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["disease-sh-historical-country"] = handle_historical_country


###################
# Vaccine Coverage
###################


class DiseaseShVaccineCoverageParams(BaseModel):
    """Parameters for global vaccine coverage time-series."""

    lastdays: Optional[int] = Field(
        default=30,
        description="Number of days of vaccine coverage history to return",
    )


def fetch_vaccine_coverage(params: DiseaseShVaccineCoverageParams) -> dict:
    """Fetch global COVID-19 vaccine coverage time-series."""
    query_params: dict[str, Any] = {}
    if params.lastdays is not None:
        query_params["lastdays"] = params.lastdays

    # Per spec: use the vaccine/coverage endpoint under the same disease.sh host.
    response = http_get(
        "https://disease.sh/v3/covid-19/vaccine/coverage",
        params=query_params or None,
        timeout=30.0,
    )
    return response.json()


async def handle_vaccine_coverage(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the disease-sh-vaccine-coverage tool call."""
    try:
        params = DiseaseShVaccineCoverageParams(**(arguments or {}))
        data = fetch_vaccine_coverage(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching disease.sh vaccine coverage: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="disease-sh-vaccine-coverage",
        description="Get worldwide COVID-19 vaccine coverage time-series.",
        inputSchema=DiseaseShVaccineCoverageParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["disease-sh-vaccine-coverage"] = handle_vaccine_coverage


async def main():
    from mcp.server.stdio import stdio_server

    from opendata_mcp.utils import create_mcp_server

    server = create_mcp_server(
        "global-disease-sh", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
