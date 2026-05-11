import pytest
from unittest.mock import patch, Mock
import httpx
from opendata_mcp.providers.global_disease_sh import (
    handle_global,
    handle_countries,
    handle_country,
    handle_historical_all,
    handle_historical_country,
    handle_vaccine_coverage,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_disease_sh_global_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "cases": 700000000,
            "deaths": 7000000,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_global()
        assert "700000000" in result[0].text


@pytest.mark.anyio
async def test_disease_sh_global_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")
        with pytest.raises(httpx.HTTPError):
            await handle_global()


@pytest.mark.anyio
async def test_disease_sh_countries_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"country": "USA", "cases": 100000000},
            {"country": "India", "cases": 45000000},
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_countries({"sort": "cases"})
        assert "USA" in result[0].text
        assert "India" in result[0].text


@pytest.mark.anyio
async def test_disease_sh_country_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "country": "France",
            "cases": 38000000,
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_country({"country": "France"})
        assert "France" in result[0].text


@pytest.mark.anyio
async def test_disease_sh_country_requires_country():
    with pytest.raises(ValueError):
        await handle_country({})


@pytest.mark.anyio
async def test_disease_sh_historical_all_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "cases": {"5/1/24": 700000000},
            "deaths": {"5/1/24": 7000000},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_historical_all({"lastdays": 7})
        assert "cases" in result[0].text


@pytest.mark.anyio
async def test_disease_sh_historical_country_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "country": "Germany",
            "timeline": {"cases": {"5/1/24": 38000000}},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_historical_country({"country": "Germany", "lastdays": 30})
        assert "Germany" in result[0].text


@pytest.mark.anyio
async def test_disease_sh_vaccine_coverage_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"5/1/24": 13000000000}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_vaccine_coverage({"lastdays": 30})
        assert "13000000000" in result[0].text
