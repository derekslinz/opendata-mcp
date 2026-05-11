import json
import pytest
from unittest.mock import patch, Mock
from opendata_mcp.providers.us_data_gov import (
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
        "after": "next-cursor",
        "results": [
            {
                "identifier": "CCDB",
                "slug": "consumer-complaint-database",
                "title": "Consumer Complaint Database",
                "publisher": "Consumer Financial Protection Bureau",
                "organization": {"name": "Consumer Financial Protection Bureau"},
                "description": "A collection of complaints received by the CFPB.",
                "harvest_record": "https://catalog.data.gov/harvest_record/abc",
            }
        ],
    }


@pytest.fixture
def mock_show_response():
    return {
        "results": [
            {
                "identifier": "CCDB",
                "slug": "consumer-complaint-database",
                "title": "Consumer Complaint Database",
                "dcat": {
                    "identifier": "CCDB",
                    "title": "Consumer Complaint Database",
                    "distribution": [
                        {
                            "title": "CSV Data",
                            "format": "CSV",
                            "accessURL": "https://example.com/data.csv",
                        }
                    ],
                },
            }
        ],
    }


def test_list_datagov_datasets(mock_search_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_search_response
        mock_get.return_value.raise_for_status = Mock()

        params = DataGovListDatasetsParams(search="complaints")
        result = list_datagov_datasets(params)
        assert result["after"] == "next-cursor"
        assert result["results"][0]["slug"] == "consumer-complaint-database"
        mock_get.assert_called_once_with(
            "https://catalog.data.gov/search",
            params={"q": "complaints", "per_page": 20},
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
        payload = json.loads(result[0].text)
        assert payload["count"] == 1
        assert payload["datasets"][0]["title"] == "Consumer Complaint Database"


def test_fetch_datagov_dataset(mock_show_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_show_response
        mock_get.return_value.raise_for_status = Mock()

        params = DataGovGetDatasetParams(dataset_id="consumer-complaint-database")
        result = fetch_datagov_dataset(params)
        assert result["title"] == "Consumer Complaint Database"
        assert len(result["dcat"]["distribution"]) == 1
        mock_get.assert_called_once_with(
            "https://catalog.data.gov/search",
            params={"q": "consumer-complaint-database", "per_page": 25},
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
        payload = json.loads(result[0].text)
        assert payload["dcat"]["distribution"][0]["title"] == "CSV Data"


def test_api_error_handling():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.raise_for_status = Mock()

        params = DataGovGetDatasetParams(dataset_id="invalid")
        with pytest.raises(ValueError, match="API Error: dataset not found: invalid"):
            fetch_datagov_dataset(params)
