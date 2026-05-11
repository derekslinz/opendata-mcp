"""
Global Weather Data Provider (Open-Meteo)

This module provides interfaces to access the Open-Meteo weather API.
Open-Meteo is an open-source weather API that aggregates data from
national meteorological services (ECMWF, NOAA, DWD, MeteoFrance, etc.).

Features:
- Global weather forecasts (hourly/daily)
- Historical weather data (80+ years archive)
- Air quality data (PM2.5, NO2, O3, Dust, etc.)

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
from typing import Any, List, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import to_json_text

# Initialize logging
log = logging.getLogger(__name__)

# Constants
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# Weather Forecast
###################


class WeatherForecastParams(BaseModel):
    """Parameters for getting a weather forecast."""

    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude of the location"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude of the location"
    )
    hourly: str = Field(
        default="temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        description="Comma-separated hourly variables to return",
    )
    daily: str = Field(
        default="weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        description="Comma-separated daily variables to return",
    )
    forecast_days: int = Field(
        default=7, ge=1, le=16, description="Number of forecast days (1-16)"
    )


def fetch_weather_forecast(params: WeatherForecastParams) -> dict:
    """Fetch forecast data from Open-Meteo."""
    query_params = {
        "latitude": params.latitude,
        "longitude": params.longitude,
        "hourly": params.hourly,
        "daily": params.daily,
        "forecast_days": params.forecast_days,
        "timezone": "auto",
    }
    response = httpx.get(FORECAST_URL, params=query_params, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def handle_get_forecast(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the weather-get-forecast tool call."""
    try:
        params = WeatherForecastParams(**(arguments or {}))
        data = fetch_weather_forecast(params)
        return [types.TextContent(type="text", text=to_json_text(data))]
    except Exception as e:
        log.error(f"Error fetching weather forecast: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="weather-get-forecast",
        description="Get current and upcoming weather forecast for a specific location.",
        inputSchema=WeatherForecastParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["weather-get-forecast"] = handle_get_forecast

###################
# Historical Weather
###################


class HistoricalWeatherParams(BaseModel):
    """Parameters for getting historical weather data."""

    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude of the location"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude of the location"
    )
    start_date: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date (YYYY-MM-DD)"
    )
    end_date: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date (YYYY-MM-DD)"
    )
    daily: str = Field(
        default="temperature_2m_max,temperature_2m_min,precipitation_sum",
        description="Comma-separated daily variables to return",
    )


def fetch_historical_weather(params: HistoricalWeatherParams) -> dict:
    """Fetch historical data from Open-Meteo Archive API."""
    query_params = {
        "latitude": params.latitude,
        "longitude": params.longitude,
        "start_date": params.start_date,
        "end_date": params.end_date,
        "daily": params.daily,
        "timezone": "auto",
    }
    response = httpx.get(ARCHIVE_URL, params=query_params, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def handle_get_historical_weather(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the weather-get-historical tool call."""
    try:
        params = HistoricalWeatherParams(**(arguments or {}))
        data = fetch_historical_weather(params)
        return [types.TextContent(type="text", text=to_json_text(data))]
    except Exception as e:
        log.error(f"Error fetching historical weather: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="weather-get-historical",
        description="Get historical weather records for a specific location and date range.",
        inputSchema=HistoricalWeatherParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["weather-get-historical"] = handle_get_historical_weather

###################
# Air Quality
###################


class AirQualityParams(BaseModel):
    """Parameters for getting air quality data."""

    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitude of the location"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude of the location"
    )
    hourly: str = Field(
        default="pm2_5,pm10,nitrogen_dioxide,ozone,dust",
        description="Comma-separated hourly variables to return",
    )


def fetch_air_quality(params: AirQualityParams) -> dict:
    """Fetch air quality data from Open-Meteo."""
    query_params = {
        "latitude": params.latitude,
        "longitude": params.longitude,
        "hourly": params.hourly,
        "timezone": "auto",
    }
    response = httpx.get(AIR_QUALITY_URL, params=query_params, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def handle_get_air_quality(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the weather-get-air-quality tool call."""
    try:
        params = AirQualityParams(**(arguments or {}))
        data = fetch_air_quality(params)
        return [types.TextContent(type="text", text=to_json_text(data))]
    except Exception as e:
        log.error(f"Error fetching air quality: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="weather-get-air-quality",
        description="Get air quality data (PM2.5, ozone, dust, etc.) for a specific location.",
        inputSchema=AirQualityParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["weather-get-air-quality"] = handle_get_air_quality


async def main(transport: str = "stdio", port: int = 8000):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-open-meteo", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
