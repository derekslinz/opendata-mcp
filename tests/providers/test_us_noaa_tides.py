import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.us_noaa_tides import (
    handle_noaa_tides_water_level,
    handle_noaa_tides_predictions,
    handle_noaa_tides_air_temperature,
    handle_noaa_tides_water_temperature,
    handle_noaa_tides_wind,
    handle_noaa_tides_currents,
    handle_noaa_tides_hourly_height,
    handle_noaa_tides_station_metadata,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_noaa_tides_water_level_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "metadata": {"id": "9447130", "name": "Seattle"},
            "data": [{"t": "2024-01-01 00:00", "v": "1.234"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_noaa_tides_water_level({"station": "9447130"})
        assert "Seattle" in result[0].text
        assert "1.234" in result[0].text


@pytest.mark.anyio
async def test_noaa_tides_water_level_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("CO-OPS unavailable")

        with pytest.raises(httpx.HTTPError):
            await handle_noaa_tides_water_level({"station": "9447130"})


@pytest.mark.anyio
async def test_noaa_tides_predictions_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "predictions": [{"t": "2024-01-01 00:00", "v": "2.0", "type": "H"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_noaa_tides_predictions(
            {
                "station": "9447130",
                "begin_date": "20240101",
                "end_date": "20240102",
                "interval": "hilo",
            }
        )
        assert "predictions" in result[0].text


@pytest.mark.anyio
async def test_noaa_tides_air_temperature_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"t": "2024-01-01 00:00", "v": "5.6"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_noaa_tides_air_temperature({"station": "9447130"})
        assert "5.6" in result[0].text


@pytest.mark.anyio
async def test_noaa_tides_water_temperature_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"t": "2024-01-01 00:00", "v": "9.1"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_noaa_tides_water_temperature({"station": "9447130"})
        assert "9.1" in result[0].text


@pytest.mark.anyio
async def test_noaa_tides_wind_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"t": "2024-01-01 00:00", "s": "5.5", "d": "180"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_noaa_tides_wind({"station": "9447130"})
        assert "180" in result[0].text


@pytest.mark.anyio
async def test_noaa_tides_currents_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"t": "2024-01-01 00:00", "s": "0.42", "d": "90"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_noaa_tides_currents({"station": "PUG1515"})
        assert "0.42" in result[0].text


@pytest.mark.anyio
async def test_noaa_tides_hourly_height_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"t": "2024-01-01 00:00", "v": "1.10"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_noaa_tides_hourly_height({"station": "9447130"})
        assert "1.10" in result[0].text


@pytest.mark.anyio
async def test_noaa_tides_station_metadata_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "stations": [{"id": "9447130", "name": "Seattle"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_noaa_tides_station_metadata({"type": "tidepredictions"})
        assert "Seattle" in result[0].text
