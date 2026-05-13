import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.us_census_geocoder import (
    TOOLS,
    TOOLS_HANDLERS,
    handle_census_geocode_oneline,
    handle_census_geocode_address,
    handle_census_geocode_coordinates,
    handle_census_geocode_oneline_geographies,
    handle_census_geocode_address_geographies,
    handle_census_benchmarks,
    handle_census_vintages,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_tools_registered():
    """All registered tools must have a matching handler entry."""
    names = [t.name for t in TOOLS]
    for name in names:
        assert name in TOOLS_HANDLERS


@pytest.mark.anyio
async def test_census_geocode_oneline_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {
                "addressMatches": [{"matchedAddress": "1600 PENNSYLVANIA AVE NW"}]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_census_geocode_oneline(
            {"address": "1600 Pennsylvania Ave NW, Washington DC 20500"}
        )
        assert len(result) == 1
        assert "PENNSYLVANIA" in result[0].text


@pytest.mark.anyio
async def test_census_geocode_oneline_missing_address():
    with pytest.raises(ValueError):
        await handle_census_geocode_oneline({})


@pytest.mark.anyio
async def test_census_geocode_address_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {"addressMatches": [{"coordinates": {"x": -77.0, "y": 38.9}}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_census_geocode_address(
            {
                "street": "1600 Pennsylvania Ave NW",
                "city": "Washington",
                "state": "DC",
                "zip": "20500",
            }
        )
        assert "coordinates" in result[0].text


@pytest.mark.anyio
async def test_census_geocode_coordinates_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {"geographies": {"Counties": [{"NAME": "District of Columbia"}]}}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_census_geocode_coordinates({"x": -77.0365, "y": 38.8977})
        assert "District of Columbia" in result[0].text


@pytest.mark.anyio
async def test_census_geocode_coordinates_missing_args():
    with pytest.raises(ValueError):
        await handle_census_geocode_coordinates({"x": -77.0})


@pytest.mark.anyio
async def test_census_geocode_oneline_geographies_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {
                "addressMatches": [
                    {"geographies": {"Census Blocks": [{"GEOID": "110010001"}]}}
                ]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_census_geocode_oneline_geographies(
            {"address": "1600 Pennsylvania Ave NW, Washington DC"}
        )
        assert "GEOID" in result[0].text


@pytest.mark.anyio
async def test_census_geocode_address_geographies_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {"addressMatches": [{"matchedAddress": "EXAMPLE"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_census_geocode_address_geographies(
            {"street": "1 Infinite Loop", "city": "Cupertino", "state": "CA"}
        )
        assert "EXAMPLE" in result[0].text


@pytest.mark.anyio
async def test_census_benchmarks_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "benchmarks": [{"benchmarkName": "Public_AR_Current"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_census_benchmarks()
        assert "Public_AR_Current" in result[0].text


@pytest.mark.anyio
async def test_census_vintages_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "vintages": [{"vintageName": "Current_Current"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_census_vintages({"benchmark": "Public_AR_Current"})
        assert "Current_Current" in result[0].text


@pytest.mark.anyio
async def test_census_benchmarks_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_census_benchmarks()
