import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_gbif import (
    handle_gbif_search_occurrences,
    handle_gbif_get_occurrence,
    handle_gbif_search_species,
    handle_gbif_get_species,
    handle_gbif_get_species_name_suggest,
    handle_gbif_list_datasets,
    handle_gbif_get_dataset,
    handle_gbif_get_occurrence_counts,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_gbif_search_occurrences_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [{"key": 1, "scientificName": "Puma concolor"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_gbif_search_occurrences(
            {"scientificName": "Puma concolor", "country": "US", "limit": 5}
        )
        assert "Puma concolor" in result[0].text


@pytest.mark.anyio
async def test_gbif_search_occurrences_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("GBIF unavailable")

        with pytest.raises(httpx.HTTPError):
            await handle_gbif_search_occurrences({"scientificName": "Puma concolor"})


@pytest.mark.anyio
async def test_gbif_get_occurrence_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "key": 9999,
            "scientificName": "Quercus alba",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_gbif_get_occurrence({"key": 9999})
        assert "Quercus alba" in result[0].text


@pytest.mark.anyio
async def test_gbif_search_species_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [{"key": 2877951, "scientificName": "Quercus"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_gbif_search_species({"q": "Quercus"})
        assert "Quercus" in result[0].text


@pytest.mark.anyio
async def test_gbif_get_species_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "key": 2877951,
            "scientificName": "Quercus L.",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_gbif_get_species({"key": 2877951})
        assert "Quercus L." in result[0].text


@pytest.mark.anyio
async def test_gbif_get_species_name_suggest_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"key": 2877951, "scientificName": "Quercus"}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_gbif_get_species_name_suggest({"q": "Querc"})
        assert "Quercus" in result[0].text


@pytest.mark.anyio
async def test_gbif_list_datasets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [{"key": "abc-uuid", "title": "Test Dataset"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_gbif_list_datasets({"type": "OCCURRENCE", "limit": 5})
        assert "Test Dataset" in result[0].text


@pytest.mark.anyio
async def test_gbif_get_dataset_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "key": "abc-uuid",
            "title": "eBird Observation Dataset",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_gbif_get_dataset({"key": "abc-uuid"})
        assert "eBird Observation Dataset" in result[0].text


@pytest.mark.anyio
async def test_gbif_get_occurrence_counts_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = 12345678
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_gbif_get_occurrence_counts({"country": "US"})
        assert "12345678" in result[0].text
