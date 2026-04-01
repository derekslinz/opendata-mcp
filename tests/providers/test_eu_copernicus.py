import pytest
from unittest.mock import patch, Mock
import httpx

from odmcp.providers.eu_copernicus import (
    list_copernicus_collections,
    ListCollectionsParams,
    handle_list_collections,
    search_copernicus_products,
    SearchProductsParams,
    handle_search_products,
    fetch_product_metadata,
    ProductMetadataParams,
    handle_get_product_metadata,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_stac_collections():
    return {
        "collections": [
            {
                "id": "sentinel-2a-l2a",
                "title": "Sentinel-2A L2A",
                "description": "Global land surface",
            },
            {
                "id": "sentinel-1-grd",
                "title": "Sentinel-1 GRD",
                "description": "Radar imaging",
            },
        ]
    }


@pytest.fixture
def mock_stac_search_results():
    return {
        "features": [
            {
                "id": "S2A_MSIL2A_20230101",
                "bbox": [0, 0, 1, 1],
                "properties": {
                    "datetime": "2023-01-01T12:00:00Z",
                    "eo:cloud_cover": 10.5,
                },
            }
        ]
    }


@pytest.fixture
def mock_odata_product():
    return {
        "Id": "uuid-1234",
        "Name": "S2A_MSIL2A_20230101",
        "ContentDate": {"Start": "2023-01-01T12:00:00Z", "End": "2023-01-01T12:00:05Z"},
    }


def test_list_copernicus_collections(mock_stac_collections):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_stac_collections
        mock_get.return_value.raise_for_status = Mock()

        params = ListCollectionsParams(limit=10)
        collections = list_copernicus_collections(params)
        assert len(collections) == 2
        assert collections[0].id == "sentinel-2a-l2a"


@pytest.mark.anyio
async def test_handle_list_collections(mock_stac_collections):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_stac_collections
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_collections({})
        assert len(result) == 1
        assert "sentinel-2a-l2a" in result[0].text


def test_search_copernicus_products(mock_stac_search_results):
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = mock_stac_search_results
        mock_post.return_value.raise_for_status = Mock()

        params = SearchProductsParams(collection="sentinel-2a-l2a", limit=5)
        response = search_copernicus_products(params)
        assert len(response["features"]) == 1
        assert response["features"][0]["id"] == "S2A_MSIL2A_20230101"


@pytest.mark.anyio
async def test_handle_search_products(mock_stac_search_results):
    with patch("httpx.post") as mock_post:
        mock_post.return_value.json.return_value = mock_stac_search_results
        mock_post.return_value.raise_for_status = Mock()

        result = await handle_search_products({"collection": "sentinel-2a-l2a"})
        assert len(result) == 1
        assert "S2A_MSIL2A_20230101" in result[0].text
        assert "10.5" in result[0].text


def test_fetch_product_metadata(mock_odata_product):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_odata_product
        mock_get.return_value.raise_for_status = Mock()

        params = ProductMetadataParams(product_id="uuid-1234")
        response = fetch_product_metadata(params)
        assert response["Id"] == "uuid-1234"
        assert response["Name"] == "S2A_MSIL2A_20230101"


@pytest.mark.anyio
async def test_handle_get_product_metadata(mock_odata_product):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_odata_product
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_product_metadata({"product_id": "uuid-1234"})
        assert len(result) == 1
        assert "uuid-1234" in result[0].text
        assert "S2A_MSIL2A_20230101" in result[0].text


@pytest.mark.anyio
async def test_handle_list_collections_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("STAC API is down")
        result = await handle_list_collections({})
        assert "Error: Unable to reach Copernicus STAC API" in result[0].text


@pytest.mark.anyio
async def test_handle_search_products_error():
    with patch("httpx.post") as mock_post:
        mock_post.side_effect = httpx.HTTPError("STAC Search failed")
        result = await handle_search_products({"collection": "sentinel-2a-l2a"})
        assert "Error searching Copernicus products" in result[0].text


@pytest.mark.anyio
async def test_handle_get_product_metadata_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("OData timeout")
        result = await handle_get_product_metadata({"product_id": "uuid-1234"})
        assert "Error fetching product metadata" in result[0].text
