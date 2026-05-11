"""
Deutsche Bahn (DB) Open Data Provider

This module provides interfaces to access Deutsche Bahn's public APIs.
It focuses on station data (StaDa) and timetable information.

Features:
- Station discovery (search by name/ID)
- Timetable: Arrivals and Departures for a specific station

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import to_json_text

# Initialize logging
log = logging.getLogger(__name__)

# Constants
# We use the public-transport-rest standard for DB data (key-less).
BASE_URL = "https://v6.db.transport.rest"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# Station Discovery
###################


class DBStationParams(BaseModel):
    """Parameters for searching Deutsche Bahn stations."""

    search: str = Field(
        ..., description="Search term for the station name (e.g., 'Berlin')"
    )


def fetch_db_stations(params: DBStationParams) -> list:
    """Fetch live station data from the public DB transport API wrapper."""
    url = f"{BASE_URL}/locations"
    query_params = {"query": params.search, "results": 5}
    response = httpx.get(url, params=query_params, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def handle_list_stations(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the db-list-stations tool call."""
    try:
        if not arguments or "search" not in arguments:
            raise ValueError("search term is required")
        params = DBStationParams(**arguments)
        data = fetch_db_stations(params)
        return [types.TextContent(type="text", text=to_json_text(data))]
    except Exception as e:
        log.error(f"Error listing DB stations: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="db-list-stations",
        description="Search for stations in the Deutsche Bahn rail network (live data).",
        inputSchema=DBStationParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["db-list-stations"] = handle_list_stations

###################
# Timetables
###################


class DBTimetableParams(BaseModel):
    """Parameters for getting station timetables."""

    station_id: str = Field(
        ..., description="The EVA ID of the station (e.g., '8011160' for Berlin Hbf)"
    )
    mode: str = Field(
        "departures", description="Whether to fetch 'departures' or 'arrivals'"
    )
    duration: int = Field(15, description="Duration in minutes to fetch (default 15)")


def fetch_db_timetable(params: DBTimetableParams) -> list:
    """Fetch live departure/arrival data from the public DB transport API wrapper."""
    endpoint = f"{BASE_URL}/stops/{params.station_id}/{params.mode}"
    query_params = {"duration": params.duration}
    response = httpx.get(endpoint, params=query_params, timeout=10.0)
    response.raise_for_status()
    # If the response is a dict containing the list, extract it. The v6 API usually returns a list or a list inside an object.
    data = response.json()
    if isinstance(data, dict):
        # Handle cases where it might be wrapped (e.g. {"departures": [...]})
        return data.get(params.mode, [])
    return data


async def handle_get_timetable(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the db-get-timetable tool call."""
    try:
        if not arguments or "station_id" not in arguments:
            raise ValueError("station_id is required")
        params = DBTimetableParams(**arguments)
        data = fetch_db_timetable(params)

        # Summarize to keep it concise for LLM
        summary = []
        for entry in data[:10]:  # Limit to 10 entries
            trip = entry.get("tripId", "N/A")
            direction = entry.get("direction", "N/A")
            planned_time = entry.get("plannedWhen")
            actual_time = entry.get("when")
            line = entry.get("line", {}).get("name", "N/A")
            summary.append(
                {
                    "line": line,
                    "direction": direction,
                    "planned": planned_time,
                    "actual": actual_time,
                    "tripId": trip,
                }
            )

        return [types.TextContent(type="text", text=to_json_text(summary))]
    except Exception as e:
        log.error(f"Error fetching DB timetable: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="db-get-timetable",
        description="Get live departures or arrivals for a specific station EVA ID.",
        inputSchema=DBTimetableParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["db-get-timetable"] = handle_get_timetable


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "de-db", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
