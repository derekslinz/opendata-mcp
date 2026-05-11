import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.sg_data_gov import (
    handle_sg_datagov_list_datasets,
    handle_sg_datagov_get_dataset,
    handle_sg_datagov_list_collections,
    handle_sg_datagov_get_collection,
    handle_sg_datagov_poll_download,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_sg_datagov_list_datasets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "datasets": [{"datasetId": "d_abc", "name": "Resale Flat Prices"}],
                "pages": {"total": 1},
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_sg_datagov_list_datasets({"page": 1, "per_page": 10})
        assert "Resale Flat Prices" in result[0].text


@pytest.mark.anyio
async def test_sg_datagov_list_datasets_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("SG outage")

        with pytest.raises(httpx.HTTPError):
            await handle_sg_datagov_list_datasets({})


@pytest.mark.anyio
async def test_sg_datagov_get_dataset_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "datasetId": "d_abc",
                "name": "Resale Flat Prices",
                "format": "CSV",
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_sg_datagov_get_dataset({"datasetId": "d_abc"})
        assert "Resale Flat Prices" in result[0].text


@pytest.mark.anyio
async def test_sg_datagov_list_collections_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "collections": [
                    {"collectionId": "c_001", "name": "Housing Collection"}
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_sg_datagov_list_collections({"page": 1})
        assert "Housing Collection" in result[0].text


@pytest.mark.anyio
async def test_sg_datagov_get_collection_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "collectionId": "c_001",
                "name": "Housing Collection",
                "description": "HDB housing datasets",
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_sg_datagov_get_collection({"collectionId": "c_001"})
        assert "Housing Collection" in result[0].text


@pytest.mark.anyio
async def test_sg_datagov_poll_download_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {"status": "READY", "url": "https://signed.example/preview"},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_sg_datagov_poll_download({"datasetId": "d_abc"})
        assert "READY" in result[0].text
