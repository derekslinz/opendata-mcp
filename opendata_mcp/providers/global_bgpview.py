"""
BGPView.io Provider

This module exposes BGPView's public REST API, which provides free access to
BGP routing data including Autonomous System (ASN) details, IP prefix
information, peer relationships, and network search.

License / source:
    Data is sourced from RouteViews, RIPE NCC RIS, and other BGP collectors.
    BGPView provides it under their public terms of service.
    Consult https://bgpview.docs.apiary.io/ for API details.

Features:
- ASN details (name, description, RIR)
- Prefixes announced by an ASN (v4 and v6)
- ASN peers, upstreams, and downstreams
- IP address information (ASN, prefix, RIR)
- IP prefix information
- Free-text search across ASNs and prefixes

Usage:
    The module can be run directly to start an MCP server, or its components
    can be imported individually.
"""

import logging
from typing import Any, List, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

log = logging.getLogger(__name__)

BASE_URL = "https://api.bgpview.io"

RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# ASN Info
###################


class BGPViewASNParams(BaseModel):
    """Parameters for fetching ASN details."""

    asn: int = Field(
        ..., description="Autonomous System Number (e.g. 13335 for Cloudflare)."
    )


def fetch_bgpview_asn(params: BGPViewASNParams) -> dict:
    """Fetch ASN details from BGPView."""
    response = http_get(f"{BASE_URL}/asn/{params.asn}")
    return response.json()


async def handle_bgpview_asn(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the bgpview-asn-info tool call."""
    try:
        if not arguments or "asn" not in arguments:
            raise ValueError("asn is required")
        params = BGPViewASNParams(**arguments)
        data = fetch_bgpview_asn(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching BGPView ASN info: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="bgpview-asn-info",
        description="Get details for an Autonomous System Number (ASN): name, description, RIR, country, and contact.",
        inputSchema=BGPViewASNParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["bgpview-asn-info"] = handle_bgpview_asn


###################
# ASN Prefixes
###################


class BGPViewASNPrefixesParams(BaseModel):
    """Parameters for listing prefixes announced by an ASN."""

    asn: int = Field(..., description="Autonomous System Number.")


def fetch_bgpview_asn_prefixes(params: BGPViewASNPrefixesParams) -> dict:
    """Fetch prefixes announced by an ASN from BGPView."""
    response = http_get(f"{BASE_URL}/asn/{params.asn}/prefixes")
    return response.json()


async def handle_bgpview_asn_prefixes(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the bgpview-asn-prefixes tool call."""
    try:
        if not arguments or "asn" not in arguments:
            raise ValueError("asn is required")
        params = BGPViewASNPrefixesParams(**arguments)
        data = fetch_bgpview_asn_prefixes(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching BGPView ASN prefixes: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="bgpview-asn-prefixes",
        description="List IPv4 and IPv6 prefixes announced by an ASN.",
        inputSchema=BGPViewASNPrefixesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["bgpview-asn-prefixes"] = handle_bgpview_asn_prefixes


###################
# ASN Peers
###################


class BGPViewASNPeersParams(BaseModel):
    """Parameters for listing peers of an ASN."""

    asn: int = Field(..., description="Autonomous System Number.")


def fetch_bgpview_asn_peers(params: BGPViewASNPeersParams) -> dict:
    """Fetch peers of an ASN from BGPView."""
    response = http_get(f"{BASE_URL}/asn/{params.asn}/peers")
    return response.json()


async def handle_bgpview_asn_peers(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the bgpview-asn-peers tool call."""
    try:
        if not arguments or "asn" not in arguments:
            raise ValueError("asn is required")
        params = BGPViewASNPeersParams(**arguments)
        data = fetch_bgpview_asn_peers(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching BGPView ASN peers: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="bgpview-asn-peers",
        description="List IPv4 and IPv6 BGP peers of an ASN.",
        inputSchema=BGPViewASNPeersParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["bgpview-asn-peers"] = handle_bgpview_asn_peers


###################
# ASN Upstreams
###################


class BGPViewASNUpstreamsParams(BaseModel):
    """Parameters for listing upstreams of an ASN."""

    asn: int = Field(..., description="Autonomous System Number.")


def fetch_bgpview_asn_upstreams(params: BGPViewASNUpstreamsParams) -> dict:
    """Fetch upstreams of an ASN from BGPView."""
    response = http_get(f"{BASE_URL}/asn/{params.asn}/upstreams")
    return response.json()


async def handle_bgpview_asn_upstreams(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the bgpview-asn-upstreams tool call."""
    try:
        if not arguments or "asn" not in arguments:
            raise ValueError("asn is required")
        params = BGPViewASNUpstreamsParams(**arguments)
        data = fetch_bgpview_asn_upstreams(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching BGPView ASN upstreams: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="bgpview-asn-upstreams",
        description="List upstream providers (transit ASNs) for an ASN over IPv4 and IPv6.",
        inputSchema=BGPViewASNUpstreamsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["bgpview-asn-upstreams"] = handle_bgpview_asn_upstreams


###################
# ASN Downstreams
###################


class BGPViewASNDownstreamsParams(BaseModel):
    """Parameters for listing downstreams of an ASN."""

    asn: int = Field(..., description="Autonomous System Number.")


def fetch_bgpview_asn_downstreams(params: BGPViewASNDownstreamsParams) -> dict:
    """Fetch downstreams of an ASN from BGPView."""
    response = http_get(f"{BASE_URL}/asn/{params.asn}/downstreams")
    return response.json()


async def handle_bgpview_asn_downstreams(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the bgpview-asn-downstreams tool call."""
    try:
        if not arguments or "asn" not in arguments:
            raise ValueError("asn is required")
        params = BGPViewASNDownstreamsParams(**arguments)
        data = fetch_bgpview_asn_downstreams(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching BGPView ASN downstreams: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="bgpview-asn-downstreams",
        description="List downstream customers of an ASN over IPv4 and IPv6.",
        inputSchema=BGPViewASNDownstreamsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["bgpview-asn-downstreams"] = handle_bgpview_asn_downstreams


###################
# IP Info
###################


class BGPViewIPParams(BaseModel):
    """Parameters for fetching information about an IP address."""

    ip: str = Field(
        ..., description="IPv4 or IPv6 address (e.g. '1.1.1.1' or '2606:4700::1')."
    )


def fetch_bgpview_ip(params: BGPViewIPParams) -> dict:
    """Fetch IP address information from BGPView."""
    response = http_get(f"{BASE_URL}/ip/{params.ip}")
    return response.json()


async def handle_bgpview_ip(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the bgpview-ip-info tool call."""
    try:
        if not arguments or "ip" not in arguments:
            raise ValueError("ip is required")
        params = BGPViewIPParams(**arguments)
        data = fetch_bgpview_ip(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching BGPView IP info: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="bgpview-ip-info",
        description="Get BGP and RIR information for an IPv4 or IPv6 address: originating ASN, prefix, RIR, and geolocation.",
        inputSchema=BGPViewIPParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["bgpview-ip-info"] = handle_bgpview_ip


###################
# Prefix Info
###################


class BGPViewPrefixParams(BaseModel):
    """Parameters for fetching information about an IP prefix."""

    prefix: str = Field(
        ..., description="IP prefix without mask length (e.g. '1.1.1.0')."
    )
    cidr: int = Field(..., description="CIDR mask length (e.g. 24).")


def fetch_bgpview_prefix(params: BGPViewPrefixParams) -> dict:
    """Fetch IP prefix information from BGPView."""
    response = http_get(f"{BASE_URL}/prefix/{params.prefix}/{params.cidr}")
    return response.json()


async def handle_bgpview_prefix(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the bgpview-prefix-info tool call."""
    try:
        if not arguments or "prefix" not in arguments or "cidr" not in arguments:
            raise ValueError("prefix and cidr are required")
        params = BGPViewPrefixParams(**arguments)
        data = fetch_bgpview_prefix(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching BGPView prefix info: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="bgpview-prefix-info",
        description="Get BGP information for an IP prefix: announcing ASNs, RIR, description, and related ASNs.",
        inputSchema=BGPViewPrefixParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["bgpview-prefix-info"] = handle_bgpview_prefix


###################
# Search
###################


class BGPViewSearchParams(BaseModel):
    """Parameters for searching BGPView."""

    query_term: str = Field(
        ...,
        description="Search term — an ASN number, network name, IP address, or description.",
    )


def fetch_bgpview_search(params: BGPViewSearchParams) -> dict:
    """Search BGPView for ASNs and prefixes."""
    response = http_get(f"{BASE_URL}/search", params={"query_term": params.query_term})
    return response.json()


async def handle_bgpview_search(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the bgpview-search tool call."""
    try:
        if not arguments or "query_term" not in arguments:
            raise ValueError("query_term is required")
        params = BGPViewSearchParams(**arguments)
        data = fetch_bgpview_search(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching BGPView: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="bgpview-search",
        description="Search BGPView for ASNs and prefixes by name, number, or description.",
        inputSchema=BGPViewSearchParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["bgpview-search"] = handle_bgpview_search


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-bgpview", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
