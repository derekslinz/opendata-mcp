import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.us_fred import (
    handle_search_series,
    handle_get_series,
    handle_get_series_observations,
    handle_list_categories,
    handle_get_category,
    handle_list_releases,
    handle_get_release,
    handle_list_sources,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _set_fred_key(monkeypatch):
    """Set a fake FRED_API_KEY for all tests in this module.

    Individual tests that want to exercise the missing-key path can
    delete the env var inside their body.
    """
    monkeypatch.setenv("FRED_API_KEY", "test_api_key")


@pytest.mark.anyio
async def test_fred_missing_key_raises(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(ValueError):
        await handle_search_series({"search_text": "gdp"})


@pytest.mark.anyio
async def test_fred_search_series_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "seriess": [{"id": "GDP", "title": "Gross Domestic Product"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_series({"search_text": "gdp"})
        assert "Gross Domestic Product" in result[0].text


@pytest.mark.anyio
async def test_fred_search_series_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_search_series({"search_text": "gdp"})


@pytest.mark.anyio
async def test_fred_search_series_missing_arg():
    with pytest.raises(ValueError):
        await handle_search_series({})


@pytest.mark.anyio
async def test_fred_get_series_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "seriess": [{"id": "GDP", "title": "Gross Domestic Product"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_series({"series_id": "GDP"})
        assert "Gross Domestic Product" in result[0].text


@pytest.mark.anyio
async def test_fred_get_series_observations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "observations": [
                {"date": "2020-01-01", "value": "21747.394"},
                {"date": "2021-01-01", "value": "23315.080"},
            ]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_series_observations(
            {
                "series_id": "GDP",
                "observation_start": "2020-01-01",
                "observation_end": "2021-12-31",
                "limit": 10,
            }
        )
        assert "21747.394" in result[0].text
        assert "23315.080" in result[0].text


@pytest.mark.anyio
async def test_fred_get_series_observations_missing_arg():
    with pytest.raises(ValueError):
        await handle_get_series_observations({})


@pytest.mark.anyio
async def test_fred_list_categories_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "categories": [{"id": 32991, "name": "Money, Banking, & Finance"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_categories()
        assert "Money, Banking, & Finance" in result[0].text


@pytest.mark.anyio
async def test_fred_get_category_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "categories": [{"id": 125, "name": "Trade Balance"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_category({"category_id": 125})
        assert "Trade Balance" in result[0].text


@pytest.mark.anyio
async def test_fred_get_category_missing_arg():
    with pytest.raises(ValueError):
        await handle_get_category({})


@pytest.mark.anyio
async def test_fred_list_releases_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "releases": [{"id": 53, "name": "Gross Domestic Product"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_releases({"limit": 5})
        assert "Gross Domestic Product" in result[0].text


@pytest.mark.anyio
async def test_fred_get_release_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "releases": [{"id": 53, "name": "Gross Domestic Product"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_release({"release_id": 53})
        assert "Gross Domestic Product" in result[0].text


@pytest.mark.anyio
async def test_fred_get_release_missing_arg():
    with pytest.raises(ValueError):
        await handle_get_release({})


@pytest.mark.anyio
async def test_fred_list_sources_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "sources": [
                {"id": 1, "name": "Board of Governors of the Federal Reserve System"}
            ]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_sources()
        assert "Board of Governors" in result[0].text
