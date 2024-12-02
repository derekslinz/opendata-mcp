import pytest
from unittest.mock import patch, Mock

from odmcp.providers.ch_sbb import (
    fetch_rail_traffic_info,
    TrafficInfoParams,
    handle_rail_traffic_info,
    fetch_railway_lines,
    RailwayLineParams,
    handle_railway_lines,
    fetch_rolling_stock,
    RollingStockParams,
    handle_rolling_stock,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


###################
# Rail Traffic Information
###################


@pytest.fixture
def mock_traffic_info_response():
    return {
        "total_count": 2,
        "results": [
            {
                "title": "Track maintenance in Zürich",
                "link": "https://data.sbb.ch/info/1",
                "description": "Maintenance work between Zürich HB and Oerlikon",
                "published": "2024-01-01T10:00:00Z",
                "author": "SBB",
                "validitybegin": "2024-01-02T00:00:00Z",
                "validityend": "2024-01-03T00:00:00Z",
                "description_html": "<p>Maintenance work between Zürich HB and Oerlikon</p>",
            },
            {
                "title": "Delays in Bern",
                "link": "https://data.sbb.ch/info/2",
                "description": "Signal failure causing delays",
                "published": "2024-01-01T11:00:00Z",
                "author": "SBB",
                "validitybegin": "2024-01-01T11:00:00Z",
                "validityend": "2024-01-01T15:00:00Z",
                "description_html": "<p>Signal failure causing delays</p>",
            },
        ],
    }


def test_fetch_rail_traffic_info(mock_traffic_info_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_traffic_info_response
        mock_get.return_value.raise_for_status = Mock()

        params = TrafficInfoParams(limit=2, timezone="Europe/Zurich")
        response = fetch_rail_traffic_info(params)

        assert response.total_count == 2
        assert len(response.results) == 2
        assert response.results[0].title == "Track maintenance in Zürich"
        assert response.results[1].title == "Delays in Bern"


@pytest.mark.anyio
async def test_handle_rail_traffic_info(mock_traffic_info_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_traffic_info_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_rail_traffic_info({"limit": 2})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Track maintenance in Zürich" in result[0].text
        assert "Delays in Bern" in result[0].text


###################
# Railway Line Information
###################


@pytest.fixture
def mock_railway_line_response():
    return {
        "total_count": 2,
        "results": [
            {
                "linie": 100,
                "linienname": "Zürich HB - Bern",
                "bpk_anfang": "Zürich HB",
                "bpk_ende": "Bern",
                "km_anfang": 0.0,
                "km_ende": 120.5,
                "stationierung_anfang": 0,
                "stationierung_ende": 120500,
                "tst": {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[8.540192, 47.378177], [7.439122, 46.949083]],
                    },
                    "properties": {},
                },
                "geo_point_2d": {"lon": 7.989657, "lat": 47.163630},
            },
            {
                "linie": 200,
                "linienname": "Basel - Luzern",
                "bpk_anfang": "Basel SBB",
                "bpk_ende": "Luzern",
                "km_anfang": 0.0,
                "km_ende": 105.8,
                "stationierung_anfang": 0,
                "stationierung_ende": 105800,
                "tst": {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[7.589576, 47.547184], [8.310485, 47.050168]],
                    },
                    "properties": {},
                },
                "geo_point_2d": {"lon": 7.950031, "lat": 47.298676},
            },
        ],
    }


def test_fetch_railway_lines(mock_railway_line_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_railway_line_response
        mock_get.return_value.raise_for_status = Mock()

        params = RailwayLineParams(limit=2)
        response = fetch_railway_lines(params)

        assert response.total_count == 2
        assert len(response.results) == 2
        assert response.results[0].linie == 100
        assert response.results[0].linienname == "Zürich HB - Bern"
        assert response.results[1].linie == 200
        assert response.results[1].linienname == "Basel - Luzern"


@pytest.mark.anyio
async def test_handle_railway_lines(mock_railway_line_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_railway_line_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_railway_lines({"limit": 2})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Zürich HB - Bern" in result[0].text
        assert "Basel - Luzern" in result[0].text


###################
# Rolling Stock Information
###################


@pytest.fixture
def mock_rolling_stock_response():
    return {
        "total_count": 2,
        "results": [
            {
                "fahrzeug_art_struktur": "Locomotive",
                "fahrzeug_typ": "Re 460",
                "objekt": "460 001-1",
                "baudatum_fahrzeug": "1991-01-15",
                "eigengewicht_tara": 84.0,
                "lange_uber_puffer_lup": 18640,
                "vmax_betrieblich_zugelassen": 200,
            },
            {
                "fahrzeug_art_struktur": "Passenger Car",
                "fahrzeug_typ": "IC 2000",
                "objekt": "IC2000-1234",
                "baudatum_fahrzeug": "1997-06-20",
                "eigengewicht_tara": 42.5,
                "lange_uber_puffer_lup": 26100,
                "vmax_betrieblich_zugelassen": 200,
            },
        ],
    }


def test_fetch_rolling_stock(mock_rolling_stock_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_rolling_stock_response
        mock_get.return_value.raise_for_status = Mock()

        params = RollingStockParams(limit=2)
        response = fetch_rolling_stock(params)

        assert response.total_count == 2
        assert len(response.results) == 2
        assert response.results[0].fahrzeug_typ == "Re 460"
        assert response.results[1].fahrzeug_typ == "IC 2000"


@pytest.mark.anyio
async def test_handle_rolling_stock(mock_rolling_stock_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_rolling_stock_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_rolling_stock({"limit": 2})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Re 460" in result[0].text
        assert "IC 2000" in result[0].text
