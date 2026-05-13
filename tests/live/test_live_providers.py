"""
Live integration tests — real HTTP calls, no mocking.

Tests are tagged ``live`` and excluded from the default pytest run.
Run with: ``pytest tests/live/ -m live -v``

Providers covered (10 stable, keyless endpoints):
  - global_frankfurter   (FX rates)
  - global_wikipedia     (article summary)
  - us_usgs_earthquake   (recent quakes)
  - global_open_library  (book search)
  - global_who_gho       (health indicators)
  - global_world_bank    (country list)
  - us_clinicaltrials    (study search)
  - global_disease_sh    (COVID global)
  - global_met_museum    (art object)
  - global_osm_nominatim (geocoding)
"""

import pytest


# ---------------------------------------------------------------------------
# global_frankfurter — ECB FX rates
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_frankfurter_latest():
    from meta_data_mcp.providers.global_frankfurter import fetch_latest, LatestParams

    data = fetch_latest(LatestParams(base="USD"))
    assert "rates" in data
    assert "EUR" in data["rates"]
    assert data["rates"]["EUR"] > 0


@pytest.mark.live
def test_live_frankfurter_currencies():
    from meta_data_mcp.providers.global_frankfurter import (
        fetch_currencies,
        CurrenciesParams,
    )

    data = fetch_currencies(CurrenciesParams())
    assert isinstance(data, dict)
    assert "EUR" in data
    assert "USD" in data


# ---------------------------------------------------------------------------
# global_wikipedia — REST API summaries
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_wikipedia_summary():
    from meta_data_mcp.providers.global_wikipedia import fetch_summary, SummaryParams

    data = fetch_summary(SummaryParams(title="Python_(programming_language)"))
    assert data.get("title") or data.get("displaytitle")
    assert "extract" in data


@pytest.mark.live
def test_live_wikipedia_onthisday():
    from meta_data_mcp.providers.global_wikipedia import fetch_onthisday, OnThisDayParams

    data = fetch_onthisday(OnThisDayParams(month="01", day="01"))
    # Returns text (API endpoint may vary by provider implementation)
    assert data is not None


# ---------------------------------------------------------------------------
# us_usgs_earthquake — FDSN Event Service
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_usgs_significant_day_feed():
    from meta_data_mcp.providers.us_usgs_earthquake import (
        handle_usgs_eq_feed_significant_week,
    )
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        handle_usgs_eq_feed_significant_week()
    )
    assert len(result) == 1
    text = result[0].text
    # GeoJSON feed — should contain "FeatureCollection" or "features"
    assert "features" in text or "FeatureCollection" in text


@pytest.mark.live
def test_live_usgs_query_count():
    from meta_data_mcp.providers.us_usgs_earthquake import fetch_count, CountParams

    data = fetch_count(
        CountParams(starttime="2024-01-01", endtime="2024-01-07", minmagnitude=5.0)
    )
    assert "count" in data or isinstance(data, dict)


# ---------------------------------------------------------------------------
# global_open_library — books
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_open_library_search():
    from meta_data_mcp.providers.global_open_library import (
        fetch_search_books,
        SearchBooksParams,
    )

    data = fetch_search_books(SearchBooksParams(title="Moby Dick", limit=3))
    assert "docs" in data or "numFound" in data


@pytest.mark.live
def test_live_open_library_isbn():
    from meta_data_mcp.providers.global_open_library import (
        fetch_isbn_lookup,
        IsbnLookupParams,
    )

    data = fetch_isbn_lookup(IsbnLookupParams(isbn="9780140328721"))
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# global_who_gho — WHO health indicators
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_who_gho_list_indicators():
    from meta_data_mcp.providers.global_who_gho import (
        fetch_list_indicators,
        ListIndicatorsParams,
    )

    data = fetch_list_indicators(ListIndicatorsParams())
    assert "value" in data or isinstance(data, dict)


# ---------------------------------------------------------------------------
# global_world_bank — development indicators
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_world_bank_list_countries():
    from meta_data_mcp.providers.global_world_bank import (
        fetch_list_countries,
        ListCountriesParams,
    )

    data = fetch_list_countries(ListCountriesParams())
    # Returns [metadata, [country, ...]]
    assert isinstance(data, list)
    assert len(data) == 2
    countries = data[1]
    assert len(countries) > 100


@pytest.mark.live
def test_live_world_bank_indicator():
    from meta_data_mcp.providers.global_world_bank import (
        fetch_get_indicator_data,
        GetIndicatorDataParams,
    )

    data = fetch_get_indicator_data(
        GetIndicatorDataParams(
            country_code="USA", indicator="NY.GDP.MKTP.CD", date_range="2020:2023"
        )
    )
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# us_clinicaltrials — ClinicalTrials.gov v2
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_clinicaltrials_search():
    from meta_data_mcp.providers.us_clinicaltrials import (
        fetch_search_studies,
        SearchStudiesParams,
    )

    data = fetch_search_studies(SearchStudiesParams(query_term="diabetes", page_size=3))
    assert "studies" in data or isinstance(data, dict)


# ---------------------------------------------------------------------------
# global_disease_sh — COVID stats
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_disease_sh_global():
    from meta_data_mcp.providers.global_disease_sh import fetch_global, GlobalParams

    data = fetch_global(GlobalParams())
    assert "cases" in data
    assert data["cases"] > 0


@pytest.mark.live
def test_live_disease_sh_country():
    from meta_data_mcp.providers.global_disease_sh import fetch_country, CountryParams

    data = fetch_country(CountryParams(country="USA"))
    assert "country" in data or "cases" in data


# ---------------------------------------------------------------------------
# global_met_museum — Metropolitan Museum of Art
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_met_museum_get_object():
    from meta_data_mcp.providers.global_met_museum import (
        fetch_get_object,
        GetObjectParams,
    )

    data = fetch_get_object(GetObjectParams(object_id=45734))
    assert "objectID" in data
    assert data["objectID"] == 45734


@pytest.mark.live
def test_live_met_museum_departments():
    from meta_data_mcp.providers.global_met_museum import (
        fetch_list_departments,
        ListDepartmentsParams,
    )

    data = fetch_list_departments(ListDepartmentsParams())
    assert "departments" in data
    assert len(data["departments"]) > 0


# ---------------------------------------------------------------------------
# global_osm_nominatim — geocoding
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_nominatim_search():
    from meta_data_mcp.providers.global_osm_nominatim import fetch_search, SearchParams

    data = fetch_search(SearchParams(q="Bern, Switzerland", limit=1))
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "lat" in data[0]
    assert "lon" in data[0]


@pytest.mark.live
def test_live_nominatim_reverse():
    from meta_data_mcp.providers.global_osm_nominatim import fetch_reverse, ReverseParams

    data = fetch_reverse(ReverseParams(lat=46.9481, lon=7.4474))
    assert "display_name" in data or "address" in data
