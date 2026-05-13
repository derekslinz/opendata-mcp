import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.us_usgs_earthquake import (
    handle_usgs_eq_query,
    handle_usgs_eq_count,
    handle_usgs_eq_feed_significant_day,
    handle_usgs_eq_feed_significant_week,
    handle_usgs_eq_feed_all_day,
    handle_usgs_eq_feed_all_week,
    handle_usgs_eq_feed_m45_week,
    handle_usgs_eq_application_version,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_usgs_eq_query_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "type": "FeatureCollection",
            "metadata": {"count": 2},
            "features": [
                {"id": "us1", "properties": {"mag": 5.1, "place": "Off the coast"}},
                {"id": "us2", "properties": {"mag": 4.7, "place": "Alaska"}},
            ],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_usgs_eq_query(
            {"starttime": "2024-01-01", "endtime": "2024-01-02", "minmagnitude": 4.0}
        )
        assert len(result) == 1
        assert "FeatureCollection" in result[0].text
        assert "Alaska" in result[0].text


@pytest.mark.anyio
async def test_usgs_eq_query_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("USGS unavailable")

        with pytest.raises(httpx.HTTPError):
            await handle_usgs_eq_query({"starttime": "2024-01-01"})


@pytest.mark.anyio
async def test_usgs_eq_count_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"count": 1234}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_usgs_eq_count(
            {"starttime": "2024-01-01", "endtime": "2024-01-02"}
        )
        assert "1234" in result[0].text


@pytest.mark.anyio
async def test_usgs_eq_feed_significant_day_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "type": "FeatureCollection",
            "metadata": {"title": "Significant Earthquakes, Past Day"},
            "features": [],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_usgs_eq_feed_significant_day()
        assert "Significant Earthquakes" in result[0].text


@pytest.mark.anyio
async def test_usgs_eq_feed_significant_week_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "type": "FeatureCollection",
            "metadata": {"title": "Significant Earthquakes, Past Week"},
            "features": [],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_usgs_eq_feed_significant_week()
        assert "Past Week" in result[0].text


@pytest.mark.anyio
async def test_usgs_eq_feed_all_day_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "type": "FeatureCollection",
            "metadata": {"title": "All Earthquakes, Past Day"},
            "features": [{"id": "eq-1"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_usgs_eq_feed_all_day()
        assert "eq-1" in result[0].text


@pytest.mark.anyio
async def test_usgs_eq_feed_all_week_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "type": "FeatureCollection",
            "metadata": {"title": "All Earthquakes, Past Week"},
            "features": [],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_usgs_eq_feed_all_week()
        assert "All Earthquakes" in result[0].text


@pytest.mark.anyio
async def test_usgs_eq_feed_m45_week_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "type": "FeatureCollection",
            "metadata": {"title": "M4.5+ Earthquakes, Past Week"},
            "features": [],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_usgs_eq_feed_m45_week()
        assert "M4.5+" in result[0].text


@pytest.mark.anyio
async def test_usgs_eq_application_version_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = "1.14.1"
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_usgs_eq_application_version()
        assert "1.14.1" in result[0].text
