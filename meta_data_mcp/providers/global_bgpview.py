"""
BGPView.io Provider — DEPRECATED

BGPView (api.bgpview.io) shut down and is no longer available.
All tools return an error directing users to the ripestat-* alternatives.

Use ripestat-network-info, ripestat-bgp-state, ripestat-announced-prefixes,
ripestat-asn-neighbours, and ripestat-asn-neighbours-history instead.
"""

import logging
from typing import Any, List, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import serialize_for_llm

log = logging.getLogger(__name__)

RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

_UNAVAILABLE_MSG = (
    "BGPView (api.bgpview.io) shut down and is no longer available. "
    "Use the RIPE NCC RIPEstat tools instead: "
    "ripestat-network-info, ripestat-bgp-state, ripestat-announced-prefixes, "
    "ripestat-asn-neighbours, ripestat-asn-neighbours-history."
)


def _unavailable() -> list[types.TextContent]:
    return [types.TextContent(type="text", text=serialize_for_llm({"error": _UNAVAILABLE_MSG}))]


class BGPViewASNParams(BaseModel):
    asn: int = Field(..., description="Autonomous System Number.")


class BGPViewASNPrefixesParams(BaseModel):
    asn: int = Field(..., description="Autonomous System Number.")


class BGPViewASNPeersParams(BaseModel):
    asn: int = Field(..., description="Autonomous System Number.")


class BGPViewASNUpstreamsParams(BaseModel):
    asn: int = Field(..., description="Autonomous System Number.")


class BGPViewASNDownstreamsParams(BaseModel):
    asn: int = Field(..., description="Autonomous System Number.")


class BGPViewIPParams(BaseModel):
    ip: str = Field(..., description="IPv4 or IPv6 address.")


class BGPViewPrefixParams(BaseModel):
    prefix: str = Field(..., description="IP prefix without mask length.")
    cidr: int = Field(..., description="CIDR mask length.")


class BGPViewSearchParams(BaseModel):
    query_term: str = Field(..., description="ASN number, network name, IP, or description.")


_DEPRECATED_NOTE = " [SERVICE UNAVAILABLE — use ripestat-* tools instead]"

async def _handle_unavailable(arguments: dict[str, Any] | None = None) -> list[types.TextContent]:
    return _unavailable()


# Named exports kept for backward compatibility
handle_bgpview_asn = _handle_unavailable
handle_bgpview_asn_prefixes = _handle_unavailable
handle_bgpview_asn_peers = _handle_unavailable
handle_bgpview_asn_upstreams = _handle_unavailable
handle_bgpview_asn_downstreams = _handle_unavailable
handle_bgpview_ip = _handle_unavailable
handle_bgpview_prefix = _handle_unavailable
handle_bgpview_search = _handle_unavailable


for _name, _desc, _schema in [
    ("bgpview-asn-info", "ASN details" + _DEPRECATED_NOTE, BGPViewASNParams),
    ("bgpview-asn-prefixes", "ASN announced prefixes" + _DEPRECATED_NOTE, BGPViewASNPrefixesParams),
    ("bgpview-asn-peers", "ASN BGP peers" + _DEPRECATED_NOTE, BGPViewASNPeersParams),
    ("bgpview-asn-upstreams", "ASN upstream providers" + _DEPRECATED_NOTE, BGPViewASNUpstreamsParams),
    ("bgpview-asn-downstreams", "ASN downstream customers" + _DEPRECATED_NOTE, BGPViewASNDownstreamsParams),
    ("bgpview-ip-info", "IP address BGP info" + _DEPRECATED_NOTE, BGPViewIPParams),
    ("bgpview-prefix-info", "IP prefix BGP info" + _DEPRECATED_NOTE, BGPViewPrefixParams),
    ("bgpview-search", "Search ASNs and prefixes" + _DEPRECATED_NOTE, BGPViewSearchParams),
]:
    TOOLS.append(types.Tool(name=_name, description=_desc, inputSchema=_schema.model_json_schema()))
    TOOLS_HANDLERS[_name] = _handle_unavailable


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-bgpview", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )
    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
