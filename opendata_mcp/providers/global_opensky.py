"""
OpenSky Network Flight Tracking Provider

This module provides interfaces to the OpenSky Network REST API, which
exposes live and historical ADS-B flight tracking data for aircraft
worldwide.

License: OpenSky data is available for non-commercial research and
educational use under the OpenSky Network Terms of Use. See
https://opensky-network.org/about/terms-of-use for full details.

Environment variables:
- None required for anonymous access. Anonymous users get reduced rate
  limits.

Features:
- Live state vectors for all aircraft (optionally bounded by a bbox)
- State vector lookup for a specific aircraft
- Historical flight intervals per aircraft
- Airport arrival and departure logs

Notes:
- All time parameters are Unix epoch seconds.
- The API is heavily rate-limited; back off aggressively on 429.

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://opensky-network.org/api"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# States All
###################


class OpenSkyStatesAllParams(BaseModel):
    """Parameters for fetching all live aircraft state vectors."""

    lamin: Optional[float] = Field(
        None, description="Lower-bound latitude of bounding box (WGS84)"
    )
    lomin: Optional[float] = Field(
        None, description="Lower-bound longitude of bounding box (WGS84)"
    )
    lamax: Optional[float] = Field(
        None, description="Upper-bound latitude of bounding box (WGS84)"
    )
    lomax: Optional[float] = Field(
        None, description="Upper-bound longitude of bounding box (WGS84)"
    )
    time: Optional[int] = Field(
        None,
        description="Unix epoch seconds; omit for the latest snapshot",
    )


def fetch_states_all(params: OpenSkyStatesAllParams) -> dict:
    """Fetch all live aircraft state vectors from OpenSky."""
    query_params: dict[str, Any] = {}
    if params.lamin is not None:
        query_params["lamin"] = params.lamin
    if params.lomin is not None:
        query_params["lomin"] = params.lomin
    if params.lamax is not None:
        query_params["lamax"] = params.lamax
    if params.lomax is not None:
        query_params["lomax"] = params.lomax
    if params.time is not None:
        query_params["time"] = params.time

    response = http_get(f"{BASE_URL}/states/all", params=query_params, timeout=30.0)
    return response.json()


async def handle_get_states_all(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opensky-get-states-all tool call."""
    try:
        params = OpenSkyStatesAllParams(**(arguments or {}))
        data = fetch_states_all(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OpenSky all states: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opensky-get-states-all",
        description="Fetch live ADS-B state vectors for all aircraft (optionally within a bounding box).",
        inputSchema=OpenSkyStatesAllParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opensky-get-states-all"] = handle_get_states_all


###################
# States By Aircraft
###################


class OpenSkyStatesByAircraftParams(BaseModel):
    """Parameters for fetching state vectors for a specific aircraft."""

    icao24: str = Field(..., description="Lowercase ICAO24 transponder address")
    time: Optional[int] = Field(
        None,
        description="Unix epoch seconds; omit for the latest snapshot",
    )


def fetch_states_by_aircraft(params: OpenSkyStatesByAircraftParams) -> dict:
    """Fetch state vectors for a specific aircraft."""
    query_params: dict[str, Any] = {"icao24": params.icao24}
    if params.time is not None:
        query_params["time"] = params.time

    response = http_get(f"{BASE_URL}/states/all", params=query_params, timeout=30.0)
    return response.json()


async def handle_get_states_by_aircraft(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opensky-get-states-by-aircraft tool call."""
    try:
        if not arguments or "icao24" not in arguments:
            raise ValueError("icao24 is required")
        params = OpenSkyStatesByAircraftParams(**arguments)
        data = fetch_states_by_aircraft(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OpenSky states by aircraft: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opensky-get-states-by-aircraft",
        description="Fetch state vectors for a specific ICAO24 aircraft.",
        inputSchema=OpenSkyStatesByAircraftParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opensky-get-states-by-aircraft"] = handle_get_states_by_aircraft


###################
# Flights By Aircraft
###################


class OpenSkyFlightsAircraftParams(BaseModel):
    """Parameters for fetching historical flights for a specific aircraft."""

    icao24: str = Field(..., description="Lowercase ICAO24 transponder address")
    begin: int = Field(..., description="Unix epoch seconds (inclusive)")
    end: int = Field(..., description="Unix epoch seconds (exclusive)")


def fetch_flights_aircraft(params: OpenSkyFlightsAircraftParams) -> list:
    """Fetch historical flights for a specific aircraft."""
    query_params = {
        "icao24": params.icao24,
        "begin": params.begin,
        "end": params.end,
    }
    response = http_get(
        f"{BASE_URL}/flights/aircraft", params=query_params, timeout=30.0
    )
    return response.json()


async def handle_get_flights_aircraft(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opensky-get-flights-aircraft tool call."""
    try:
        if (
            not arguments
            or "icao24" not in arguments
            or "begin" not in arguments
            or "end" not in arguments
        ):
            raise ValueError("icao24, begin, and end are required")
        params = OpenSkyFlightsAircraftParams(**arguments)
        data = fetch_flights_aircraft(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OpenSky flights for aircraft: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opensky-get-flights-aircraft",
        description="Fetch historical flights for a specific ICAO24 aircraft within a time interval.",
        inputSchema=OpenSkyFlightsAircraftParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opensky-get-flights-aircraft"] = handle_get_flights_aircraft


###################
# Flights Arrival
###################


class OpenSkyFlightsArrivalParams(BaseModel):
    """Parameters for fetching arrivals at an airport."""

    airport: str = Field(..., description="ICAO airport code (e.g. 'EDDF')")
    begin: int = Field(..., description="Unix epoch seconds (inclusive)")
    end: int = Field(..., description="Unix epoch seconds (exclusive)")


def fetch_flights_arrival(params: OpenSkyFlightsArrivalParams) -> list:
    """Fetch arrivals at a specific airport in a time interval."""
    query_params = {
        "airport": params.airport,
        "begin": params.begin,
        "end": params.end,
    }
    response = http_get(
        f"{BASE_URL}/flights/arrival", params=query_params, timeout=30.0
    )
    return response.json()


async def handle_get_flights_arrival(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opensky-get-flights-arrival tool call."""
    try:
        if (
            not arguments
            or "airport" not in arguments
            or "begin" not in arguments
            or "end" not in arguments
        ):
            raise ValueError("airport, begin, and end are required")
        params = OpenSkyFlightsArrivalParams(**arguments)
        data = fetch_flights_arrival(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OpenSky arrivals: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opensky-get-flights-arrival",
        description="Fetch arrivals at an ICAO airport within a time interval.",
        inputSchema=OpenSkyFlightsArrivalParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opensky-get-flights-arrival"] = handle_get_flights_arrival


###################
# Flights Departure
###################


class OpenSkyFlightsDepartureParams(BaseModel):
    """Parameters for fetching departures from an airport."""

    airport: str = Field(..., description="ICAO airport code (e.g. 'EDDF')")
    begin: int = Field(..., description="Unix epoch seconds (inclusive)")
    end: int = Field(..., description="Unix epoch seconds (exclusive)")


def fetch_flights_departure(params: OpenSkyFlightsDepartureParams) -> list:
    """Fetch departures from a specific airport in a time interval."""
    query_params = {
        "airport": params.airport,
        "begin": params.begin,
        "end": params.end,
    }
    response = http_get(
        f"{BASE_URL}/flights/departure", params=query_params, timeout=30.0
    )
    return response.json()


async def handle_get_flights_departure(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opensky-get-flights-departure tool call."""
    try:
        if (
            not arguments
            or "airport" not in arguments
            or "begin" not in arguments
            or "end" not in arguments
        ):
            raise ValueError("airport, begin, and end are required")
        params = OpenSkyFlightsDepartureParams(**arguments)
        data = fetch_flights_departure(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OpenSky departures: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opensky-get-flights-departure",
        description="Fetch departures from an ICAO airport within a time interval.",
        inputSchema=OpenSkyFlightsDepartureParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opensky-get-flights-departure"] = handle_get_flights_departure


async def main():
    from mcp.server.stdio import stdio_server

    from opendata_mcp.utils import create_mcp_server

    server = create_mcp_server(
        "global-opensky", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
