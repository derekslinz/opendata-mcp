import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_ripe_stat import (
    handle_ripestat_network_info,
    handle_ripestat_bgp_state,
    handle_ripestat_prefix_overview,
    handle_ripestat_announced_prefixes,
    handle_ripestat_routing_history,
    handle_ripestat_geoloc,
)


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
