"""
OpenStreetMap Overpass API Provider

This module provides interfaces to the Overpass API, a read-only query
endpoint for OpenStreetMap (OSM) data. Overpass lets you select OSM
objects by tag, bounding box, area, or proximity using the OverpassQL
query language.

Source: https://overpass-api.de / https://wiki.openstreetmap.org/wiki/Overpass_API
License: OSM data is licensed under the Open Database License (ODbL). When
using results, attribute "(c) OpenStreetMap contributors". See
https://www.openstreetmap.org/copyright for full terms.

Fair-use notes:
- The public ``overpass-api.de`` endpoint is shared and enforces strict
  rate / load limits. Use sparingly. Prefer narrow queries (tag filters,
  bbox / radius bounds, modest output sizes).
- Long queries are common; this module caps the textual output returned
  to clients at ~20,000 characters.
- Use ``[out:json]`` in your OverpassQL queries to receive structured JSON.

Features:
- Raw OverpassQL query execution
- Helper for "amenity around lat/lon"
- Helper for "feature key=value inside bbox"
- Service status (plain text)

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
from typing import Any, List, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://overpass-api.de/api"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _run_overpass_query(query: str) -> Any:
    """Send an OverpassQL query string to the interpreter endpoint.

    Uses ``http_get`` with the query passed via the ``data`` query parameter
    (Overpass accepts both GET and POST). Returns the parsed JSON when the
    response content-type is JSON; otherwise returns the raw text.
    """
    response = http_get(
        f"{BASE_URL}/interpreter",
        params={"data": query},
        timeout=60.0,
        headers={"Accept": "*/*"},
    )
    content_type = (
        response.headers.get("content-type", "") if hasattr(response, "headers") else ""
    )
    if "json" in content_type.lower():
        return response.json()
    # Fall back to JSON parse if the body looks like JSON; otherwise return text.
    try:
        return response.json()
    except Exception:
        return response.text


###################
# Raw Query
###################


class OverpassQueryParams(BaseModel):
    """Parameters for executing a raw OverpassQL query."""

    query: str = Field(
        ...,
        min_length=1,
        description=(
            "Raw OverpassQL query string. Include '[out:json];' for JSON "
            'responses (e.g. \'[out:json];node["amenity"="cafe"]'
            "(around:500,52.52,13.41);out body;')."
        ),
    )


def fetch_query(params: OverpassQueryParams) -> Any:
    """Execute a raw OverpassQL query."""
    return _run_overpass_query(params.query)


async def handle_query(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the overpass-query tool call."""
    try:
        if not arguments or "query" not in arguments:
            raise ValueError("query is required")
        params = OverpassQueryParams(**arguments)
        data = fetch_query(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error running Overpass query: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="overpass-query",
        description=(
            "Execute a raw OverpassQL query against the Overpass API. "
            "Prefix with '[out:json];' for structured JSON output. "
            "Use sparingly: the public endpoint has rate / load limits."
        ),
        inputSchema=OverpassQueryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["overpass-query"] = handle_query


###################
# Status
###################


class OverpassStatusParams(BaseModel):
    """Parameters for the Overpass status endpoint."""

    pass


def fetch_status(_params: OverpassStatusParams) -> str:
    """Fetch the Overpass service status (plain text)."""
    response = http_get(
        f"{BASE_URL}/status",
        timeout=30.0,
        headers={"Accept": "*/*"},
    )
    return response.text


async def handle_status(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the overpass-status tool call."""
    try:
        params = OverpassStatusParams(**(arguments or {}))
        data = fetch_status(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Overpass status: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="overpass-status",
        description="Get the Overpass API service status (plain text).",
        inputSchema=OverpassStatusParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["overpass-status"] = handle_status


###################
# Around Amenity (helper)
###################


class OverpassAroundAmenityParams(BaseModel):
    """Parameters for an 'amenity around lat/lon' Overpass helper."""

    amenity: str = Field(..., description="OSM amenity value, e.g. 'cafe', 'hospital'")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Center latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Center longitude")
    radius: int = Field(default=500, ge=1, description="Search radius in meters")


def fetch_around_amenity(params: OverpassAroundAmenityParams) -> Any:
    """Find nodes tagged amenity={amenity} within radius (meters) of lat/lon."""
    query = (
        f"[out:json];"
        f'node["amenity"="{params.amenity}"]'
        f"(around:{params.radius},{params.lat},{params.lon});"
        f"out body;"
    )
    return _run_overpass_query(query)


async def handle_around_amenity(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the overpass-around-amenity tool call."""
    try:
        if (
            not arguments
            or "amenity" not in arguments
            or "lat" not in arguments
            or "lon" not in arguments
        ):
            raise ValueError("amenity, lat, and lon are required")
        params = OverpassAroundAmenityParams(**arguments)
        data = fetch_around_amenity(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error running Overpass around-amenity query: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="overpass-around-amenity",
        description=(
            "Find OSM nodes tagged with a given amenity within a radius (m) "
            "around a lat/lon point."
        ),
        inputSchema=OverpassAroundAmenityParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["overpass-around-amenity"] = handle_around_amenity


###################
# BBox Feature (helper)
###################


class OverpassBboxFeatureParams(BaseModel):
    """Parameters for a key/value tag query inside a bounding box."""

    key: str = Field(..., description="OSM tag key (e.g. 'highway', 'amenity')")
    value: str = Field(..., description="OSM tag value (e.g. 'primary', 'restaurant')")
    s: float = Field(..., ge=-90.0, le=90.0, description="South latitude")
    w: float = Field(..., ge=-180.0, le=180.0, description="West longitude")
    n: float = Field(..., ge=-90.0, le=90.0, description="North latitude")
    e: float = Field(..., ge=-180.0, le=180.0, description="East longitude")


def fetch_bbox_feature(params: OverpassBboxFeatureParams) -> Any:
    """Find nodes and ways with key=value inside bbox (s,w,n,e)."""
    # Build a query for both nodes and ways with the given key=value.
    query = (
        f"[out:json];"
        f"("
        f'node["{params.key}"="{params.value}"]({params.s},{params.w},{params.n},{params.e});'
        f'way["{params.key}"="{params.value}"]({params.s},{params.w},{params.n},{params.e});'
        f");"
        f"out body;"
    )
    return _run_overpass_query(query)


async def handle_bbox_feature(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the overpass-bbox-feature tool call."""
    try:
        if (
            not arguments
            or "key" not in arguments
            or "value" not in arguments
            or "s" not in arguments
            or "w" not in arguments
            or "n" not in arguments
            or "e" not in arguments
        ):
            raise ValueError("key, value, s, w, n, and e are required")
        params = OverpassBboxFeatureParams(**arguments)
        data = fetch_bbox_feature(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error running Overpass bbox-feature query: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="overpass-bbox-feature",
        description=(
            "Find OSM nodes and ways tagged with a given key=value inside a "
            "bounding box (south, west, north, east)."
        ),
        inputSchema=OverpassBboxFeatureParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["overpass-bbox-feature"] = handle_bbox_feature


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-overpass", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
