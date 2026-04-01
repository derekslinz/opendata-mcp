import pytest
from unittest.mock import patch, Mock
from odmcp.providers.global_open_meteo import (
    fetch_weather_forecast,
    WeatherForecastParams,
    handle_get_forecast,
    fetch_historical_weather,
    HistoricalWeatherParams,
    handle_get_historical_weather,
    fetch_air_quality,
    AirQualityParams,
    handle_get_air_quality,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_forecast_response():
    return {
        "latitude": 52.52,
        "longitude": 13.41,
        "hourly": {"time": ["2023-01-01T00:00"], "temperature_2m": [10.5]},
        "daily": {"time": ["2023-01-01"], "temperature_2m_max": [15.0]},
    }


@pytest.fixture
def mock_historical_response():
    return {
        "latitude": 52.52,
        "longitude": 13.41,
        "daily": {"time": ["2020-01-01"], "temperature_2m_max": [5.0]},
    }


@pytest.fixture
def mock_air_quality_response():
    return {
        "latitude": 52.52,
        "longitude": 13.41,
        "hourly": {"time": ["2023-01-01T00:00"], "pm2_5": [5.0]},
    }


def test_fetch_weather_forecast(mock_forecast_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_forecast_response
        mock_get.return_value.raise_for_status = Mock()

        params = WeatherForecastParams(latitude=52.52, longitude=13.41)
        response = fetch_weather_forecast(params)
        assert response["latitude"] == 52.52
        assert response["hourly"]["temperature_2m"][0] == 10.5


@pytest.mark.anyio
async def test_handle_get_forecast(mock_forecast_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_forecast_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_forecast({"latitude": 52.52, "longitude": 13.41})
        assert len(result) == 1
        assert "10.5" in result[0].text


def test_fetch_historical_weather(mock_historical_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_historical_response
        mock_get.return_value.raise_for_status = Mock()

        params = HistoricalWeatherParams(
            latitude=52.52,
            longitude=13.41,
            start_date="2020-01-01",
            end_date="2020-01-01",
        )
        response = fetch_historical_weather(params)
        assert response["daily"]["temperature_2m_max"][0] == 5.0


@pytest.mark.anyio
async def test_handle_get_historical_weather(mock_historical_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_historical_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_historical_weather(
            {
                "latitude": 52.52,
                "longitude": 13.41,
                "start_date": "2020-01-01",
                "end_date": "2020-01-01",
            }
        )
        assert len(result) == 1
        assert "5.0" in result[0].text


def test_fetch_air_quality(mock_air_quality_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_air_quality_response
        mock_get.return_value.raise_for_status = Mock()

        params = AirQualityParams(latitude=52.52, longitude=13.41)
        response = fetch_air_quality(params)
        assert response["hourly"]["pm2_5"][0] == 5.0


@pytest.mark.anyio
async def test_handle_get_air_quality(mock_air_quality_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_air_quality_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_air_quality({"latitude": 52.52, "longitude": 13.41})
        assert len(result) == 1
        assert "5.0" in result[0].text
