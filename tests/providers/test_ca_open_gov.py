import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.ca_open_gov import (
    handle_ca_opengov_search_datasets,
    handle_ca_opengov_get_dataset,
    handle_ca_opengov_list_organizations,
    handle_ca_opengov_get_organization,
    handle_ca_opengov_list_groups,
    handle_ca_opengov_list_tags,
    handle_ca_opengov_list_licenses,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_ca_opengov_search_datasets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {
                "count": 1,
                "results": [
                    {"name": "canada-census-2021", "title": "Canada Census 2021"}
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ca_opengov_search_datasets({"q": "census"})
        assert "Canada Census 2021" in result[0].text


@pytest.mark.anyio
async def test_ca_opengov_search_datasets_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Boom")

        with pytest.raises(httpx.HTTPError):
            await handle_ca_opengov_search_datasets({"q": "x"})


@pytest.mark.anyio
async def test_ca_opengov_get_dataset_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {
                "name": "canada-census-2021",
                "title": "Canada Census 2021",
                "resources": [{"format": "CSV"}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ca_opengov_get_dataset({"id": "canada-census-2021"})
        assert "Canada Census 2021" in result[0].text


@pytest.mark.anyio
async def test_ca_opengov_list_organizations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": [{"name": "statcan", "title": "Statistics Canada"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ca_opengov_list_organizations({"limit": 10})
        assert "Statistics Canada" in result[0].text


@pytest.mark.anyio
async def test_ca_opengov_get_organization_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {"name": "statcan", "title": "Statistics Canada"},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ca_opengov_get_organization({"id": "statcan"})
        assert "Statistics Canada" in result[0].text


@pytest.mark.anyio
async def test_ca_opengov_list_groups_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": [{"name": "environment", "display_name": "Environment"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ca_opengov_list_groups({})
        assert "Environment" in result[0].text


@pytest.mark.anyio
async def test_ca_opengov_list_tags_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": ["climate", "climate-change"],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ca_opengov_list_tags({"query": "climate"})
        assert "climate" in result[0].text


@pytest.mark.anyio
async def test_ca_opengov_list_licenses_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": [
                {"id": "ca-ogl-lgo", "title": "Open Government Licence - Canada"}
            ],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ca_opengov_list_licenses({})
        assert "Open Government Licence" in result[0].text
