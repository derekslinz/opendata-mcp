import pytest
from unittest.mock import patch, Mock
import httpx
from meta_data_mcp.providers.global_overpass import (
    handle_query,
    handle_status,
    handle_around_amenity,
    handle_bbox_feature,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _mock_json_response(mock_get, payload):
    """Configure mock_get to return JSON content-type."""
    mock_get.return_value.json.return_value = payload
    mock_get.return_value.raise_for_status = Mock()
    mock_get.return_value.headers = {"content-type": "application/json; charset=utf-8"}
    mock_get.return_value.text = str(payload)


def _mock_text_response(mock_get, text):
    """Configure mock_get to return plain-text content-type."""
    mock_get.return_value.raise_for_status = Mock()
    mock_get.return_value.headers = {"content-type": "text/plain; charset=utf-8"}
    mock_get.return_value.text = text
    # _run_overpass_query falls back to json() if content-type doesn't match;
    # status uses .text directly, but make json() raise to force fallback.
    mock_get.return_value.json.side_effect = ValueError("not json")


@pytest.mark.anyio
async def test_overpass_query_success():
    with patch("httpx.get") as mock_get:
        _mock_json_response(
            mock_get,
            {"elements": [{"type": "node", "id": 1, "tags": {"amenity": "cafe"}}]},
        )
        result = await handle_query(
            {
                "query": '[out:json];node["amenity"="cafe"](around:500,52.52,13.41);out body;'
            }
        )
        assert "cafe" in result[0].text


@pytest.mark.anyio
async def test_overpass_query_requires_query():
    with pytest.raises(ValueError):
        await handle_query({})


@pytest.mark.anyio
async def test_overpass_query_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")
        with pytest.raises(httpx.HTTPError):
            await handle_query({"query": "[out:json];out body;"})


@pytest.mark.anyio
async def test_overpass_status_success():
    with patch("httpx.get") as mock_get:
        _mock_text_response(mock_get, "Connected as: 12345\n1 slots available")
        result = await handle_status()
        assert "slots available" in result[0].text


@pytest.mark.anyio
async def test_overpass_around_amenity_success():
    with patch("httpx.get") as mock_get:
        _mock_json_response(
            mock_get,
            {"elements": [{"type": "node", "id": 99, "tags": {"amenity": "cafe"}}]},
        )
        result = await handle_around_amenity(
            {"amenity": "cafe", "lat": 52.52, "lon": 13.41, "radius": 500}
        )
        assert "cafe" in result[0].text
        # Verify the constructed query contains the around clause
        called_kwargs = mock_get.call_args.kwargs
        assert "params" in called_kwargs
        assert "around:500,52.52,13.41" in called_kwargs["params"]["data"]


@pytest.mark.anyio
async def test_overpass_around_amenity_requires_args():
    with pytest.raises(ValueError):
        await handle_around_amenity({"amenity": "cafe"})


@pytest.mark.anyio
async def test_overpass_bbox_feature_success():
    with patch("httpx.get") as mock_get:
        _mock_json_response(
            mock_get,
            {"elements": [{"type": "node", "id": 7, "tags": {"highway": "primary"}}]},
        )
        result = await handle_bbox_feature(
            {
                "key": "highway",
                "value": "primary",
                "s": 52.5,
                "w": 13.3,
                "n": 52.6,
                "e": 13.5,
            }
        )
        assert "primary" in result[0].text
        called_kwargs = mock_get.call_args.kwargs
        assert "params" in called_kwargs
        # Should have both node and way clauses inside the bbox
        assert '"highway"="primary"' in called_kwargs["params"]["data"]
        assert "52.5,13.3,52.6,13.5" in called_kwargs["params"]["data"]


@pytest.mark.anyio
async def test_overpass_bbox_feature_requires_args():
    with pytest.raises(ValueError):
        await handle_bbox_feature({"key": "highway", "value": "primary"})
