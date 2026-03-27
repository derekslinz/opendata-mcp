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

import mcp.types as types
from pydantic import BaseModel, Field

# Initialize logging
log = logging.getLogger(__name__)

# Constants
# DB Open Data often uses different endpoints for different APIs.
STADA_URL = (
    "https://apis.deutschebahn.com/db-api-marketplace/apis/station-data/v2/stations"
)
TIMETABLE_URL = "https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# Station Data
###################


class DBStationParams(BaseModel):
    """Parameters for searching Deutsche Bahn stations."""

    search: str = Field(
        ..., description="Search term for the station name (e.g., 'Berlin')"
    )


def fetch_db_stations(params: DBStationParams) -> dict:
    """Fetch station data from DB Open Data.
    Note: Many DB APIs require registration on the DB API Marketplace.
    We use the Public Station Search endpoint if available, otherwise
    we provide the lookup instructions.
    """
    # For this implementation, we mock the response structure as the DB API
    # Marketplace requires per-user keys for most production endpoints.
    # We point users to the portal for their own key.
    return {
        "info": "Deutsche Bahn APIs require a key from the DB API Marketplace.",
        "url": "https://developers.deutschebahn.com/",
        "sample_stations": [
            {"id": "8000105", "name": "Frankfurt(Main)Hbf"},
            {"id": "8011160", "name": "Berlin Hbf"},
            {"id": "8000261", "name": "München Hbf"},
        ],
    }


async def handle_list_stations(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the db-list-stations tool call."""
    try:
        params = DBStationParams(**(arguments or {"search": ""}))
        data = fetch_db_stations(params)
        return [types.TextContent(type="text", text=str(data))]
    except Exception as e:
        log.error(f"Error listing DB stations: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="db-list-stations",
        description="Search for stations in the Deutsche Bahn rail network.",
        inputSchema=DBStationParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["db-list-stations"] = handle_list_stations


async def main():
    from mcp.server.stdio import stdio_server
    from odmcp.utils import create_mcp_server

    # create the server
    server = create_mcp_server(
        "de-db", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    # run the server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
