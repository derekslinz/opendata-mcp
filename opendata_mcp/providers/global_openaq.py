"""
OpenAQ Global Air Quality Provider

This module provides interfaces to the OpenAQ v3 API, exposing global air
quality measurements from thousands of monitoring stations worldwide.

License: OpenAQ data is published under CC BY 4.0. See
https://docs.openaq.org/about/about for full license terms.

Environment variables:
- OPENAQ_API_KEY (REQUIRED): The OpenAQ API key. Handlers raise
  ValueError if this is not set. Register for a free key at
  https://explore.openaq.org/register.

Features:
- Parameters catalogue (PM2.5, NO2, O3, CO, SO2, BC, etc.)
- Countries list
- Locations search (by country, parameter, paginated)
- Location detail and latest readings
- Per-location sensor enumeration

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
BASE_URL = "https://api.openaq.org/v3"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _auth_headers() -> dict[str, str]:
    """Return the X-API-Key header for OpenAQ requests.

    Raises:
        ValueError: If OPENAQ_API_KEY is not set in the environment.
    """
    key = os.getenv("OPENAQ_API_KEY")
    if not key:
        raise ValueError(
            "OPENAQ_API_KEY environment variable is required for OpenAQ tools. "
            "Register at https://explore.openaq.org/register to obtain one."
        )
    return {"X-API-Key": key}


###################
# List Parameters
###################


class OpenAQListParametersParams(BaseModel):
    """Parameters for listing OpenAQ measurement parameters."""

    limit: int = Field(default=100, description="Number of results to return")
    page: int = Field(default=1, description="Page number (1-indexed)")


def fetch_list_parameters(params: OpenAQListParametersParams) -> dict:
    """Fetch the catalogue of OpenAQ measurement parameters."""
    query_params = {"limit": params.limit, "page": params.page}
    response = http_get(
        f"{BASE_URL}/parameters",
        params=query_params,
        headers=_auth_headers(),
    )
    return response.json()


async def handle_list_parameters(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openaq-list-parameters tool call."""
    try:
        params = OpenAQListParametersParams(**(arguments or {}))
        data = fetch_list_parameters(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching OpenAQ parameters: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openaq-list-parameters",
        description="List OpenAQ measurement parameters (PM2.5, NO2, O3, CO, SO2, BC, etc.).",
        inputSchema=OpenAQListParametersParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openaq-list-parameters"] = handle_list_parameters


###################
# List Locations
###################


class OpenAQListLocationsParams(BaseModel):
    """Parameters for searching OpenAQ monitoring locations."""

    country: Optional[str] = Field(
        None, description="Country code (e.g. 'US') or country id"
    )
    parameters_id: Optional[int] = Field(
        None, description="Restrict to a specific parameter id"
    )
    limit: int = Field(default=100, description="Number of locations to return")
    page: int = Field(default=1, description="Page number (1-indexed)")


def fetch_list_locations(params: OpenAQListLocationsParams) -> dict:
    """Search OpenAQ monitoring locations."""
    query_params: dict[str, Any] = {"limit": params.limit, "page": params.page}
    if params.country:
        query_params["country"] = params.country
    if params.parameters_id is not None:
        query_params["parameters_id"] = params.parameters_id

    response = http_get(
        f"{BASE_URL}/locations",
        params=query_params,
        headers=_auth_headers(),
    )
    return response.json()


async def handle_list_locations(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openaq-list-locations tool call."""
    try:
        params = OpenAQListLocationsParams(**(arguments or {}))
        data = fetch_list_locations(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching OpenAQ locations: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openaq-list-locations",
        description="Search OpenAQ monitoring locations by country and/or parameter.",
        inputSchema=OpenAQListLocationsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openaq-list-locations"] = handle_list_locations


###################
# Get Location
###################


class OpenAQGetLocationParams(BaseModel):
    """Parameters for fetching a single OpenAQ location."""

    locations_id: int = Field(..., description="The OpenAQ numeric location id")


def fetch_get_location(params: OpenAQGetLocationParams) -> dict:
    """Fetch metadata for a specific OpenAQ location."""
    response = http_get(
        f"{BASE_URL}/locations/{params.locations_id}",
        headers=_auth_headers(),
    )
    return response.json()


async def handle_get_location(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openaq-get-location tool call."""
    try:
        if not arguments or "locations_id" not in arguments:
            raise ValueError("locations_id is required")
        params = OpenAQGetLocationParams(**arguments)
        data = fetch_get_location(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching OpenAQ location: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openaq-get-location",
        description="Fetch full metadata for a specific OpenAQ monitoring location.",
        inputSchema=OpenAQGetLocationParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openaq-get-location"] = handle_get_location


###################
# Get Latest
###################


class OpenAQGetLatestParams(BaseModel):
    """Parameters for fetching latest readings at an OpenAQ location."""

    locations_id: int = Field(..., description="The OpenAQ numeric location id")


def fetch_get_latest(params: OpenAQGetLatestParams) -> dict:
    """Fetch the latest measurements for an OpenAQ location."""
    response = http_get(
        f"{BASE_URL}/locations/{params.locations_id}/latest",
        headers=_auth_headers(),
    )
    return response.json()


async def handle_get_latest(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openaq-get-latest tool call."""
    try:
        if not arguments or "locations_id" not in arguments:
            raise ValueError("locations_id is required")
        params = OpenAQGetLatestParams(**arguments)
        data = fetch_get_latest(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching OpenAQ latest measurements: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openaq-get-latest",
        description="Fetch the latest air quality readings for a specific OpenAQ location.",
        inputSchema=OpenAQGetLatestParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openaq-get-latest"] = handle_get_latest


###################
# List Countries
###################


class OpenAQListCountriesParams(BaseModel):
    """Parameters for listing OpenAQ countries."""

    limit: int = Field(default=200, description="Number of countries to return")


def fetch_list_countries(params: OpenAQListCountriesParams) -> dict:
    """Fetch the list of countries covered by OpenAQ."""
    query_params = {"limit": params.limit}
    response = http_get(
        f"{BASE_URL}/countries",
        params=query_params,
        headers=_auth_headers(),
    )
    return response.json()


async def handle_list_countries(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openaq-list-countries tool call."""
    try:
        params = OpenAQListCountriesParams(**(arguments or {}))
        data = fetch_list_countries(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching OpenAQ countries: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openaq-list-countries",
        description="List countries with OpenAQ air quality coverage.",
        inputSchema=OpenAQListCountriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openaq-list-countries"] = handle_list_countries


###################
# List Sensors
###################


class OpenAQListSensorsParams(BaseModel):
    """Parameters for listing sensors attached to an OpenAQ location."""

    locations_id: int = Field(..., description="The OpenAQ numeric location id")


def fetch_list_sensors(params: OpenAQListSensorsParams) -> dict:
    """Fetch the sensors at a given OpenAQ location."""
    response = http_get(
        f"{BASE_URL}/locations/{params.locations_id}/sensors",
        headers=_auth_headers(),
    )
    return response.json()


async def handle_list_sensors(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openaq-list-sensors tool call."""
    try:
        if not arguments or "locations_id" not in arguments:
            raise ValueError("locations_id is required")
        params = OpenAQListSensorsParams(**arguments)
        data = fetch_list_sensors(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching OpenAQ sensors: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openaq-list-sensors",
        description="List sensors attached to a specific OpenAQ monitoring location.",
        inputSchema=OpenAQListSensorsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openaq-list-sensors"] = handle_list_sensors


async def main(transport: str = "stdio", port: int = 8000):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-openaq", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
