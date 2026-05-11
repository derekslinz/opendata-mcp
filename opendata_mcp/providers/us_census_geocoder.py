"""
US Census Bureau Geocoding Services Provider

This module exposes the US Census Bureau's public Geocoding Services API,
a keyless web service that converts street addresses to geographic coordinates
and returns Census geography (state, county, tract, block) for any point.

License note:
    Data and metadata returned by the Census Geocoder are public domain
    (US Government work). Consult the Census Bureau's terms of use for
    redistribution rules.

Features:
- Forward geocode a free-form ("one-line") address to coordinates
- Forward geocode a structured (street/city/state/zip) address
- Reverse geocode coordinates to Census geographies
- Address-to-geographies (returns coords + Census tract/block)
- List available benchmarks (Public_AR_Current, Public_AR_Census2020, etc.)
- List vintages valid for a given benchmark

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://geocoding.geo.census.gov/geocoder"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Oneline address geocoding (locations)
###################


class CensusGeocodeOnelineParams(BaseModel):
    """Parameters for one-line address forward geocoding."""

    address: str = Field(
        ...,
        description="Free-form (one-line) street address to geocode, e.g. '1600 Pennsylvania Ave NW, Washington DC 20500'.",
    )
    benchmark: str = Field(
        default="Public_AR_Current",
        description="Census Geocoder benchmark name (e.g. Public_AR_Current, Public_AR_Census2020).",
    )


def fetch_census_geocode_oneline(params: CensusGeocodeOnelineParams) -> dict:
    """Call /locations/onelineaddress on the Census Geocoder."""
    query_params: dict[str, Any] = {
        "address": params.address,
        "benchmark": params.benchmark,
        "format": "json",
    }
    response = http_get(f"{BASE_URL}/locations/onelineaddress", params=query_params)
    return response.json()


async def handle_census_geocode_oneline(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the census-geocode-oneline tool call."""
    try:
        if not arguments or "address" not in arguments:
            raise ValueError("address is required")
        params = CensusGeocodeOnelineParams(**arguments)
        data = fetch_census_geocode_oneline(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error geocoding one-line address via Census: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="census-geocode-oneline",
        description="Forward-geocode a free-form (one-line) US address using the Census Geocoder.",
        inputSchema=CensusGeocodeOnelineParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["census-geocode-oneline"] = handle_census_geocode_oneline


###################
# Structured address geocoding (locations)
###################


class CensusGeocodeAddressParams(BaseModel):
    """Parameters for structured address forward geocoding."""

    street: str = Field(
        ..., description="Street number and name, e.g. '1600 Pennsylvania Ave NW'."
    )
    city: Optional[str] = Field(None, description="City name, e.g. 'Washington'.")
    state: Optional[str] = Field(
        None, description="USPS state abbreviation, e.g. 'DC'."
    )
    zip: Optional[str] = Field(None, description="ZIP or ZIP+4 code.")
    benchmark: str = Field(
        default="Public_AR_Current",
        description="Census Geocoder benchmark name.",
    )


def fetch_census_geocode_address(params: CensusGeocodeAddressParams) -> dict:
    """Call /locations/address on the Census Geocoder."""
    query_params: dict[str, Any] = {
        "street": params.street,
        "benchmark": params.benchmark,
        "format": "json",
    }
    if params.city:
        query_params["city"] = params.city
    if params.state:
        query_params["state"] = params.state
    if params.zip:
        query_params["zip"] = params.zip
    response = http_get(f"{BASE_URL}/locations/address", params=query_params)
    return response.json()


async def handle_census_geocode_address(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the census-geocode-address tool call."""
    try:
        if not arguments or "street" not in arguments:
            raise ValueError("street is required")
        params = CensusGeocodeAddressParams(**arguments)
        data = fetch_census_geocode_address(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error geocoding structured address via Census: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="census-geocode-address",
        description="Forward-geocode a structured US address (street/city/state/zip) using the Census Geocoder.",
        inputSchema=CensusGeocodeAddressParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["census-geocode-address"] = handle_census_geocode_address


###################
# Reverse geocoding by coordinates (geographies)
###################


class CensusGeocodeCoordinatesParams(BaseModel):
    """Parameters for reverse geocoding from coordinates."""

    x: float = Field(..., description="Longitude (x), WGS84 decimal degrees.")
    y: float = Field(..., description="Latitude (y), WGS84 decimal degrees.")
    benchmark: str = Field(
        default="Public_AR_Current",
        description="Census Geocoder benchmark name.",
    )
    vintage: str = Field(
        default="Current_Current",
        description="Census geography vintage compatible with the benchmark (e.g. Current_Current).",
    )


def fetch_census_geocode_coordinates(params: CensusGeocodeCoordinatesParams) -> dict:
    """Call /geographies/coordinates on the Census Geocoder."""
    query_params: dict[str, Any] = {
        "x": params.x,
        "y": params.y,
        "benchmark": params.benchmark,
        "vintage": params.vintage,
        "format": "json",
    }
    response = http_get(f"{BASE_URL}/geographies/coordinates", params=query_params)
    return response.json()


async def handle_census_geocode_coordinates(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the census-geocode-coordinates tool call."""
    try:
        if not arguments or "x" not in arguments or "y" not in arguments:
            raise ValueError("x and y are required")
        params = CensusGeocodeCoordinatesParams(**arguments)
        data = fetch_census_geocode_coordinates(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error reverse-geocoding coordinates via Census: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="census-geocode-coordinates",
        description="Reverse-geocode an (x=longitude, y=latitude) pair to Census geographies (state/county/tract/block).",
        inputSchema=CensusGeocodeCoordinatesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["census-geocode-coordinates"] = handle_census_geocode_coordinates


###################
# Oneline address -> geographies
###################


class CensusGeocodeOnelineGeoParams(BaseModel):
    """Parameters for one-line address geocoding with geographies output."""

    address: str = Field(..., description="Free-form (one-line) US street address.")
    benchmark: str = Field(
        default="Public_AR_Current", description="Census Geocoder benchmark."
    )
    vintage: str = Field(
        default="Current_Current",
        description="Census geography vintage compatible with the benchmark.",
    )


def fetch_census_geocode_oneline_geographies(
    params: CensusGeocodeOnelineGeoParams,
) -> dict:
    """Call /geographies/onelineaddress on the Census Geocoder."""
    query_params: dict[str, Any] = {
        "address": params.address,
        "benchmark": params.benchmark,
        "vintage": params.vintage,
        "format": "json",
    }
    response = http_get(f"{BASE_URL}/geographies/onelineaddress", params=query_params)
    return response.json()


async def handle_census_geocode_oneline_geographies(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the census-geocode-onelineaddress-geographies tool call."""
    try:
        if not arguments or "address" not in arguments:
            raise ValueError("address is required")
        params = CensusGeocodeOnelineGeoParams(**arguments)
        data = fetch_census_geocode_oneline_geographies(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error geocoding one-line address with geographies via Census: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="census-geocode-onelineaddress-geographies",
        description="Forward-geocode a one-line US address and return coordinates plus Census geographies.",
        inputSchema=CensusGeocodeOnelineGeoParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["census-geocode-onelineaddress-geographies"] = (
    handle_census_geocode_oneline_geographies
)


###################
# Structured address -> geographies
###################


class CensusGeocodeAddressGeoParams(BaseModel):
    """Parameters for structured address geocoding with geographies output."""

    street: str = Field(..., description="Street number and name.")
    city: Optional[str] = Field(None, description="City name.")
    state: Optional[str] = Field(None, description="USPS state abbreviation.")
    zip: Optional[str] = Field(None, description="ZIP or ZIP+4 code.")
    benchmark: str = Field(
        default="Public_AR_Current", description="Census Geocoder benchmark."
    )
    vintage: str = Field(
        default="Current_Current",
        description="Census geography vintage compatible with the benchmark.",
    )


def fetch_census_geocode_address_geographies(
    params: CensusGeocodeAddressGeoParams,
) -> dict:
    """Call /geographies/address on the Census Geocoder."""
    query_params: dict[str, Any] = {
        "street": params.street,
        "benchmark": params.benchmark,
        "vintage": params.vintage,
        "format": "json",
    }
    if params.city:
        query_params["city"] = params.city
    if params.state:
        query_params["state"] = params.state
    if params.zip:
        query_params["zip"] = params.zip
    response = http_get(f"{BASE_URL}/geographies/address", params=query_params)
    return response.json()


async def handle_census_geocode_address_geographies(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the census-geocode-address-geographies tool call."""
    try:
        if not arguments or "street" not in arguments:
            raise ValueError("street is required")
        params = CensusGeocodeAddressGeoParams(**arguments)
        data = fetch_census_geocode_address_geographies(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(
            f"Error geocoding structured address with geographies via Census: {e}"
        )
        raise


TOOLS.append(
    types.Tool(
        name="census-geocode-address-geographies",
        description="Forward-geocode a structured US address and return coordinates plus Census geographies.",
        inputSchema=CensusGeocodeAddressGeoParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["census-geocode-address-geographies"] = (
    handle_census_geocode_address_geographies
)


###################
# Benchmarks list
###################


class CensusBenchmarksParams(BaseModel):
    """Parameters for listing Census Geocoder benchmarks."""


def fetch_census_benchmarks(params: CensusBenchmarksParams) -> dict:
    """Call /benchmarks on the Census Geocoder."""
    response = http_get(f"{BASE_URL}/benchmarks", params={"format": "json"})
    return response.json()


async def handle_census_benchmarks(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the census-geocode-benchmarks tool call."""
    try:
        params = CensusBenchmarksParams(**(arguments or {}))
        data = fetch_census_benchmarks(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing Census benchmarks: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="census-geocode-benchmarks",
        description="List available Census Geocoder benchmarks (e.g. Public_AR_Current).",
        inputSchema=CensusBenchmarksParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["census-geocode-benchmarks"] = handle_census_benchmarks


###################
# Vintages list
###################


class CensusVintagesParams(BaseModel):
    """Parameters for listing Census Geocoder vintages valid for a benchmark."""

    benchmark: str = Field(
        ...,
        description="Benchmark name to list compatible vintages for, e.g. Public_AR_Current.",
    )


def fetch_census_vintages(params: CensusVintagesParams) -> dict:
    """Call /vintages on the Census Geocoder for the given benchmark."""
    query_params: dict[str, Any] = {
        "benchmark": params.benchmark,
        "format": "json",
    }
    response = http_get(f"{BASE_URL}/vintages", params=query_params)
    return response.json()


async def handle_census_vintages(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the census-geocode-vintages tool call."""
    try:
        if not arguments or "benchmark" not in arguments:
            raise ValueError("benchmark is required")
        params = CensusVintagesParams(**arguments)
        data = fetch_census_vintages(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing Census vintages: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="census-geocode-vintages",
        description="List Census geography vintages valid for a given benchmark.",
        inputSchema=CensusVintagesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["census-geocode-vintages"] = handle_census_vintages


async def main(transport: str = "stdio", port: int = 8000):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "us-census-geocoder",
        RESOURCES,
        RESOURCES_HANDLERS,
        TOOLS,
        TOOLS_HANDLERS,
    )

    await run_server(server, transport, port)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
