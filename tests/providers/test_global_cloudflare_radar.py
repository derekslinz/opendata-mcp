import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_cloudflare_radar import (
    handle_cloudflare_radar_bgp_timeseries,
    handle_cloudflare_radar_bgp_hijacks,
    handle_cloudflare_radar_bgp_leaks,
    handle_cloudflare_radar_bgp_routes_realtime,
    handle_cloudflare_radar_internet_quality,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_cloudflare_radar_bgp_timeseries_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {
                "meta": {
                    "dateRange": [{"startTime": "2024-01-01", "endTime": "2024-01-07"}]
                },
                "serie_0": {"timestamps": ["2024-01-01T00:00:00Z"], "total": [100]},
            },
            "success": True,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_cloudflare_radar_bgp_timeseries({"dateRange": "7d"})
        assert "timestamps" in result[0].text


@pytest.mark.anyio
async def test_cloudflare_radar_bgp_timeseries_sends_auth_header(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token-xyz")
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"result": {}, "success": True}
        mock_get.return_value.raise_for_status = Mock()

        await handle_cloudflare_radar_bgp_timeseries({})

        headers = mock_get.call_args.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer test-token-xyz"


@pytest.mark.anyio
async def test_cloudflare_radar_bgp_timeseries_no_auth_without_token(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"result": {}, "success": True}
        mock_get.return_value.raise_for_status = Mock()

        await handle_cloudflare_radar_bgp_timeseries({})

        headers = mock_get.call_args.kwargs.get("headers", {})
        assert "Authorization" not in headers


@pytest.mark.anyio
async def test_cloudflare_radar_bgp_timeseries_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Unauthorized")
        with pytest.raises(httpx.HTTPError):
            await handle_cloudflare_radar_bgp_timeseries({})


@pytest.mark.anyio
async def test_cloudflare_radar_bgp_hijacks_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {
                "events": [
                    {
                        "id": 1,
                        "hijackPrefix": "8.8.8.0/24",
                        "hijackerAsn": 99999,
                        "maxConfidenceScore": 95,
                    }
                ]
            },
            "success": True,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_cloudflare_radar_bgp_hijacks({})
        assert "8.8.8.0/24" in result[0].text
        assert "99999" in result[0].text


@pytest.mark.anyio
async def test_cloudflare_radar_bgp_leaks_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {
                "events": [
                    {
                        "id": 2,
                        "leakSegment": "65000-65001-65002",
                        "leakType": 1,
                    }
                ]
            },
            "success": True,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_cloudflare_radar_bgp_leaks({})
        assert "65000" in result[0].text


@pytest.mark.anyio
async def test_cloudflare_radar_bgp_routes_realtime_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {
                "stats": {"totalPeers": 500, "peersSeeingPrefix": 480},
                "routes": [{"prefix": "1.1.1.0/24", "origin": "AS13335"}],
            },
            "success": True,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_cloudflare_radar_bgp_routes_realtime(
            {"prefix": "1.1.1.0/24"}
        )
        assert "1.1.1.0/24" in result[0].text
        assert "AS13335" in result[0].text


@pytest.mark.anyio
async def test_cloudflare_radar_bgp_routes_realtime_missing_param():
    with pytest.raises(ValueError):
        await handle_cloudflare_radar_bgp_routes_realtime({})


@pytest.mark.anyio
async def test_cloudflare_radar_internet_quality_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {
                "summary_0": {
                    "bandwidthDownload": "50.5",
                    "latency": "15.2",
                    "dnsResponseTime": "20.1",
                }
            },
            "success": True,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_cloudflare_radar_internet_quality({})
        assert "bandwidthDownload" in result[0].text


@pytest.mark.anyio
async def test_cloudflare_radar_internet_quality_with_location():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"result": {}, "success": True}
        mock_get.return_value.raise_for_status = Mock()

        await handle_cloudflare_radar_internet_quality({"location": "DE"})

        call_params = mock_get.call_args.kwargs.get("params", {})
        assert call_params.get("location") == "DE"
