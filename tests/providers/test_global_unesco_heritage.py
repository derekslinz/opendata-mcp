import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_unesco_heritage import (
    handle_unesco_heritage_list_sites,
    handle_unesco_heritage_get_site,
    handle_unesco_heritage_search,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_unesco_heritage_list_sites_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {
                "id_number": 1,
                "site": "Galápagos Islands",
                "states": "EC",
                "region": "LAC",
                "category": "Natural",
                "date_inscribed": 1978,
            },
            {
                "id_number": 456,
                "site": "Taj Mahal",
                "states": "IN",
                "region": "APA",
                "category": "Cultural",
                "date_inscribed": 1983,
            },
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_unesco_heritage_list_sites({})
        assert "Galápagos Islands" in result[0].text
        assert "Taj Mahal" in result[0].text


@pytest.mark.anyio
async def test_unesco_heritage_list_sites_with_filters():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status = Mock()

        await handle_unesco_heritage_list_sites(
            {"iso": "FR", "category": "Cultural", "danger": 0}
        )
        call_params = mock_get.call_args.kwargs.get("params", {})
        assert call_params.get("iso") == "FR"
        assert call_params.get("category") == "Cultural"


@pytest.mark.anyio
async def test_unesco_heritage_list_sites_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Server error")
        with pytest.raises(httpx.HTTPError):
            await handle_unesco_heritage_list_sites({})


@pytest.mark.anyio
async def test_unesco_heritage_get_site_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "id_number": 456,
            "site": "Taj Mahal",
            "states": "IN",
            "region": "APA",
            "category": "Cultural",
            "date_inscribed": 1983,
            "latitude": "27.175015",
            "longitude": "78.042111",
            "area_hectares": 42.0,
            "short_description": "An immense mausoleum of white marble...",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_unesco_heritage_get_site({"site_id": 456})
        assert "Taj Mahal" in result[0].text
        assert "456" in result[0].text


@pytest.mark.anyio
async def test_unesco_heritage_get_site_missing_param():
    with pytest.raises(ValueError):
        await handle_unesco_heritage_get_site({})


@pytest.mark.anyio
async def test_unesco_heritage_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {
                "id_number": 154,
                "site": "Venice and its Lagoon",
                "states": "IT",
                "category": "Cultural",
            }
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_unesco_heritage_search({"name": "Venice"})
        assert "Venice" in result[0].text


@pytest.mark.anyio
async def test_unesco_heritage_search_missing_param():
    with pytest.raises(ValueError):
        await handle_unesco_heritage_search({})


@pytest.mark.anyio
async def test_unesco_heritage_search_passes_name_param():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = []
        mock_get.return_value.raise_for_status = Mock()

        await handle_unesco_heritage_search({"name": "Great Barrier Reef"})
        call_params = mock_get.call_args.kwargs.get("params", {})
        assert call_params.get("name") == "Great Barrier Reef"
