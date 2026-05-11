import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.us_federal_register import (
    handle_fedreg_search_documents,
    handle_fedreg_get_document,
    handle_fedreg_list_agencies,
    handle_fedreg_get_agency,
    handle_fedreg_public_inspection,
    handle_fedreg_list_executive_orders,
    handle_fedreg_suggested_searches,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_fedreg_search_documents_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [
                {
                    "document_number": "2024-12345",
                    "title": "Clean Air Act amendments",
                }
            ],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fedreg_search_documents({"term": "clean air"})
        assert "Clean Air Act amendments" in result[0].text


@pytest.mark.anyio
async def test_fedreg_search_documents_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("FedReg down")

        with pytest.raises(httpx.HTTPError):
            await handle_fedreg_search_documents({"term": "x"})


@pytest.mark.anyio
async def test_fedreg_search_documents_passes_term_filter():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"count": 0, "results": []}
        mock_get.return_value.raise_for_status = Mock()

        await handle_fedreg_search_documents({"term": "ozone", "per_page": 5})

        params = mock_get.call_args.kwargs.get("params", {})
        assert params.get("conditions[term]") == "ozone"
        assert params.get("per_page") == 5


@pytest.mark.anyio
async def test_fedreg_get_document_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "document_number": "2024-12345",
            "title": "Rule X",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fedreg_get_document({"document_number": "2024-12345"})
        assert "Rule X" in result[0].text
        assert "2024-12345" in result[0].text


@pytest.mark.anyio
async def test_fedreg_get_document_requires_document_number():
    with pytest.raises(ValueError):
        await handle_fedreg_get_document({})


@pytest.mark.anyio
async def test_fedreg_list_agencies_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"slug": "environmental-protection-agency", "name": "EPA"},
            {"slug": "department-of-energy", "name": "DOE"},
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fedreg_list_agencies({})
        assert "EPA" in result[0].text
        assert "environmental-protection-agency" in result[0].text


@pytest.mark.anyio
async def test_fedreg_get_agency_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "slug": "environmental-protection-agency",
            "name": "Environmental Protection Agency",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fedreg_get_agency(
            {"slug": "environmental-protection-agency"}
        )
        assert "Environmental Protection Agency" in result[0].text


@pytest.mark.anyio
async def test_fedreg_public_inspection_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [{"document_number": "PI-1", "title": "Pre-pub"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fedreg_public_inspection({"available_on": "2024-05-10"})
        assert "Pre-pub" in result[0].text


@pytest.mark.anyio
async def test_fedreg_list_executive_orders_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [
                {
                    "document_number": "2024-99999",
                    "title": "Executive Order on Energy",
                }
            ],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fedreg_list_executive_orders({"president": "joe-biden"})
        assert "Executive Order on Energy" in result[0].text

        params = mock_get.call_args.kwargs.get("params", {})
        assert params.get("conditions[presidential_document_type]") == "executive_order"


@pytest.mark.anyio
async def test_fedreg_suggested_searches_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = [
            {"title": "Climate change", "slug": "climate-change"}
        ]
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_fedreg_suggested_searches({"sections": "environment"})
        assert "Climate change" in result[0].text
