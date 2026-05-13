"""
RIPE NCC RIPEstat Provider

This module exposes RIPE NCC's RIPEstat data API, which provides production-
grade BGP routing data, network information, and Internet routing analytics.

License / source:
    Data is provided by RIPE NCC under their terms of service.
    Most RIPEstat data is available free of charge without authentication.
    Consult https://stat.ripe.net/docs/data_api for details.

Fair-use notes:
    - No API key is required for basic queries.
    - Identify your application by setting OPENDATA_MCP_CONTACT.

Features:
- Network info for an IP or prefix (covering ASN and RIR details)
- BGP state (routing table snapshot for a prefix or ASN)
- Prefix overview (origin ASNs, visibility)
- Prefixes announced by an ASN
- Routing history for a prefix or ASN
- Geolocation of an IP address

Usage:
    The module can be run directly to start an MCP server, or its components
    can be imported individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

log = logging.getLogger(__name__)

BASE_URL = "https://stat.ripe.net/data"

RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Network Info
###################


class RIPEStatNetworkInfoParams(BaseModel):
    """Parameters for fetching network info for an IP or prefix."""

    resource: str = Field(
        ...,
        description=(
            "An IP address, prefix (e.g. '193.0.0.0/21'), or ASN (e.g. 'AS3333'). "
            "Returns the containing prefix and announcing ASN."
        ),
    )


def fetch_ripestat_network_info(params: RIPEStatNetworkInfoParams) -> dict:
    """Fetch network info from RIPEstat."""
    response = http_get(
        f"{BASE_URL}/network-info/data.json",
        params={"resource": params.resource},
    )
    return response.json()


async def handle_ripestat_network_info(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ripestat-network-info tool call."""
    try:
        if not arguments or "resource" not in arguments:
            raise ValueError("resource is required")
        params = RIPEStatNetworkInfoParams(**arguments)
        data = fetch_ripestat_network_info(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching RIPEstat network info: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ripestat-network-info",
        description=(
            "Get the BGP prefix and announcing ASN(s) for an IP address or prefix using RIPE NCC RIPEstat."
        ),
        inputSchema=RIPEStatNetworkInfoParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ripestat-network-info"] = handle_ripestat_network_info


###################
# BGP State
###################


class RIPEStatBGPStateParams(BaseModel):
    """Parameters for fetching the current BGP routing table state."""

    resource: str = Field(
        ...,
        description=(
            "An IP prefix (e.g. '193.0.0.0/21') or ASN (e.g. 'AS3333'). "
            "Returns current BGP routing entries from RIPE RIS collectors."
        ),
    )
    rrcs: Optional[str] = Field(
        None,
        description="Comma-separated list of RIPE RIS Route Collectors (e.g. 'rrc00,rrc01'). Defaults to all.",
    )


def fetch_ripestat_bgp_state(params: RIPEStatBGPStateParams) -> dict:
    """Fetch BGP state from RIPEstat."""
    query_params: dict[str, Any] = {"resource": params.resource}
    if params.rrcs:
        query_params["rrcs"] = params.rrcs
    response = http_get(f"{BASE_URL}/bgp-state/data.json", params=query_params)
    return response.json()


async def handle_ripestat_bgp_state(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ripestat-bgp-state tool call."""
    try:
        if not arguments or "resource" not in arguments:
            raise ValueError("resource is required")
        params = RIPEStatBGPStateParams(**arguments)
        data = fetch_ripestat_bgp_state(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching RIPEstat BGP state: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ripestat-bgp-state",
        description=(
            "Get a snapshot of the current BGP routing table state for a prefix or ASN "
            "from RIPE NCC RIS collectors."
        ),
        inputSchema=RIPEStatBGPStateParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ripestat-bgp-state"] = handle_ripestat_bgp_state


###################
# Prefix Overview
###################


class RIPEStatPrefixOverviewParams(BaseModel):
    """Parameters for fetching a prefix overview."""

    resource: str = Field(
        ...,
        description="IP prefix (e.g. '193.0.0.0/21'). Returns origin ASNs, visibility, and RIR info.",
    )


def fetch_ripestat_prefix_overview(params: RIPEStatPrefixOverviewParams) -> dict:
    """Fetch prefix overview from RIPEstat."""
    response = http_get(
        f"{BASE_URL}/prefix-overview/data.json",
        params={"resource": params.resource},
    )
    return response.json()


async def handle_ripestat_prefix_overview(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ripestat-prefix-overview tool call."""
    try:
        if not arguments or "resource" not in arguments:
            raise ValueError("resource is required")
        params = RIPEStatPrefixOverviewParams(**arguments)
        data = fetch_ripestat_prefix_overview(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching RIPEstat prefix overview: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ripestat-prefix-overview",
        description=(
            "Get an overview of an IP prefix: originating ASNs, visibility across route "
            "collectors, RIR, and related prefixes."
        ),
        inputSchema=RIPEStatPrefixOverviewParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ripestat-prefix-overview"] = handle_ripestat_prefix_overview


###################
# Announced Prefixes
###################


class RIPEStatAnnouncedPrefixesParams(BaseModel):
    """Parameters for listing prefixes announced by an ASN."""

    resource: str = Field(
        ...,
        description="ASN (e.g. 'AS3333' or '3333'). Returns all prefixes originated by this ASN.",
    )
    starttime: Optional[str] = Field(
        None,
        description="Start of the time window (ISO 8601, e.g. '2024-01-01T00:00:00'). Defaults to 2 weeks ago.",
    )
    endtime: Optional[str] = Field(
        None,
        description="End of the time window (ISO 8601). Defaults to now.",
    )
    min_peers_seeing: Optional[int] = Field(
        None,
        description="Minimum number of RIS peers that must have seen a prefix to be included.",
    )


def fetch_ripestat_announced_prefixes(
    params: RIPEStatAnnouncedPrefixesParams,
) -> dict:
    """Fetch announced prefixes for an ASN from RIPEstat."""
    query_params: dict[str, Any] = {"resource": params.resource}
    if params.starttime:
        query_params["starttime"] = params.starttime
    if params.endtime:
        query_params["endtime"] = params.endtime
    if params.min_peers_seeing is not None:
        query_params["min_peers_seeing"] = params.min_peers_seeing
    response = http_get(f"{BASE_URL}/announced-prefixes/data.json", params=query_params)
    return response.json()


async def handle_ripestat_announced_prefixes(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ripestat-announced-prefixes tool call."""
    try:
        if not arguments or "resource" not in arguments:
            raise ValueError("resource is required")
        params = RIPEStatAnnouncedPrefixesParams(**arguments)
        data = fetch_ripestat_announced_prefixes(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching RIPEstat announced prefixes: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ripestat-announced-prefixes",
        description="List all IP prefixes announced by an ASN over a time window.",
        inputSchema=RIPEStatAnnouncedPrefixesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ripestat-announced-prefixes"] = handle_ripestat_announced_prefixes


###################
# Routing History
###################


class RIPEStatRoutingHistoryParams(BaseModel):
    """Parameters for fetching routing history."""

    resource: str = Field(
        ...,
        description=(
            "IP prefix (e.g. '193.0.0.0/21') or ASN (e.g. 'AS3333'). "
            "Returns a timeline of routing changes."
        ),
    )
    starttime: Optional[str] = Field(
        None,
        description="Start of the time window (ISO 8601). Defaults to 2 weeks ago.",
    )
    endtime: Optional[str] = Field(
        None,
        description="End of the time window (ISO 8601). Defaults to now.",
    )


def fetch_ripestat_routing_history(params: RIPEStatRoutingHistoryParams) -> dict:
    """Fetch routing history from RIPEstat."""
    query_params: dict[str, Any] = {"resource": params.resource}
    if params.starttime:
        query_params["starttime"] = params.starttime
    if params.endtime:
        query_params["endtime"] = params.endtime
    response = http_get(f"{BASE_URL}/routing-history/data.json", params=query_params)
    return response.json()


async def handle_ripestat_routing_history(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ripestat-routing-history tool call."""
    try:
        if not arguments or "resource" not in arguments:
            raise ValueError("resource is required")
        params = RIPEStatRoutingHistoryParams(**arguments)
        data = fetch_ripestat_routing_history(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching RIPEstat routing history: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ripestat-routing-history",
        description=(
            "Get the routing history (announcements and withdrawals) for an IP prefix or ASN."
        ),
        inputSchema=RIPEStatRoutingHistoryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ripestat-routing-history"] = handle_ripestat_routing_history


###################
# ASN Neighbours
###################


class RIPEStatASNNeighboursParams(BaseModel):
    """Parameters for fetching current BGP neighbours of an ASN."""

    resource: str = Field(
        ...,
        description="ASN (e.g. 'AS3333' or '3333'). Returns current BGP neighbors.",
    )
    starttime: Optional[str] = Field(
        None,
        description="Start of the time window (ISO 8601). Defaults to most recent data.",
    )
    endtime: Optional[str] = Field(
        None,
        description="End of the time window (ISO 8601). Defaults to now.",
    )


def fetch_ripestat_asn_neighbours(params: RIPEStatASNNeighboursParams) -> dict:
    query_params: dict[str, Any] = {"resource": params.resource}
    if params.starttime:
        query_params["starttime"] = params.starttime
    if params.endtime:
        query_params["endtime"] = params.endtime
    response = http_get(f"{BASE_URL}/asn-neighbours/data.json", params=query_params)
    return response.json()


async def handle_ripestat_asn_neighbours(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    try:
        if not arguments or "resource" not in arguments:
            raise ValueError("resource is required")
        params = RIPEStatASNNeighboursParams(**arguments)
        data = fetch_ripestat_asn_neighbours(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching RIPEstat ASN neighbours: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ripestat-asn-neighbours",
        description=(
            "Get the current BGP neighbors (peers, upstreams, downstreams) of an ASN "
            "from RIPE NCC RIS. Returns neighbor ASNs grouped by relationship type."
        ),
        inputSchema=RIPEStatASNNeighboursParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ripestat-asn-neighbours"] = handle_ripestat_asn_neighbours


###################
# ASN Neighbours History
###################


class RIPEStatASNNeighboursHistoryParams(BaseModel):
    """Parameters for fetching historical BGP neighbour data for an ASN."""

    resource: str = Field(
        ...,
        description="ASN (e.g. 'AS3333' or '3333'). Returns historical BGP neighbor changes.",
    )
    starttime: Optional[str] = Field(
        None,
        description="Start of the time window (ISO 8601). Defaults to 2 weeks ago.",
    )
    endtime: Optional[str] = Field(
        None,
        description="End of the time window (ISO 8601). Defaults to now.",
    )
    max_rows: Optional[int] = Field(
        None,
        description="Maximum number of result rows to return.",
    )


def fetch_ripestat_asn_neighbours_history(
    params: RIPEStatASNNeighboursHistoryParams,
) -> dict:
    query_params: dict[str, Any] = {"resource": params.resource}
    if params.starttime:
        query_params["starttime"] = params.starttime
    if params.endtime:
        query_params["endtime"] = params.endtime
    if params.max_rows is not None:
        query_params["max_rows"] = params.max_rows
    response = http_get(
        f"{BASE_URL}/asn-neighbours-history/data.json", params=query_params
    )
    return response.json()


async def handle_ripestat_asn_neighbours_history(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    try:
        if not arguments or "resource" not in arguments:
            raise ValueError("resource is required")
        params = RIPEStatASNNeighboursHistoryParams(**arguments)
        data = fetch_ripestat_asn_neighbours_history(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching RIPEstat ASN neighbours history: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ripestat-asn-neighbours-history",
        description=(
            "Get the historical BGP neighbour relationships for an ASN over a time window. "
            "Shows how peering, transit, and customer relationships changed over time."
        ),
        inputSchema=RIPEStatASNNeighboursHistoryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ripestat-asn-neighbours-history"] = handle_ripestat_asn_neighbours_history


###################
# Geolocation
###################


class RIPEStatGeolocParams(BaseModel):
    """Parameters for geolocating an IP address or prefix."""

    resource: str = Field(
        ...,
        description="IP address or prefix (e.g. '193.0.0.1' or '193.0.0.0/21').",
    )


def fetch_ripestat_geoloc(params: RIPEStatGeolocParams) -> dict:
    """Fetch geolocation data from RIPEstat."""
    response = http_get(
        f"{BASE_URL}/geoloc/data.json",
        params={"resource": params.resource},
    )
    return response.json()


async def handle_ripestat_geoloc(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ripestat-geoloc tool call."""
    try:
        if not arguments or "resource" not in arguments:
            raise ValueError("resource is required")
        params = RIPEStatGeolocParams(**arguments)
        data = fetch_ripestat_geoloc(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching RIPEstat geoloc: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ripestat-geoloc",
        description="Get the geolocation (country, coordinates) of an IP address or prefix using RIPE NCC data.",
        inputSchema=RIPEStatGeolocParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ripestat-geoloc"] = handle_ripestat_geoloc


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-ripe-stat", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
