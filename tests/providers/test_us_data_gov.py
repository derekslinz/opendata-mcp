import pytest
from unittest.mock import patch, Mock
from odmcp.providers.us_data_gov import (
    list_datagov_datasets,
    DataGovListDatasetsParams,
    handle_datagov_list_datasets,
    fetch_datagov_dataset,
    DataGovGetDatasetParams,
    handle_datagov_get_dataset,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_search_response():
    return {
        "success": True,
        "result": {
            "count": 1,
            "results": [
                {
                    "id": "consumer-complaint-database",
                    "name": "consumer-complaint-database",
                    "title": "Consumer Complaint Database",
                    "organization": {"title": "Consumer Financial Protection Bureau"},
                    "notes": "A collection of complaints received by the CFPB.",
                }
            ],
        },
    }


@pytest.fixture
def mock_show_response():
    return {
        "success": True,
        "result": {
            "id": "consumer-complaint-database",
            "name": "consumer-complaint-database",
            "title": "Consumer Complaint Database",
            "resources": [
                {
                    "id": "resource-123",
                    "name": "CSV Data",
                    "format": "CSV",
                    "url": "https://example.com/data.csv",
                }
            ],
        },
    }


def test_list_datagov_datasets(mock_search_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_search_response
        mock_get.return_value.raise_for_status = Mock()

        params = DataGovListDatasetsParams(search="complaints")
        result = list_datagov_datasets(params)
        assert result["count"] == 1
        assert result["results"][0]["name"] == "consumer-complaint-database"
        mock_get.assert_called_once_with(
            "https://catalog.data.gov/api/3/action/package_search",
            params={"q": "complaints", "rows": 20, "start": 0},
            timeout=10.0,
        )


@pytest.mark.anyio
async def test_handle_datagov_list_datasets(mock_search_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_search_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_datagov_list_datasets({"search": "complaints"})
        assert len(result) == 1
        assert "Consumer Complaint Database" in result[0].text


def test_fetch_datagov_dataset(mock_show_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_show_response
        mock_get.return_value.raise_for_status = Mock()

        params = DataGovGetDatasetParams(dataset_id="consumer-complaint-database")
        result = fetch_datagov_dataset(params)
        assert result["title"] == "Consumer Complaint Database"
        assert len(result["resources"]) == 1
        mock_get.assert_called_once_with(
            "https://catalog.data.gov/api/3/action/package_show",
            params={"id": "consumer-complaint-database"},
            timeout=10.0,
        )


@pytest.mark.anyio
async def test_handle_datagov_get_dataset(mock_show_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_show_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_datagov_get_dataset(
            {"dataset_id": "consumer-complaint-database"}
        )
        assert len(result) == 1
        assert "CSV Data" in result[0].text


def test_api_error_handling():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": False,
            "error": "Not Found",
        }
        mock_get.return_value.raise_for_status = Mock()

        params = DataGovGetDatasetParams(dataset_id="invalid")
        with pytest.raises(ValueError, match="API Error: Not Found"):
            fetch_datagov_dataset(params)
