import pytest
from unittest.mock import patch, Mock

# We'll test NASA, DB, and DOE ARM
from odmcp.providers.us_nasa import handle_get_apod, handle_get_asteroids
from odmcp.providers.de_db import handle_list_stations
from odmcp.providers.us_doe_arm import handle_search_lasso


@pytest.fixture
def anyio_backend():
    return "asyncio"


# NASA Tests
@pytest.mark.anyio
async def test_nasa_get_apod():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "title": "Test Image",
            "url": "http://test.jpg",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_apod()
        assert len(result) == 1
        assert "Test Image" in result[0].text


@pytest.mark.anyio
async def test_nasa_get_asteroids():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"element_count": 5}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_asteroids(
            {"start_date": "2024-01-01", "end_date": "2024-01-07"}
        )
        assert "element_count" in result[0].text


# DB Tests
@pytest.mark.anyio
async def test_db_list_stations():
    # DB provider is currently mocked/instructional
    result = await handle_list_stations({"search": "Berlin"})
    assert "Berlin Hbf" in result[0].text


# DOE ARM Tests
@pytest.mark.anyio
async def test_arm_search_lasso():
    # ARM provider is currently mocked/instructional
    result = await handle_search_lasso({"site": "sgp"})
    assert "LASSO" in result[0].text
