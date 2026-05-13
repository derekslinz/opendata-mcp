import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_bgpview import (
    handle_bgpview_asn,
    handle_bgpview_asn_prefixes,
    handle_bgpview_asn_peers,
    handle_bgpview_asn_upstreams,
    handle_bgpview_asn_downstreams,
    handle_bgpview_ip,
    handle_bgpview_prefix,
    handle_bgpview_search,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_bgpview_asn_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "asn": 13335,
                "name": "CLOUDFLARENET",
                "description_short": "Cloudflare, Inc.",
                "country_code": "US",
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_bgpview_asn({"asn": 13335})
        assert "CLOUDFLARENET" in result[0].text
        assert "13335" in result[0].text


@pytest.mark.anyio
async def test_bgpview_asn_missing_param():
    with pytest.raises(ValueError):
        await handle_bgpview_asn({})


@pytest.mark.anyio
async def test_bgpview_asn_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Service unavailable")
        with pytest.raises(httpx.HTTPError):
            await handle_bgpview_asn({"asn": 13335})


@pytest.mark.anyio
async def test_bgpview_asn_prefixes_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "ipv4_prefixes": [{"prefix": "1.1.1.0/24", "name": "APNIC-LABS"}],
                "ipv6_prefixes": [],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_bgpview_asn_prefixes({"asn": 13335})
        assert "1.1.1.0/24" in result[0].text


@pytest.mark.anyio
async def test_bgpview_asn_peers_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "ipv4_peers": [{"asn": 3356, "name": "LEVEL3"}],
                "ipv6_peers": [],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_bgpview_asn_peers({"asn": 13335})
        assert "LEVEL3" in result[0].text


@pytest.mark.anyio
async def test_bgpview_asn_upstreams_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "ipv4_upstreams": [{"asn": 174, "name": "COGENT-174"}],
                "ipv6_upstreams": [],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_bgpview_asn_upstreams({"asn": 13335})
        assert "COGENT-174" in result[0].text


@pytest.mark.anyio
async def test_bgpview_asn_downstreams_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "ipv4_downstreams": [{"asn": 55555, "name": "SMALLNET"}],
                "ipv6_downstreams": [],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_bgpview_asn_downstreams({"asn": 13335})
        assert "SMALLNET" in result[0].text


@pytest.mark.anyio
async def test_bgpview_ip_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "ip": "1.1.1.1",
                "rir_allocation": {"rir_name": "APNIC"},
                "prefixes": [{"prefix": "1.1.1.0/24", "asn": {"asn": 13335}}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_bgpview_ip({"ip": "1.1.1.1"})
        assert "1.1.1.1" in result[0].text
        assert "APNIC" in result[0].text


@pytest.mark.anyio
async def test_bgpview_ip_missing_param():
    with pytest.raises(ValueError):
        await handle_bgpview_ip({})


@pytest.mark.anyio
async def test_bgpview_prefix_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "prefix": "1.1.1.0/24",
                "asns": [{"asn": 13335, "name": "CLOUDFLARENET"}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_bgpview_prefix({"prefix": "1.1.1.0", "cidr": 24})
        assert "CLOUDFLARENET" in result[0].text


@pytest.mark.anyio
async def test_bgpview_prefix_missing_params():
    with pytest.raises(ValueError):
        await handle_bgpview_prefix({"prefix": "1.1.1.0"})


@pytest.mark.anyio
async def test_bgpview_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "data": {
                "asns": [{"asn": 13335, "name": "CLOUDFLARENET"}],
                "ipv4_prefixes": [],
                "ipv6_prefixes": [],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_bgpview_search({"query_term": "cloudflare"})
        assert "CLOUDFLARENET" in result[0].text


@pytest.mark.anyio
async def test_bgpview_search_missing_param():
    with pytest.raises(ValueError):
        await handle_bgpview_search({})
