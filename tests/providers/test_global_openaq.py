import pytest
from unittest.mock import patch, Mock
import httpx


@pytest.fixture(autouse=True)
def openaq_api_key(monkeypatch):
    """Ensure OPENAQ_API_KEY is set for every test in this module."""
    monkeypatch.setenv("OPENAQ_API_KEY", "test-key")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _import_handlers():
    from opendata_mcp.providers.global_openaq import (
        handle_list_parameters,
        handle_list_locations,
        handle_get_location,
        handle_get_latest,
        handle_list_countries,
        handle_list_sensors,
    )

    return (
        handle_list_parameters,
        handle_list_locations,
        handle_get_location,
        handle_get_latest,
        handle_list_countries,
        handle_list_sensors,
    )


@pytest.mark.anyio
async def test_openaq_list_parameters_success():
    handle_list_parameters, *_ = _import_handlers()
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"id": 2, "name": "pm25"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_parameters({"limit": 5})
        assert len(result) == 1
        assert "pm25" in result[0].text


@pytest.mark.anyio
async def test_openaq_list_locations_success():
    _, handle_list_locations, *_ = _import_handlers()
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"id": 100, "name": "Loc1"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_locations(
            {"country": "US", "parameters_id": 2, "limit": 1, "page": 1}
        )
        assert "Loc1" in result[0].text


@pytest.mark.anyio
async def test_openaq_get_location_success():
    _, _, handle_get_location, *_ = _import_handlers()
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"id": 42, "city": "Boston"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_location({"locations_id": 42})
        assert "Boston" in result[0].text


@pytest.mark.anyio
async def test_openaq_get_latest_success():
    _, _, _, handle_get_latest, *_ = _import_handlers()
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": [{"value": 12.5}]}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_latest({"locations_id": 42})
        assert "12.5" in result[0].text


@pytest.mark.anyio
async def test_openaq_list_countries_success():
    _, _, _, _, handle_list_countries, _ = _import_handlers()
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": [{"code": "US"}]}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_countries({"limit": 10})
        assert "US" in result[0].text


@pytest.mark.anyio
async def test_openaq_list_sensors_success():
    *_, handle_list_sensors = _import_handlers()
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"id": 9001, "parameter": "no2"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_sensors({"locations_id": 42})
        assert "no2" in result[0].text


@pytest.mark.anyio
async def test_openaq_missing_api_key_raises(monkeypatch):
    handle_list_parameters, *_ = _import_handlers()
    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAQ_API_KEY"):
        await handle_list_parameters({})


@pytest.mark.anyio
async def test_openaq_http_error_propagates():
    handle_list_parameters, *_ = _import_handlers()
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")
        with pytest.raises(httpx.HTTPError):
            await handle_list_parameters({})
