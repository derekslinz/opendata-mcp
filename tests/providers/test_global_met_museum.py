import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_met_museum import (
    handle_met_list_objects,
    handle_met_get_object,
    handle_met_search,
    handle_met_list_departments,
    handle_met_search_by_artist,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_met_list_objects_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total": 2,
            "objectIDs": [123, 456],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_met_list_objects({"departmentIds": "11"})
        assert "123" in result[0].text
        assert "objectIDs" in result[0].text


@pytest.mark.anyio
async def test_met_list_objects_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Met API down")

        with pytest.raises(httpx.HTTPError):
            await handle_met_list_objects({})


@pytest.mark.anyio
async def test_met_get_object_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "objectID": 436535,
            "title": "Wheat Field with Cypresses",
            "artistDisplayName": "Vincent van Gogh",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_met_get_object({"objectID": 436535})
        assert "Wheat Field with Cypresses" in result[0].text
        assert "Vincent van Gogh" in result[0].text


@pytest.mark.anyio
async def test_met_get_object_requires_id():
    with pytest.raises(ValueError):
        await handle_met_get_object({})


@pytest.mark.anyio
async def test_met_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total": 1,
            "objectIDs": [436535],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_met_search(
            {"q": "sunflowers", "hasImages": True, "departmentId": 11}
        )
        assert "436535" in result[0].text


@pytest.mark.anyio
async def test_met_list_departments_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "departments": [
                {"departmentId": 1, "displayName": "American Decorative Arts"}
            ]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_met_list_departments({})
        assert "American Decorative Arts" in result[0].text


@pytest.mark.anyio
async def test_met_search_by_artist_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total": 5,
            "objectIDs": [1, 2, 3, 4, 5],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_met_search_by_artist({"q": "Van Gogh"})
        assert "objectIDs" in result[0].text
