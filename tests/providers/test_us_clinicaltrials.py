import pytest
from unittest.mock import patch, Mock
import httpx
from meta_data_mcp.providers.us_clinicaltrials import (
    handle_search_studies,
    handle_get_study,
    handle_search_by_condition,
    handle_search_by_intervention,
    handle_search_by_location,
    handle_list_stats,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_ctgov_search_studies_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "studies": [
                {"protocolSection": {"identificationModule": {"nctId": "NCT01234567"}}}
            ],
            "nextPageToken": "abc",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_studies({"query_term": "cancer"})
        assert len(result) == 1
        assert "NCT01234567" in result[0].text


@pytest.mark.anyio
async def test_ctgov_search_studies_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")
        with pytest.raises(httpx.HTTPError):
            await handle_search_studies({"query_term": "cancer"})


@pytest.mark.anyio
async def test_ctgov_get_study_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000001",
                    "briefTitle": "Sample Study",
                }
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_study({"nctId": "NCT00000001"})
        assert "NCT00000001" in result[0].text
        assert "Sample Study" in result[0].text


@pytest.mark.anyio
async def test_ctgov_get_study_requires_nctid():
    with pytest.raises(ValueError):
        await handle_get_study({})


@pytest.mark.anyio
async def test_ctgov_search_by_condition_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "studies": [{"condition": "diabetes"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_by_condition({"condition": "diabetes"})
        assert "diabetes" in result[0].text


@pytest.mark.anyio
async def test_ctgov_search_by_intervention_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "studies": [{"intervention": "metformin"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_by_intervention({"intervention": "metformin"})
        assert "metformin" in result[0].text


@pytest.mark.anyio
async def test_ctgov_search_by_location_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"studies": [{"location": "Boston"}]}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_by_location({"location": "Boston"})
        assert "Boston" in result[0].text


@pytest.mark.anyio
async def test_ctgov_list_stats_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"totalStudies": 500000}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_stats()
        assert "500000" in result[0].text
