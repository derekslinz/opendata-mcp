import pytest
from unittest.mock import patch, Mock
import httpx
from meta_data_mcp.providers.de_db import handle_list_stations, handle_get_timetable


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_db_list_stations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {"id": "8011160", "name": "Berlin Hbf"}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_stations({"search": "Berlin"})
        assert len(result) == 1
        assert "Berlin Hbf" in result[0].text
        mock_get.assert_called_once()


@pytest.mark.anyio
async def test_db_list_stations_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(httpx.HTTPError):
            await handle_list_stations({"search": "Berlin"})


@pytest.mark.anyio
async def test_db_get_timetable_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "tripId": "123",
                "direction": "Munich",
                "plannedWhen": "2024-01-01T12:00:00Z",
                "line": {"name": "ICE 1"},
            }
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_timetable({"station_id": "8011160"})
        assert len(result) == 1
        assert "ICE 1" in result[0].text
        assert "Munich" in result[0].text


@pytest.mark.anyio
async def test_db_get_timetable_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Timeout")

        with pytest.raises(httpx.HTTPError):
            await handle_get_timetable({"station_id": "8011160"})
