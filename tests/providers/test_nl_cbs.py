import pytest
from unittest.mock import patch, Mock
from odmcp.providers.nl_cbs import (
    fetch_cbs_data,
    CBSDataParams,
    handle_cbs_data,
    fetch_cbs_metadata,
    CBSMetadataParams,
    handle_cbs_metadata,
    list_cbs_tables,
    CBSListTablesParams,
    handle_cbs_list_tables,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_cbs_data_response():
    return {
        "value": [
            {
                "ID": 0,
                "Periods": "2023MM01",
                "Euro95_1": 1.500,
                "Diesel_2": 1.200,
                "LPG_3": 0.600,
            }
        ]
    }


@pytest.fixture
def mock_cbs_metadata_response():
    return {
        "value": [
            {
                "Key": "Euro95_1",
                "Title": "Euro 95",
                "Description": "Unleaded motor petrol",
            }
        ]
    }


@pytest.fixture
def mock_cbs_catalog_response():
    return {
        "value": [
            {
                "Identifier": "80416ENG",
                "ShortTitle": "Fuel prices",
                "Title": "Motor fuel prices; by day",
            }
        ]
    }


def test_fetch_cbs_data(mock_cbs_data_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_cbs_data_response
        mock_get.return_value.raise_for_status = Mock()

        params = CBSDataParams(table_id="80416ENG")
        response = fetch_cbs_data(params)

        assert "value" in response
        assert response["value"][0]["Euro95_1"] == 1.500


@pytest.mark.anyio
async def test_handle_cbs_data(mock_cbs_data_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_cbs_data_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_cbs_data({"table_id": "80416ENG"})

        assert len(result) == 1
        assert "2023MM01" in result[0].text


def test_fetch_cbs_metadata(mock_cbs_metadata_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_cbs_metadata_response
        mock_get.return_value.raise_for_status = Mock()

        params = CBSMetadataParams(table_id="80416ENG")
        response = fetch_cbs_metadata(params)

        assert response["value"][0]["Title"] == "Euro 95"


@pytest.mark.anyio
async def test_handle_cbs_metadata(mock_cbs_metadata_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_cbs_metadata_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_cbs_metadata({"table_id": "80416ENG"})

        assert "Euro 95" in result[0].text


def test_list_cbs_tables(mock_cbs_catalog_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_cbs_catalog_response
        mock_get.return_value.raise_for_status = Mock()

        params = CBSListTablesParams(search="Fuel")
        response = list_cbs_tables(params)

        assert response["value"][0]["Identifier"] == "80416ENG"


@pytest.mark.anyio
async def test_handle_cbs_list_tables(mock_cbs_catalog_response):
    # Add odata.count to mock response
    mock_response = mock_cbs_catalog_response.copy()
    mock_response["odata.count"] = 100

    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = Mock()

        # Test with search
        result = await handle_cbs_list_tables({"search": "Fuel"})
        assert "80416ENG" in result[0].text
        assert "'total_count': 100" in result[0].text
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["$top"] == 10
        assert kwargs["params"]["$skip"] == 0
        assert kwargs["params"]["$inlinecount"] == "allpages"

        # Test with pagination
        result = await handle_cbs_list_tables({"top": 5, "skip": 10})
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["$top"] == 5
        assert kwargs["params"]["$skip"] == 10


@pytest.mark.anyio
async def test_handle_cbs_data_pagination(mock_cbs_data_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_cbs_data_response
        mock_get.return_value.raise_for_status = Mock()

        # Test with top and skip
        result = await handle_cbs_data({"table_id": "80416ENG", "top": 5, "skip": 10})
        assert "2023MM01" in result[0].text
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["$top"] == 5
        assert kwargs["params"]["$skip"] == 10
