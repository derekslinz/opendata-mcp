import pytest
from unittest.mock import patch, Mock
import httpx
from opendata_mcp.providers.global_who_gho import (
    handle_list_indicators,
    handle_get_indicator_data,
    handle_list_dimensions,
    handle_list_dimension_values,
    handle_list_countries,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_who_gho_list_indicators_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "value": [
                {
                    "IndicatorCode": "WHOSIS_000001",
                    "IndicatorName": "Life expectancy at birth (years)",
                },
            ]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_indicators({"top": 1})
        assert "WHOSIS_000001" in result[0].text


@pytest.mark.anyio
async def test_who_gho_list_indicators_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")
        with pytest.raises(httpx.HTTPError):
            await handle_list_indicators()


@pytest.mark.anyio
async def test_who_gho_get_indicator_data_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "value": [{"SpatialDim": "USA", "TimeDim": 2020, "NumericValue": 78.5}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_indicator_data(
            {"indicator_code": "WHOSIS_000001", "filter": "SpatialDim eq 'USA'"}
        )
        assert "USA" in result[0].text
        assert "78.5" in result[0].text


@pytest.mark.anyio
async def test_who_gho_get_indicator_data_requires_code():
    with pytest.raises(ValueError):
        await handle_get_indicator_data({})


@pytest.mark.anyio
async def test_who_gho_list_dimensions_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "value": [
                {"Code": "COUNTRY", "Title": "Country"},
                {"Code": "SEX", "Title": "Sex"},
            ]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_dimensions()
        assert "COUNTRY" in result[0].text
        assert "SEX" in result[0].text


@pytest.mark.anyio
async def test_who_gho_list_dimension_values_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "value": [{"Code": "USA", "Title": "United States of America"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_dimension_values({"dim": "COUNTRY"})
        assert "United States of America" in result[0].text


@pytest.mark.anyio
async def test_who_gho_list_dimension_values_requires_dim():
    with pytest.raises(ValueError):
        await handle_list_dimension_values({})


@pytest.mark.anyio
async def test_who_gho_list_countries_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "value": [{"Code": "FRA", "Title": "France"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_countries()
        assert "France" in result[0].text
