"""
NASA Open Data Provider

This module provides interfaces to access NASA's public APIs.
It uses the public DEMO_KEY by default (30 req/hr limit). Set the
NASA_API_KEY environment variable to use a personal API key with
higher rate limits.

Features:
- APOD: Astronomy Picture of the Day
- NeoWs: Asteroid tracking and Near Earth Objects
- Mars Rover Photos: Curiosity, Opportunity, Spirit
- Space Weather: ACE Solar Wind data (via CDAWeb)

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
import os
from typing import Any, List, Optional, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import to_json_text

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.nasa.gov"
DEMO_KEY = "DEMO_KEY"
# Use NASA_API_KEY env var if set, otherwise fall back to the public DEMO_KEY
_API_KEY = os.getenv("NASA_API_KEY", DEMO_KEY)

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# APOD
###################


class APODParams(BaseModel):
    """Parameters for getting the Astronomy Picture of the Day."""

    date: Optional[str] = Field(
        None, description="The date of the APOD image (YYYY-MM-DD)"
    )


def fetch_apod(params: APODParams) -> dict:
    """Fetch APOD data from NASA API."""
    query_params = {"api_key": _API_KEY}
    if params.date:
        query_params["date"] = params.date

    response = httpx.get(
        f"{BASE_URL}/planetary/apod", params=query_params, timeout=10.0
    )
    response.raise_for_status()
    return response.json()


async def handle_get_apod(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the nasa-get-apod tool call."""
    try:
        params = APODParams(**(arguments or {}))
        data = fetch_apod(params)
        return [types.TextContent(type="text", text=to_json_text(data))]
    except Exception as e:
        log.error(f"Error fetching NASA APOD: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="nasa-get-apod",
        description="Get NASA's Astronomy Picture of the Day with its explanation. Uses DEMO_KEY (30 req/hr limit) unless NASA_API_KEY env var is set.",
        inputSchema=APODParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["nasa-get-apod"] = handle_get_apod

###################
# NeoWs (Asteroids)
###################


class NeoWsParams(BaseModel):
    """Parameters for getting Near Earth Objects."""

    start_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Start date for asteroid search (YYYY-MM-DD)",
    )
    end_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="End date for asteroid search (YYYY-MM-DD)",
    )


def fetch_neows(params: NeoWsParams) -> dict:
    """Fetch NEO data from NASA API."""
    query_params = {
        "api_key": _API_KEY,
        "start_date": params.start_date,
        "end_date": params.end_date,
    }
    response = httpx.get(
        f"{BASE_URL}/neo/rest/v1/feed", params=query_params, timeout=10.0
    )
    response.raise_for_status()
    return response.json()


async def handle_get_asteroids(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the nasa-get-asteroids tool call."""
    try:
        if not arguments or "start_date" not in arguments:
            raise ValueError("start_date is required")
        params = NeoWsParams(**arguments)
        data = fetch_neows(params)
        return [types.TextContent(type="text", text=to_json_text(data))]
    except Exception as e:
        log.error(f"Error fetching NASA Asteroids: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="nasa-get-asteroids",
        description="Search for Near Earth Objects (asteroids) within a date range.",
        inputSchema=NeoWsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["nasa-get-asteroids"] = handle_get_asteroids

###################
# Mars Rover Photos
###################


class MarsRoverParams(BaseModel):
    """Parameters for fetching Mars rover photos."""

    rover: str = Field(
        ..., description="The rover name (curiosity, opportunity, spirit)"
    )
    earth_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="The Earth date the photo was taken (YYYY-MM-DD)",
    )
    camera: Optional[str] = Field(
        None, description="The camera abbreviation (e.g., FHAZ, RHAZ, MAST)"
    )


def fetch_mars_photos(params: MarsRoverParams) -> dict:
    """Fetch Mars rover photos from NASA API."""
    query_params = {"api_key": _API_KEY, "earth_date": params.earth_date}
    if params.camera:
        query_params["camera"] = params.camera

    response = httpx.get(
        f"{BASE_URL}/mars-photos/api/v1/rovers/{params.rover}/photos",
        params=query_params,
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


async def handle_get_mars_photos(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the nasa-get-mars-photos tool call."""
    try:
        if not arguments or "rover" not in arguments:
            raise ValueError("rover is required")
        params = MarsRoverParams(**arguments)
        data = fetch_mars_photos(params)
        return [types.TextContent(type="text", text=to_json_text(data))]
    except Exception as e:
        log.error(f"Error fetching Mars photos: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="nasa-get-mars-photos",
        description="Get photos taken by NASA's Mars rovers (Curiosity, Opportunity, Spirit).",
        inputSchema=MarsRoverParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["nasa-get-mars-photos"] = handle_get_mars_photos

###################
# ACE Solar Wind
###################


class ACESolarWindParams(BaseModel):
    """Parameters for fetching ACE Solar Wind data."""

    start_date: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date (YYYY-MM-DD)"
    )
    end_date: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date (YYYY-MM-DD)"
    )


def fetch_ace_data(params: ACESolarWindParams) -> list:
    """Fetch ACE/DSCOVR Solar Wind data from NOAA SWPC.
    Note: Real-time API only provides the last 7 days of data.
    """
    url = "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json"
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()
    data = response.json()

    if not data or len(data) < 2:
        return []

    headers = data[0]
    results = []

    start_str = params.start_date
    end_str = params.end_date

    for row in data[1:]:
        time_tag = row[0]
        # time_tag format is "YYYY-MM-DD HH:MM:SS.SSS"
        if time_tag:
            date_part = time_tag.split(" ")[0]
            if start_str <= date_part <= end_str:
                results.append(dict(zip(headers, row)))

    return results


async def handle_get_ace_data(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the nasa-get-ace-data tool call."""
    try:
        if (
            not arguments
            or "start_date" not in arguments
            or "end_date" not in arguments
        ):
            raise ValueError("start_date and end_date are required")
        params = ACESolarWindParams(**arguments)
        data = fetch_ace_data(params)

        if not data:
            return [
                types.TextContent(
                    type="text",
                    text="No data found for the requested date range. Note: Only the last 7 days of data are available from the real-time NOAA Space Weather API.",
                )
            ]

        return [types.TextContent(type="text", text=to_json_text(data))]
    except Exception as e:
        log.error(f"Error fetching ACE data: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="nasa-get-ace-data",
        description="Get Solar Wind plasma data from NOAA Space Weather (last 7 days only). Dates outside that window return no results.",
        inputSchema=ACESolarWindParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["nasa-get-ace-data"] = handle_get_ace_data


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "us-nasa", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
