import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_inaturalist import (
    handle_inaturalist_search_observations,
    handle_inaturalist_get_observation,
    handle_inaturalist_search_taxa,
    handle_inaturalist_get_taxon,
    handle_inaturalist_list_places,
    handle_inaturalist_get_place,
    handle_inaturalist_list_projects,
    handle_inaturalist_get_user,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_inaturalist_search_observations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total_results": 1,
            "results": [{"id": 42, "species_guess": "Western Bluebird"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_inaturalist_search_observations(
            {"taxon_name": "Sialia mexicana", "per_page": 5}
        )
        assert "Western Bluebird" in result[0].text


@pytest.mark.anyio
async def test_inaturalist_search_observations_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("iNaturalist unavailable")

        with pytest.raises(httpx.HTTPError):
            await handle_inaturalist_search_observations({"q": "owl"})


@pytest.mark.anyio
async def test_inaturalist_get_observation_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total_results": 1,
            "results": [{"id": 100, "species_guess": "Mountain Lion"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_inaturalist_get_observation({"id": 100})
        assert "Mountain Lion" in result[0].text


@pytest.mark.anyio
async def test_inaturalist_search_taxa_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total_results": 1,
            "results": [{"id": 1, "name": "Quercus alba", "rank": "species"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_inaturalist_search_taxa(
            {"q": "Quercus", "rank": "species"}
        )
        assert "Quercus alba" in result[0].text


@pytest.mark.anyio
async def test_inaturalist_get_taxon_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total_results": 1,
            "results": [{"id": 50, "name": "Felis catus"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_inaturalist_get_taxon({"id": 50})
        assert "Felis catus" in result[0].text


@pytest.mark.anyio
async def test_inaturalist_list_places_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total_results": 1,
            "results": [{"id": 7, "display_name": "California, US"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_inaturalist_list_places({"q": "Calif"})
        assert "California, US" in result[0].text


@pytest.mark.anyio
async def test_inaturalist_get_place_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total_results": 1,
            "results": [{"id": 14, "display_name": "Yosemite National Park"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_inaturalist_get_place({"id": 14})
        assert "Yosemite National Park" in result[0].text


@pytest.mark.anyio
async def test_inaturalist_list_projects_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total_results": 1,
            "results": [{"id": 99, "title": "City Nature Challenge"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_inaturalist_list_projects({"q": "City Nature"})
        assert "City Nature Challenge" in result[0].text


@pytest.mark.anyio
async def test_inaturalist_get_user_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "total_results": 1,
            "results": [{"id": 1, "login": "kueda", "name": "Ken-ichi Ueda"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_inaturalist_get_user({"id": "kueda"})
        assert "Ken-ichi Ueda" in result[0].text
