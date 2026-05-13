"""
BGPView provider tests.

BGPView (api.bgpview.io) shut down. All handlers now return a service-unavailable
error message pointing users to the RIPEstat alternatives.
"""

import json

import pytest

from meta_data_mcp.providers.global_bgpview import (
    handle_bgpview_asn,
    handle_bgpview_asn_downstreams,
    handle_bgpview_asn_peers,
    handle_bgpview_asn_prefixes,
    handle_bgpview_asn_upstreams,
    handle_bgpview_ip,
    handle_bgpview_prefix,
    handle_bgpview_search,
    TOOLS,
    TOOLS_HANDLERS,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _text(coro):
    result = await coro
    return result[0].text


@pytest.mark.anyio
async def test_all_handlers_return_unavailable_message():
    handlers = [
        handle_bgpview_asn,
        handle_bgpview_asn_prefixes,
        handle_bgpview_asn_peers,
        handle_bgpview_asn_upstreams,
        handle_bgpview_asn_downstreams,
        handle_bgpview_ip,
        handle_bgpview_prefix,
        handle_bgpview_search,
    ]
    for handler in handlers:
        text = await _text(handler({}))
        payload = json.loads(text)
        assert "error" in payload
        assert "BGPView" in payload["error"]
        assert "ripestat" in payload["error"]


def test_all_tools_registered():
    assert len(TOOLS) == 8
    names = {t.name for t in TOOLS}
    assert "bgpview-asn-info" in names
    assert "bgpview-search" in names


def test_tools_descriptions_mention_unavailable():
    for tool in TOOLS:
        assert "SERVICE UNAVAILABLE" in tool.description


def test_all_handlers_in_tools_handlers():
    for tool in TOOLS:
        assert tool.name in TOOLS_HANDLERS
