import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.uk_gov import (
    handle_uk_gov_search_datasets,
    handle_uk_gov_get_dataset,
    handle_uk_gov_list_organizations,
    handle_uk_gov_get_organization,
    handle_uk_gov_list_groups,
    handle_uk_gov_list_tags,
    handle_uk_gov_list_recently_changed,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_uk_gov_search_datasets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {
                "count": 1,
                "results": [{"name": "uk-house-prices", "title": "UK House Prices"}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_gov_search_datasets({"q": "house prices", "rows": 5})
        assert len(result) == 1
        assert "UK House Prices" in result[0].text


@pytest.mark.anyio
async def test_uk_gov_search_datasets_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_uk_gov_search_datasets({"q": "anything"})


@pytest.mark.anyio
async def test_uk_gov_get_dataset_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {
                "name": "uk-house-prices",
                "title": "UK House Prices",
                "resources": [{"format": "CSV"}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_gov_get_dataset({"id": "uk-house-prices"})
        assert "UK House Prices" in result[0].text


@pytest.mark.anyio
async def test_uk_gov_list_organizations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": [{"name": "office-for-national-statistics"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_gov_list_organizations({"limit": 10})
        assert "office-for-national-statistics" in result[0].text


@pytest.mark.anyio
async def test_uk_gov_get_organization_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {
                "name": "office-for-national-statistics",
                "title": "Office for National Statistics",
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_gov_get_organization(
            {"id": "office-for-national-statistics"}
        )
        assert "Office for National Statistics" in result[0].text


@pytest.mark.anyio
async def test_uk_gov_list_groups_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": [{"name": "health", "display_name": "Health"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_gov_list_groups({})
        assert "Health" in result[0].text


@pytest.mark.anyio
async def test_uk_gov_list_tags_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": ["transport", "transport-policy"],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_gov_list_tags({"query": "trans"})
        assert "transport" in result[0].text


@pytest.mark.anyio
async def test_uk_gov_list_recently_changed_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": [{"activity_type": "changed package"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_gov_list_recently_changed({"limit": 5})
        assert "changed package" in result[0].text
