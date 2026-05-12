"""
Cloudflare Radar Provider

This module exposes Cloudflare Radar's public API, which provides real-time
and historical data on Internet traffic, BGP routing events (hijacks, leaks),
Internet quality, and global connectivity trends.

License / source:
    Data is provided by Cloudflare under the CC BY-NC 4.0 license.
    Consult https://developers.cloudflare.com/radar/ for documentation.

Authentication:
    A free Cloudflare API token with Radar:Read permission is required.
    Create one at https://dash.cloudflare.com/profile/api-tokens and set the
    ``CLOUDFLARE_API_TOKEN`` environment variable. Without a token all requests
    will fail with a 403 error.

Features:
- BGP statistics time series
- BGP hijack events
- BGP route leak events
- Real-time BGP routes for a prefix
- Internet Quality Index summary

Usage:
    The module can be run directly to start an MCP server, or its components
    can be imported individually.
"""

import logging
import os
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

log = logging.getLogger(__name__)

BASE_URL = "https://api.cloudflare.com/client/v4/radar"

RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _auth_headers() -> dict[str, str]:
    """Return Authorization header using CLOUDFLARE_API_TOKEN if set."""
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


###################
# BGP Timeseries
###################


class CloudflareRadarBGPTimeseriesParams(BaseModel):
    """Parameters for fetching BGP statistics time series."""

    aggInterval: str = Field(
        default="1h",
        description="Aggregation interval: '15m', '1h', '1d', or '1w'.",
    )
    dateRange: Optional[str] = Field(
        default="7d",
        description=(
            "Relative date range shortcut such as '1d', '7d', '14d', '28d', '12w', '24w', '52w'. "
            "Takes precedence over dateStart/dateEnd."
        ),
    )
    dateStart: Optional[str] = Field(
        None,
        description="Start of the time window (ISO 8601, e.g. '2024-01-01T00:00:00Z').",
    )
    dateEnd: Optional[str] = Field(
        None,
        description="End of the time window (ISO 8601).",
    )


def fetch_cloudflare_radar_bgp_timeseries(
    params: CloudflareRadarBGPTimeseriesParams,
) -> dict:
    """Fetch BGP statistics time series from Cloudflare Radar."""
    query_params: dict[str, Any] = {"aggInterval": params.aggInterval}
    if params.dateRange:
        query_params["dateRange"] = params.dateRange
    if params.dateStart:
        query_params["dateStart"] = params.dateStart
    if params.dateEnd:
        query_params["dateEnd"] = params.dateEnd
    response = http_get(
        f"{BASE_URL}/bgp/timeseries",
        params=query_params,
        headers=_auth_headers(),
    )
    return response.json()


async def handle_cloudflare_radar_bgp_timeseries(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cloudflare-radar-bgp-timeseries tool call."""
    try:
        params = CloudflareRadarBGPTimeseriesParams(**(arguments or {}))
        data = fetch_cloudflare_radar_bgp_timeseries(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Cloudflare Radar BGP timeseries: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cloudflare-radar-bgp-timeseries",
        description=(
            "Get a time series of global BGP statistics (update counts, prefix counts) "
            "from Cloudflare Radar. Requires CLOUDFLARE_API_TOKEN."
        ),
        inputSchema=CloudflareRadarBGPTimeseriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cloudflare-radar-bgp-timeseries"] = (
    handle_cloudflare_radar_bgp_timeseries
)


###################
# BGP Hijack Events
###################


class CloudflareRadarBGPHijacksParams(BaseModel):
    """Parameters for fetching BGP hijack events."""

    page: int = Field(default=0, description="Page number for pagination (0-indexed).")
    per_page: int = Field(
        default=25, ge=1, le=100, description="Results per page (1-100)."
    )
    dateRange: Optional[str] = Field(
        default="7d",
        description="Relative date range (e.g. '1d', '7d', '28d').",
    )
    dateStart: Optional[str] = Field(None, description="Start time (ISO 8601).")
    dateEnd: Optional[str] = Field(None, description="End time (ISO 8601).")
    minConfidence: Optional[int] = Field(
        None,
        description="Minimum confidence score (0-100) to filter hijack events.",
    )


def fetch_cloudflare_radar_bgp_hijacks(
    params: CloudflareRadarBGPHijacksParams,
) -> dict:
    """Fetch BGP hijack events from Cloudflare Radar."""
    query_params: dict[str, Any] = {
        "page": params.page,
        "per_page": params.per_page,
    }
    if params.dateRange:
        query_params["dateRange"] = params.dateRange
    if params.dateStart:
        query_params["dateStart"] = params.dateStart
    if params.dateEnd:
        query_params["dateEnd"] = params.dateEnd
    if params.minConfidence is not None:
        query_params["minConfidence"] = params.minConfidence
    response = http_get(
        f"{BASE_URL}/bgp/hijacks/events",
        params=query_params,
        headers=_auth_headers(),
    )
    return response.json()


async def handle_cloudflare_radar_bgp_hijacks(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cloudflare-radar-bgp-hijacks tool call."""
    try:
        params = CloudflareRadarBGPHijacksParams(**(arguments or {}))
        data = fetch_cloudflare_radar_bgp_hijacks(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Cloudflare Radar BGP hijacks: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cloudflare-radar-bgp-hijacks",
        description=(
            "Get recent BGP route hijack events from Cloudflare Radar. "
            "Requires CLOUDFLARE_API_TOKEN."
        ),
        inputSchema=CloudflareRadarBGPHijacksParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cloudflare-radar-bgp-hijacks"] = handle_cloudflare_radar_bgp_hijacks


###################
# BGP Leak Events
###################


class CloudflareRadarBGPLeaksParams(BaseModel):
    """Parameters for fetching BGP route leak events."""

    page: int = Field(default=0, description="Page number for pagination (0-indexed).")
    per_page: int = Field(
        default=25, ge=1, le=100, description="Results per page (1-100)."
    )
    dateRange: Optional[str] = Field(
        default="7d",
        description="Relative date range (e.g. '1d', '7d', '28d').",
    )
    dateStart: Optional[str] = Field(None, description="Start time (ISO 8601).")
    dateEnd: Optional[str] = Field(None, description="End time (ISO 8601).")


def fetch_cloudflare_radar_bgp_leaks(
    params: CloudflareRadarBGPLeaksParams,
) -> dict:
    """Fetch BGP route leak events from Cloudflare Radar."""
    query_params: dict[str, Any] = {
        "page": params.page,
        "per_page": params.per_page,
    }
    if params.dateRange:
        query_params["dateRange"] = params.dateRange
    if params.dateStart:
        query_params["dateStart"] = params.dateStart
    if params.dateEnd:
        query_params["dateEnd"] = params.dateEnd
    response = http_get(
        f"{BASE_URL}/bgp/leaks/events",
        params=query_params,
        headers=_auth_headers(),
    )
    return response.json()


async def handle_cloudflare_radar_bgp_leaks(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cloudflare-radar-bgp-leaks tool call."""
    try:
        params = CloudflareRadarBGPLeaksParams(**(arguments or {}))
        data = fetch_cloudflare_radar_bgp_leaks(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Cloudflare Radar BGP leaks: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cloudflare-radar-bgp-leaks",
        description=(
            "Get recent BGP route leak events from Cloudflare Radar. "
            "Requires CLOUDFLARE_API_TOKEN."
        ),
        inputSchema=CloudflareRadarBGPLeaksParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cloudflare-radar-bgp-leaks"] = handle_cloudflare_radar_bgp_leaks


###################
# BGP Routes Realtime
###################


class CloudflareRadarBGPRoutesRealtimeParams(BaseModel):
    """Parameters for fetching real-time BGP routes for a prefix."""

    prefix: str = Field(
        ...,
        description="IP prefix in CIDR notation (e.g. '1.1.1.0/24').",
    )


def fetch_cloudflare_radar_bgp_routes_realtime(
    params: CloudflareRadarBGPRoutesRealtimeParams,
) -> dict:
    """Fetch real-time BGP routes for a prefix from Cloudflare Radar."""
    response = http_get(
        f"{BASE_URL}/bgp/routes/realtime",
        params={"prefix": params.prefix},
        headers=_auth_headers(),
    )
    return response.json()


async def handle_cloudflare_radar_bgp_routes_realtime(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cloudflare-radar-bgp-routes-realtime tool call."""
    try:
        if not arguments or "prefix" not in arguments:
            raise ValueError("prefix is required")
        params = CloudflareRadarBGPRoutesRealtimeParams(**arguments)
        data = fetch_cloudflare_radar_bgp_routes_realtime(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Cloudflare Radar BGP routes: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cloudflare-radar-bgp-routes-realtime",
        description=(
            "Get real-time BGP route visibility for a specific IP prefix from Cloudflare Radar. "
            "Requires CLOUDFLARE_API_TOKEN."
        ),
        inputSchema=CloudflareRadarBGPRoutesRealtimeParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cloudflare-radar-bgp-routes-realtime"] = (
    handle_cloudflare_radar_bgp_routes_realtime
)


###################
# Internet Quality Index
###################


class CloudflareRadarInternetQualityParams(BaseModel):
    """Parameters for fetching the Internet Quality Index summary."""

    dateRange: Optional[str] = Field(
        default="7d",
        description="Relative date range (e.g. '1d', '7d', '28d').",
    )
    dateStart: Optional[str] = Field(None, description="Start time (ISO 8601).")
    dateEnd: Optional[str] = Field(None, description="End time (ISO 8601).")
    location: Optional[str] = Field(
        None,
        description="ISO 3166-1 alpha-2 country code to filter by location (e.g. 'US', 'DE').",
    )
    asn: Optional[str] = Field(
        None,
        description="Filter by ASN (e.g. 'AS13335').",
    )


def fetch_cloudflare_radar_internet_quality(
    params: CloudflareRadarInternetQualityParams,
) -> dict:
    """Fetch the Internet Quality Index summary from Cloudflare Radar."""
    query_params: dict[str, Any] = {}
    if params.dateRange:
        query_params["dateRange"] = params.dateRange
    if params.dateStart:
        query_params["dateStart"] = params.dateStart
    if params.dateEnd:
        query_params["dateEnd"] = params.dateEnd
    if params.location:
        query_params["location"] = params.location
    if params.asn:
        query_params["asn"] = params.asn
    response = http_get(
        f"{BASE_URL}/quality/iqi/summary",
        params=query_params,
        headers=_auth_headers(),
    )
    return response.json()


async def handle_cloudflare_radar_internet_quality(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cloudflare-radar-internet-quality tool call."""
    try:
        params = CloudflareRadarInternetQualityParams(**(arguments or {}))
        data = fetch_cloudflare_radar_internet_quality(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Cloudflare Radar Internet Quality: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cloudflare-radar-internet-quality",
        description=(
            "Get the Internet Quality Index (IQI) summary from Cloudflare Radar — "
            "bandwidth, latency, and DNS performance globally or per country/ASN. "
            "Requires CLOUDFLARE_API_TOKEN."
        ),
        inputSchema=CloudflareRadarInternetQualityParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cloudflare-radar-internet-quality"] = (
    handle_cloudflare_radar_internet_quality
)


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-cloudflare-radar",
        RESOURCES,
        RESOURCES_HANDLERS,
        TOOLS,
        TOOLS_HANDLERS,
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
