"""Tests for the global-openaq provider."""

from unittest.mock import Mock, patch

import httpx
import pytest

from meta_data_mcp.providers.global_openaq import (
    OpenAqListLocationsParams,
    OpenAqListParametersParams,
    OpenAqLocationLatestParams,
    fetch_openaq_list_locations,
    fetch_openaq_list_parameters,
    fetch_openaq_location_latest,
    handle_openaq_list_locations,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _ok_response(payload: dict) -> Mock:
    r = Mock()
    r.json.return_value = payload
    r.raise_for_status = Mock()
    r.status_code = 200
    r.headers = {}
    return r


def test_list_locations_sends_coordinates_and_radius():
    payload = {"meta": {"found": 1}, "results": [{"id": 42, "name": "X"}]}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok_response(payload)
        params = OpenAqListLocationsParams(coordinates="37.77,-122.41", radius=5000)
        result = fetch_openaq_list_locations(params)
        assert result["results"][0]["id"] == 42
        sent = mock_get.call_args[1]["params"]
        assert sent["coordinates"] == "37.77,-122.41"
        assert sent["radius"] == 5000


def test_list_locations_validates_radius_bounds():
    with pytest.raises(Exception):
        OpenAqListLocationsParams(radius=0)
    with pytest.raises(Exception):
        OpenAqListLocationsParams(radius=25001)


def test_location_latest_path_param():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok_response({"results": [{"value": 12.3}]})
        result = fetch_openaq_location_latest(
            OpenAqLocationLatestParams(location_id=42)
        )
        assert result["results"][0]["value"] == 12.3
        assert "/locations/42/latest" in mock_get.call_args[0][0]


def test_location_latest_rejects_invalid_id():
    with pytest.raises(Exception):
        OpenAqLocationLatestParams(location_id=0)


def test_list_parameters():
    payload = {"results": [{"id": 2, "name": "pm25", "units": "µg/m³"}]}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok_response(payload)
        result = fetch_openaq_list_parameters(OpenAqListParametersParams())
        assert result["results"][0]["name"] == "pm25"


def test_auth_header_sent_when_env_set(monkeypatch):
    monkeypatch.setenv("OPENAQ_API_KEY", "secret-token")
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok_response({"results": []})
        fetch_openaq_list_locations(OpenAqListLocationsParams())
        sent_headers = mock_get.call_args[1]["headers"]
        assert sent_headers["X-API-Key"] == "secret-token"


@pytest.mark.anyio
async def test_handle_list_locations():
    payload = {"results": [{"id": 1, "name": "Test Station"}]}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok_response(payload)
        result = await handle_openaq_list_locations({"iso": "NL"})
        assert "Test Station" in result[0].text


@pytest.mark.anyio
async def test_handle_translates_404_via_provider_kwarg():
    from meta_data_mcp.errors import NotFoundError

    req = httpx.Request("GET", "https://api.openaq.org/v3/locations")
    resp = httpx.Response(status_code=404, request=req)
    status_err = httpx.HTTPStatusError("not found", request=req, response=resp)

    with patch("httpx.get") as mock_get:
        mock_get.return_value.raise_for_status = Mock(side_effect=status_err)
        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = {}

        with pytest.raises(NotFoundError) as exc_info:
            await handle_openaq_list_locations({"iso": "ZZ"})
        assert exc_info.value.provider == "global-openaq"
