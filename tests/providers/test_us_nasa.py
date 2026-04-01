import pytest
from unittest.mock import patch, Mock
import httpx
from odmcp.providers.us_nasa import (
    handle_get_apod,
    handle_get_asteroids,
    handle_get_mars_photos,
    handle_get_ace_data,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_nasa_get_apod_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "title": "Starry Night",
            "url": "http://example.com/nasa.jpg",
            "explanation": "Testing context",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_apod()
        assert len(result) == 1
        assert "Starry Night" in result[0].text


@pytest.mark.anyio
async def test_nasa_get_apod_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        result = await handle_get_apod()
        assert "Error reaching NASA APOD API" in result[0].text


@pytest.mark.anyio
async def test_nasa_get_asteroids_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"element_count": 42}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_asteroids(
            {"start_date": "2024-01-01", "end_date": "2024-01-07"}
        )
        assert "element_count" in result[0].text
        assert "42" in result[0].text


@pytest.mark.anyio
async def test_nasa_get_mars_photos_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "photos": [{"img_src": "mars_pic.jpg"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_mars_photos(
            {"rover": "curiosity", "earth_date": "2024-01-01"}
        )
        assert "mars_pic.jpg" in result[0].text


@pytest.mark.anyio
async def test_nasa_get_ace_data_success():
    # Fixed ACE tool hitting SWPC API
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            ["time_tag", "density"],
            ["2024-04-01 12:00:00", "5.0"],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_ace_data(
            {"start_date": "2024-04-01", "end_date": "2024-04-01"}
        )
        assert "density" in result[0].text
        assert "5.0" in result[0].text


@pytest.mark.anyio
async def test_nasa_get_ace_data_no_results():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [["time_tag", "density"]]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_ace_data(
            {"start_date": "2099-01-01", "end_date": "2099-01-01"}
        )
        assert "No data found" in result[0].text
