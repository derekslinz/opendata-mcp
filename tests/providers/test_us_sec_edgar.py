import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.us_sec_edgar import (
    TOOLS,
    TOOLS_HANDLERS,
    handle_edgar_get_company_submissions,
    handle_edgar_get_company_concept,
    handle_edgar_get_company_facts,
    handle_edgar_get_frames,
    handle_edgar_list_tickers,
    handle_edgar_search_by_ticker,
    handle_edgar_search_by_name,
    _pad_cik,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_tools_registered():
    names = [t.name for t in TOOLS]
    for name in names:
        assert name in TOOLS_HANDLERS


def test_pad_cik():
    assert _pad_cik("320193") == "0000320193"
    assert _pad_cik(320193) == "0000320193"
    assert _pad_cik("0000320193") == "0000320193"


@pytest.mark.anyio
async def test_edgar_get_company_submissions_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "cik": "320193",
            "name": "Apple Inc.",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_edgar_get_company_submissions({"cik": "320193"})
        assert len(result) == 1
        assert "Apple" in result[0].text


@pytest.mark.anyio
async def test_edgar_get_company_submissions_missing_cik():
    with pytest.raises(ValueError):
        await handle_edgar_get_company_submissions({})


@pytest.mark.anyio
async def test_edgar_get_company_concept_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "cik": 320193,
            "tag": "Revenues",
            "units": {"USD": [{"val": 100, "fy": 2023}]},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_edgar_get_company_concept(
            {"cik": "320193", "concept": "Revenues"}
        )
        assert "Revenues" in result[0].text


@pytest.mark.anyio
async def test_edgar_get_company_facts_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "cik": 320193,
            "facts": {"us-gaap": {"Revenues": {}}},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_edgar_get_company_facts({"cik": "320193"})
        assert "facts" in result[0].text


@pytest.mark.anyio
async def test_edgar_get_frames_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "tag": "Revenues",
            "data": [{"cik": 1, "val": 100}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_edgar_get_frames(
            {"concept": "Revenues", "year": 2023, "quarter": 1}
        )
        assert "Revenues" in result[0].text


@pytest.mark.anyio
async def test_edgar_list_tickers_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_edgar_list_tickers()
        assert "AAPL" in result[0].text


@pytest.mark.anyio
async def test_edgar_search_by_ticker_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_edgar_search_by_ticker({"ticker": "AAPL"})
        assert "Apple" in result[0].text
        assert "0000320193" in result[0].text


@pytest.mark.anyio
async def test_edgar_search_by_ticker_not_found():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_edgar_search_by_ticker({"ticker": "ZZZZ"})
        assert "No company found" in result[0].text


@pytest.mark.anyio
async def test_edgar_search_by_name_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_edgar_search_by_name({"name": "apple"})
        assert "Apple" in result[0].text


@pytest.mark.anyio
async def test_edgar_get_company_submissions_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_edgar_get_company_submissions({"cik": "320193"})
