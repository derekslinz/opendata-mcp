import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.uk_ons import (
    handle_list_datasets,
    handle_get_dataset,
    handle_list_editions,
    handle_get_edition,
    handle_list_versions,
    handle_get_observations,
    handle_list_codelists,
    handle_get_codelist,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_ons_list_datasets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "items": [{"id": "cpih01", "title": "Consumer Prices Index incl. housing"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_datasets()
        assert "cpih01" in result[0].text


@pytest.mark.anyio
async def test_ons_list_datasets_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_list_datasets()


@pytest.mark.anyio
async def test_ons_get_dataset_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "id": "cpih01",
            "title": "CPIH",
            "description": "Consumer Prices Index incl. owner occupiers' housing costs",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_dataset({"id": "cpih01"})
        assert "CPIH" in result[0].text


@pytest.mark.anyio
async def test_ons_get_dataset_missing_arg():
    with pytest.raises(ValueError):
        await handle_get_dataset({})


@pytest.mark.anyio
async def test_ons_list_editions_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "items": [{"edition": "time-series", "state": "published"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_editions({"id": "cpih01"})
        assert "time-series" in result[0].text


@pytest.mark.anyio
async def test_ons_get_edition_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "edition": "time-series",
            "state": "published",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_edition({"id": "cpih01", "edition": "time-series"})
        assert "time-series" in result[0].text


@pytest.mark.anyio
async def test_ons_get_edition_missing_args():
    with pytest.raises(ValueError):
        await handle_get_edition({"id": "cpih01"})


@pytest.mark.anyio
async def test_ons_list_versions_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "items": [{"version": 1, "state": "published"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_versions({"id": "cpih01", "edition": "time-series"})
        assert "version" in result[0].text


@pytest.mark.anyio
async def test_ons_get_observations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "observations": [
                {"observation": "123.4", "dimensions": {"time": "2023-Jan"}}
            ],
            "total_observations": 1,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_observations(
            {
                "id": "cpih01",
                "edition": "time-series",
                "version": "1",
                "time": "2023-Jan",
                "geography": "K02000001",
            }
        )
        assert "123.4" in result[0].text


@pytest.mark.anyio
async def test_ons_get_observations_missing_args():
    with pytest.raises(ValueError):
        await handle_get_observations({"id": "cpih01", "edition": "time-series"})


@pytest.mark.anyio
async def test_ons_list_codelists_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "items": [{"id": "uk-only", "name": "UK"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_codelists()
        assert "uk-only" in result[0].text


@pytest.mark.anyio
async def test_ons_get_codelist_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "id": "uk-only",
            "name": "UK",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_codelist({"id": "uk-only"})
        assert "uk-only" in result[0].text
