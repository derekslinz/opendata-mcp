import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.fr_data_gouv import (
    handle_fr_datagouv_search_datasets,
    handle_fr_datagouv_get_dataset,
    handle_fr_datagouv_list_organizations,
    handle_fr_datagouv_get_organization,
    handle_fr_datagouv_search_reuses,
    handle_fr_datagouv_list_topics,
    handle_fr_datagouv_list_tags,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_fr_datagouv_search_datasets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"slug": "transports-publics", "title": "Transports Publics"}],
            "total": 1,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fr_datagouv_search_datasets({"q": "transports"})
        assert "Transports Publics" in result[0].text


@pytest.mark.anyio
async def test_fr_datagouv_search_datasets_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Panne de réseau")

        with pytest.raises(httpx.HTTPError):
            await handle_fr_datagouv_search_datasets({"q": "x"})


@pytest.mark.anyio
async def test_fr_datagouv_get_dataset_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "slug": "transports-publics",
            "title": "Transports Publics",
            "resources": [{"format": "csv"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fr_datagouv_get_dataset({"id": "transports-publics"})
        assert "Transports Publics" in result[0].text


@pytest.mark.anyio
async def test_fr_datagouv_list_organizations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"slug": "insee", "name": "INSEE"}],
            "total": 1,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fr_datagouv_list_organizations({"page_size": 5})
        assert "INSEE" in result[0].text


@pytest.mark.anyio
async def test_fr_datagouv_get_organization_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "slug": "insee",
            "name": "INSEE",
            "description": "Institut national de la statistique",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fr_datagouv_get_organization({"id": "insee"})
        assert "INSEE" in result[0].text


@pytest.mark.anyio
async def test_fr_datagouv_search_reuses_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"title": "Carte des Transports", "url": "https://example.fr"}],
            "total": 1,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fr_datagouv_search_reuses({"q": "carte"})
        assert "Carte des Transports" in result[0].text


@pytest.mark.anyio
async def test_fr_datagouv_list_topics_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": [{"slug": "sante", "name": "Santé"}],
            "total": 1,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fr_datagouv_list_topics({"page_size": 5})
        assert "Santé" in result[0].text


@pytest.mark.anyio
async def test_fr_datagouv_list_tags_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"text": "transport"},
            {"text": "transport-public"},
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fr_datagouv_list_tags({"q": "trans"})
        assert "transport" in result[0].text
