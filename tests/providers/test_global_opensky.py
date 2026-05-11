import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_opensky import (
    handle_get_states_all,
    handle_get_states_by_aircraft,
    handle_get_flights_aircraft,
    handle_get_flights_arrival,
    handle_get_flights_departure,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_opensky_states_all_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "time": 1700000000,
            "states": [["abc123", "AAL123"]],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_states_all(
            {"lamin": 40.0, "lomin": -75.0, "lamax": 41.0, "lomax": -74.0}
        )
        assert "abc123" in result[0].text


@pytest.mark.anyio
async def test_opensky_states_all_no_bbox():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"time": 1, "states": []}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_states_all({})
        assert "states" in result[0].text


@pytest.mark.anyio
async def test_opensky_states_by_aircraft_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "time": 1,
            "states": [["deadbe", "TEST1"]],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_states_by_aircraft({"icao24": "deadbe"})
        assert "TEST1" in result[0].text


@pytest.mark.anyio
async def test_opensky_states_by_aircraft_missing_icao():
    with pytest.raises(ValueError, match="icao24 is required"):
        await handle_get_states_by_aircraft({})


@pytest.mark.anyio
async def test_opensky_flights_aircraft_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"icao24": "deadbe", "firstSeen": 1, "lastSeen": 2}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_flights_aircraft(
            {"icao24": "deadbe", "begin": 1, "end": 2}
        )
        assert "deadbe" in result[0].text


@pytest.mark.anyio
async def test_opensky_flights_arrival_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"estArrivalAirport": "EDDF", "icao24": "abc"}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_flights_arrival(
            {"airport": "EDDF", "begin": 100, "end": 200}
        )
        assert "EDDF" in result[0].text


@pytest.mark.anyio
async def test_opensky_flights_departure_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"estDepartureAirport": "KJFK", "icao24": "xyz"}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_flights_departure(
            {"airport": "KJFK", "begin": 100, "end": 200}
        )
        assert "KJFK" in result[0].text


@pytest.mark.anyio
async def test_opensky_flights_arrival_missing_args():
    with pytest.raises(ValueError, match="airport, begin, and end are required"):
        await handle_get_flights_arrival({"airport": "EDDF"})


@pytest.mark.anyio
async def test_opensky_http_error_propagates():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")
        with pytest.raises(httpx.HTTPError):
            await handle_get_states_all({})
