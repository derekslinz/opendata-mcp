import json

import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_ripe_stat import (
    TOOLS,
    _ripestat_geoloc_to_shape_payload,
    handle_ripestat_network_info,
    handle_ripestat_bgp_state,
    handle_ripestat_prefix_overview,
    handle_ripestat_announced_prefixes,
    handle_ripestat_routing_history,
    handle_ripestat_geoloc,
    handle_ripestat_asn_neighbours,
    handle_ripestat_asn_neighbours_history,
)
from meta_data_mcp.ui_resources.shape_geofeatures_v1 import URI as GEOFEATURES_URI


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_ripestat_network_info_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "193.0.0.0",
                "asns": ["3333"],
                "prefix": "193.0.0.0/21",
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_network_info({"resource": "193.0.0.1"})
        assert "193.0.0.0/21" in result[0].text
        assert "3333" in result[0].text


@pytest.mark.anyio
async def test_ripestat_network_info_missing_param():
    with pytest.raises(ValueError):
        await handle_ripestat_network_info({})


@pytest.mark.anyio
async def test_ripestat_network_info_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Timeout")
        with pytest.raises(httpx.HTTPError):
            await handle_ripestat_network_info({"resource": "193.0.0.1"})


@pytest.mark.anyio
async def test_ripestat_bgp_state_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "193.0.0.0/21",
                "routes": [{"prefix": "193.0.0.0/21", "origin": "AS3333"}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_bgp_state({"resource": "193.0.0.0/21"})
        assert "AS3333" in result[0].text


@pytest.mark.anyio
async def test_ripestat_bgp_state_with_rrcs():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {"routes": []},
        }
        mock_get.return_value.raise_for_status = Mock()

        await handle_ripestat_bgp_state(
            {"resource": "193.0.0.0/21", "rrcs": "rrc00,rrc01"}
        )
        call_params = mock_get.call_args.kwargs.get("params", {})
        assert call_params.get("rrcs") == "rrc00,rrc01"


@pytest.mark.anyio
async def test_ripestat_prefix_overview_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "193.0.0.0/21",
                "asns": [{"asn": 3333, "holder": "RIPE-NCC-AS"}],
                "visibility": {"v4": {"observed_neighbours": 200}},
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_prefix_overview({"resource": "193.0.0.0/21"})
        assert "RIPE-NCC-AS" in result[0].text


@pytest.mark.anyio
async def test_ripestat_announced_prefixes_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "AS3333",
                "prefixes": [
                    {"prefix": "193.0.0.0/21", "timelines": []},
                    {"prefix": "2001:67c:2e8::/48", "timelines": []},
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_announced_prefixes({"resource": "AS3333"})
        assert "193.0.0.0/21" in result[0].text


@pytest.mark.anyio
async def test_ripestat_routing_history_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "193.0.0.0/21",
                "by_origin": [{"origin": "AS3333", "prefixes": []}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_routing_history({"resource": "193.0.0.0/21"})
        assert "AS3333" in result[0].text


@pytest.mark.anyio
async def test_ripestat_geoloc_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "193.0.0.1",
                "locations": [
                    {
                        "country": "NL",
                        "city": "Amsterdam",
                        "latitude": 52.37,
                        "longitude": 4.9,
                        "resources": ["193.0.0.1"],
                    }
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_geoloc({"resource": "193.0.0.1"})
        assert "Amsterdam" in result[0].text
        assert "NL" in result[0].text


@pytest.mark.anyio
async def test_ripestat_geoloc_missing_param():
    with pytest.raises(ValueError):
        await handle_ripestat_geoloc({})


@pytest.mark.anyio
async def test_ripestat_asn_neighbours_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "AS3333",
                "neighbours": [
                    {"asn": 1234, "type": "left"},
                    {"asn": 5678, "type": "right"},
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_asn_neighbours({"resource": "AS3333"})
        assert "1234" in result[0].text
        assert "5678" in result[0].text


@pytest.mark.anyio
async def test_ripestat_asn_neighbours_missing_param():
    with pytest.raises(ValueError):
        await handle_ripestat_asn_neighbours({})


@pytest.mark.anyio
async def test_ripestat_asn_neighbours_history_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "AS3333",
                "neighbours_series": [
                    {
                        "starttime": "2024-01-01T00:00:00",
                        "endtime": "2024-01-07T00:00:00",
                        "neighbours": [{"asn": 1234, "type": "left"}],
                    }
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_asn_neighbours_history({"resource": "AS3333"})
        assert "neighbours_series" in result[0].text
        assert "1234" in result[0].text


@pytest.mark.anyio
async def test_ripestat_asn_neighbours_history_with_params():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok", "data": {}}
        mock_get.return_value.raise_for_status = Mock()

        await handle_ripestat_asn_neighbours_history(
            {"resource": "AS3333", "starttime": "2024-01-01T00:00:00", "max_rows": 100}
        )
        call_params = mock_get.call_args.kwargs.get("params", {})
        assert call_params.get("starttime") == "2024-01-01T00:00:00"
        assert call_params.get("max_rows") == 100


@pytest.mark.anyio
async def test_ripestat_asn_neighbours_history_missing_param():
    with pytest.raises(ValueError):
        await handle_ripestat_asn_neighbours_history({})


# ---------------------------------------------------------------------------
# Phase 4: MCP Apps shape primitive binding for ripestat-geoloc.
# ---------------------------------------------------------------------------


def test_adapter_maps_locations_to_features():
    raw = {
        "status": "ok",
        "data": {
            "resource": "193.0.0.1",
            "locations": [
                {
                    "country": "NL",
                    "city": "Amsterdam",
                    "latitude": 52.37,
                    "longitude": 4.9,
                    "resources": ["193.0.0.1"],
                },
                {
                    "country": "DE",
                    "city": "Frankfurt",
                    "latitude": 50.11,
                    "longitude": 8.68,
                    "resources": ["193.0.0.2"],
                },
            ],
        },
    }
    payload = _ripestat_geoloc_to_shape_payload(raw)
    assert len(payload["features"]) == 2
    assert payload["features"][0]["lat"] == 52.37
    assert payload["features"][0]["lon"] == 4.9
    assert payload["features"][0]["attrs"]["city"] == "Amsterdam"
    assert payload["features"][0]["attrs"]["country"] == "NL"
    # Coordinate keys stripped from attrs (already promoted)
    assert "latitude" not in payload["features"][0]["attrs"]


def test_adapter_handles_empty_locations():
    raw = {"data": {"resource": "x", "locations": []}}
    assert _ripestat_geoloc_to_shape_payload(raw) == {"features": []}


def test_adapter_handles_missing_structure():
    """Empty data block or missing locations key must not crash."""
    assert _ripestat_geoloc_to_shape_payload({}) == {"features": []}
    assert _ripestat_geoloc_to_shape_payload({"data": {}}) == {"features": []}
    assert _ripestat_geoloc_to_shape_payload("err") == {"features": []}


def test_adapter_skips_locations_without_coords():
    raw = {
        "data": {
            "locations": [
                {"country": "NL", "city": "no coords"},
                {"latitude": "bad", "longitude": 4.9, "city": "bad lat"},
                {"latitude": 200.0, "longitude": 4.9, "city": "out of range"},
                {"latitude": 52.37, "longitude": 4.9, "city": "ok"},
            ]
        }
    }
    payload = _ripestat_geoloc_to_shape_payload(raw)
    assert len(payload["features"]) == 1
    assert payload["features"][0]["attrs"]["city"] == "ok"


def test_geoloc_tool_binds_to_geofeatures_shape_primitive():
    tool = next(t for t in TOOLS if t.name == "ripestat-geoloc")
    assert tool.meta == {"ui": {"resourceUri": GEOFEATURES_URI}}
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert wire.get("_meta", {}).get("ui", {}).get("resourceUri") == GEOFEATURES_URI


@pytest.mark.anyio
async def test_ripestat_geoloc_returns_shape_payload():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "resource": "193.0.0.1",
                "locations": [
                    {
                        "country": "NL",
                        "city": "Amsterdam",
                        "latitude": 52.37,
                        "longitude": 4.9,
                        "resources": ["193.0.0.1"],
                    }
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ripestat_geoloc({"resource": "193.0.0.1"})
        body = json.loads(result[0].text)
        assert body["features"][0]["lat"] == 52.37
        assert body["features"][0]["lon"] == 4.9
        assert body["features"][0]["attrs"]["city"] == "Amsterdam"
        assert body["features"][0]["attrs"]["country"] == "NL"
