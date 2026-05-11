import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.us_noaa_ncei import (
    handle_ncei_get_daily_summaries,
    handle_ncei_get_global_summary,
    handle_ncei_search_stations,
    handle_ncei_list_datasets,
    handle_ncei_get_station_meta,
    handle_ncei_get_precipitation,
    handle_ncei_get_temperature,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_ncei_daily_summaries_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"STATION": "USW00014739", "DATE": "2024-01-01", "TMAX": 12, "TMIN": 3}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ncei_get_daily_summaries(
            {
                "stations": "USW00014739",
                "startDate": "2024-01-01",
                "endDate": "2024-01-01",
                "dataTypes": "TMAX,TMIN",
            }
        )
        assert "USW00014739" in result[0].text
        assert "TMAX" in result[0].text


@pytest.mark.anyio
async def test_ncei_daily_summaries_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("NCEI down")

        with pytest.raises(httpx.HTTPError):
            await handle_ncei_get_daily_summaries(
                {
                    "stations": "USW00014739",
                    "startDate": "2024-01-01",
                    "endDate": "2024-01-01",
                }
            )


@pytest.mark.anyio
async def test_ncei_global_summary_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"STATION": "72509014739", "DATE": "2024-01-01", "TEMP": "30.4"}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ncei_get_global_summary(
            {
                "stations": "72509014739",
                "startDate": "2024-01-01",
                "endDate": "2024-01-01",
            }
        )
        assert "72509014739" in result[0].text


@pytest.mark.anyio
async def test_ncei_search_stations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [{"id": "USW00014739", "name": "Boston Logan"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ncei_search_stations(
            {"boundingBox": "42.5,-71.5,42.0,-70.5", "limit": 5}
        )
        assert "Boston Logan" in result[0].text


@pytest.mark.anyio
async def test_ncei_list_datasets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 2,
            "results": [
                {"id": "daily-summaries"},
                {"id": "global-summary-of-the-day"},
            ],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ncei_list_datasets({"limit": 10})
        assert "daily-summaries" in result[0].text


@pytest.mark.anyio
async def test_ncei_get_station_meta_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"id": "USW00014739", "name": "Boston Logan Intl"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ncei_get_station_meta({"stations": "USW00014739"})
        assert "Boston Logan Intl" in result[0].text


@pytest.mark.anyio
async def test_ncei_get_precipitation_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"STATION": "USW00014739", "DATE": "2024-01-01", "PRCP": 0.42}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ncei_get_precipitation(
            {
                "stations": "USW00014739",
                "startDate": "2024-01-01",
                "endDate": "2024-01-01",
            }
        )
        assert "PRCP" in result[0].text
        assert "0.42" in result[0].text


@pytest.mark.anyio
async def test_ncei_get_temperature_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"STATION": "USW00014739", "DATE": "2024-01-01", "TMAX": 12, "TMIN": 3}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ncei_get_temperature(
            {
                "stations": "USW00014739",
                "startDate": "2024-01-01",
                "endDate": "2024-01-01",
            }
        )
        assert "TMAX" in result[0].text
        assert "TMIN" in result[0].text
