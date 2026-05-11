import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.au_data_gov import (
    handle_au_datagov_search_datasets,
    handle_au_datagov_get_dataset,
    handle_au_datagov_list_organizations,
    handle_au_datagov_get_organization,
    handle_au_datagov_list_groups,
    handle_au_datagov_list_tags,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_au_datagov_search_datasets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {
                "count": 1,
                "results": [
                    {"name": "abs-population", "title": "ABS Population Estimates"}
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_au_datagov_search_datasets({"q": "population"})
        assert "ABS Population Estimates" in result[0].text


@pytest.mark.anyio
async def test_au_datagov_search_datasets_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Down under outage")

        with pytest.raises(httpx.HTTPError):
            await handle_au_datagov_search_datasets({"q": "anything"})


@pytest.mark.anyio
async def test_au_datagov_get_dataset_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {
                "name": "abs-population",
                "title": "ABS Population Estimates",
                "resources": [{"format": "CSV"}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_au_datagov_get_dataset({"id": "abs-population"})
        assert "ABS Population Estimates" in result[0].text


@pytest.mark.anyio
async def test_au_datagov_list_organizations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": [{"name": "abs", "title": "Australian Bureau of Statistics"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_au_datagov_list_organizations({"limit": 10})
        assert "Australian Bureau of Statistics" in result[0].text


@pytest.mark.anyio
async def test_au_datagov_get_organization_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {"name": "abs", "title": "Australian Bureau of Statistics"},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_au_datagov_get_organization({"id": "abs"})
        assert "Australian Bureau of Statistics" in result[0].text


@pytest.mark.anyio
async def test_au_datagov_list_groups_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": [{"name": "environment", "display_name": "Environment"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_au_datagov_list_groups({})
        assert "Environment" in result[0].text


@pytest.mark.anyio
async def test_au_datagov_list_tags_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": ["geospatial", "geology"],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_au_datagov_list_tags({"query": "geo"})
        assert "geospatial" in result[0].text
