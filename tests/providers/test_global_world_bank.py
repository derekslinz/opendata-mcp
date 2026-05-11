import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_world_bank import (
    handle_list_countries,
    handle_get_country,
    handle_list_indicators,
    handle_search_indicators,
    handle_get_indicator_data,
    handle_list_topics,
    handle_list_sources,
    handle_list_income_levels,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_world_bank_list_countries_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"page": 1, "pages": 1, "per_page": 300, "total": 2},
            [
                {"id": "USA", "name": "United States"},
                {"id": "BRA", "name": "Brazil"},
            ],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_countries()
        assert len(result) == 1
        assert "United States" in result[0].text
        assert "Brazil" in result[0].text


@pytest.mark.anyio
async def test_world_bank_list_countries_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_list_countries()


@pytest.mark.anyio
async def test_world_bank_get_country_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"page": 1, "pages": 1, "per_page": 50, "total": 1},
            [{"id": "BRA", "iso2Code": "BR", "name": "Brazil"}],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_country({"country": "BRA"})
        assert "Brazil" in result[0].text


@pytest.mark.anyio
async def test_world_bank_get_country_missing_arg():
    with pytest.raises(ValueError):
        await handle_get_country({})


@pytest.mark.anyio
async def test_world_bank_list_indicators_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"page": 1, "pages": 5, "per_page": 200, "total": 1000},
            [{"id": "NY.GDP.MKTP.CD", "name": "GDP (current US$)"}],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_indicators()
        assert "NY.GDP.MKTP.CD" in result[0].text


@pytest.mark.anyio
async def test_world_bank_search_indicators_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"page": 1, "pages": 1, "per_page": 200, "total": 1},
            [{"id": "SP.POP.TOTL", "name": "Population, total"}],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_indicators({"topic": 8})
        assert "Population, total" in result[0].text


@pytest.mark.anyio
async def test_world_bank_get_indicator_data_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"page": 1, "pages": 1, "per_page": 100, "total": 2},
            [
                {
                    "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"},
                    "country": {"id": "US", "value": "United States"},
                    "value": 23315080560000.0,
                    "date": "2021",
                },
            ],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_indicator_data(
            {
                "country": "USA",
                "indicator": "NY.GDP.MKTP.CD",
                "start": 2020,
                "end": 2021,
            }
        )
        assert "NY.GDP.MKTP.CD" in result[0].text
        assert "United States" in result[0].text


@pytest.mark.anyio
async def test_world_bank_get_indicator_data_missing_args():
    with pytest.raises(ValueError):
        await handle_get_indicator_data({"country": "USA"})


@pytest.mark.anyio
async def test_world_bank_list_topics_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"page": 1, "pages": 1, "per_page": 50, "total": 1},
            [{"id": "1", "value": "Agriculture & Rural Development"}],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_topics()
        assert "Agriculture" in result[0].text


@pytest.mark.anyio
async def test_world_bank_list_sources_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"page": 1, "pages": 1, "per_page": 50, "total": 1},
            [{"id": "2", "name": "World Development Indicators"}],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_sources()
        assert "World Development Indicators" in result[0].text


@pytest.mark.anyio
async def test_world_bank_list_income_levels_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"page": 1, "pages": 1, "per_page": 50, "total": 1},
            [{"id": "HIC", "value": "High income"}],
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_income_levels()
        assert "High income" in result[0].text
