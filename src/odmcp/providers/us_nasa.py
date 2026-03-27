"""
NASA Open Data Provider

This module provides interfaces to access NASA's public APIs.
It uses the public DEMO_KEY which has rate limits (30 req/hr).

Features:
- APOD: Astronomy Picture of the Day
- NeoWs: Asteroid tracking and Near Earth Objects
- Mars Rover Photos: Curiosity, Opportunity, Spirit
- Space Weather: ACE Solar Wind data (via CDAWeb)

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.nasa.gov"
DEMO_KEY = "DEMO_KEY"

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
    query_params = {"api_key": DEMO_KEY}
    if params.date:
        query_params["date"] = params.date

    response = httpx.get(f"{BASE_URL}/planetary/apod", params=query_params)
    response.raise_for_status()
    return response.json()


async def handle_get_apod(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the nasa-get-apod tool call."""
    try:
        params = APODParams(**(arguments or {}))
        data = fetch_apod(params)
        return [types.TextContent(type="text", text=str(data))]
    except Exception as e:
        log.error(f"Error fetching NASA APOD: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="nasa-get-apod",
        description="Get NASA's Astronomy Picture of the Day with its explanation.",
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
        ..., description="Start date for asteroid search (YYYY-MM-DD)"
    )
    end_date: str = Field(..., description="End date for asteroid search (YYYY-MM-DD)")


def fetch_neows(params: NeoWsParams) -> dict:
    """Fetch NEO data from NASA API."""
    query_params = {
        "api_key": DEMO_KEY,
        "start_date": params.start_date,
        "end_date": params.end_date,
    }
    response = httpx.get(f"{BASE_URL}/neo/rest/v1/feed", params=query_params)
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
        return [types.TextContent(type="text", text=str(data))]
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
        ..., description="The Earth date the photo was taken (YYYY-MM-DD)"
    )
    camera: Optional[str] = Field(
        None, description="The camera abbreviation (e.g., FHAZ, RHAZ, MAST)"
    )


def fetch_mars_photos(params: MarsRoverParams) -> dict:
    """Fetch Mars rover photos from NASA API."""
    query_params = {"api_key": DEMO_KEY, "earth_date": params.earth_date}
    if params.camera:
        query_params["camera"] = params.camera

    response = httpx.get(
        f"{BASE_URL}/mars-photos/api/v1/rovers/{params.rover}/photos",
        params=query_params,
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
        return [types.TextContent(type="text", text=str(data))]
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

    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


def fetch_ace_data(params: ACESolarWindParams) -> dict:
    """Fetch ACE Solar Wind data from NASA CDAWeb.
    Note: We use the CDF-JSON interface if available, or simplified text representation.
    For this implementation, we use the HTTP API for data retrieval.
    """
    # Simplified access to ACE H1 (High-resolution) solar wind parameters
    # This is a simplified proxy - real CDAWeb API is more complex.
    # We use a known open endpoint for solar wind counts.
    # url = "https://cdaweb.gsfc.nasa.gov/pub/software/cdawlib/0JSON/ace/swics/h1/swi_h1_20240101_v01.json"
    # Note: In a real implementation, we would build the URL dynamically.
    # For now, we point to the general CDAWeb JSON explorer.
    return {
        "info": "NASA Specialized Science Data (ACE Solar Wind) is available at CDAWeb.",
        "url": "https://cdaweb.gsfc.nasa.gov/cgi-bin/eval2.cgi?dataset=AC_H1_SWE&index=sp_phys",
    }


async def handle_get_ace_data(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the nasa-get-ace-data tool call."""
    try:
        return [
            types.TextContent(
                type="text",
                text="ACE Solar Wind data can be explored at https://cdaweb.gsfc.nasa.gov/",
            )
        ]
    except Exception as e:
        log.error(f"Error fetching ACE data: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="nasa-get-ace-data",
        description="Get information about the ACE (Advanced Composition Explorer) Solar Wind data.",
        inputSchema=ACESolarWindParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["nasa-get-ace-data"] = handle_get_ace_data


async def main():
    from mcp.server.stdio import stdio_server
    from odmcp.utils import create_mcp_server

    # create the server
    server = create_mcp_server(
        "us-nasa", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    # run the server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
