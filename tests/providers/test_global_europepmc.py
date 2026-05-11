import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_europepmc import (
    handle_europepmc_search,
    handle_europepmc_get_article,
    handle_europepmc_references,
    handle_europepmc_citations,
    handle_europepmc_fulltext_xml,
    handle_europepmc_supplementaryfiles,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_europepmc_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "hitCount": 1,
            "resultList": {
                "result": [
                    {"id": "12345", "source": "MED", "title": "CRISPR gene editing"}
                ]
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_europepmc_search({"query": "CRISPR"})
        assert "CRISPR gene editing" in result[0].text


@pytest.mark.anyio
async def test_europepmc_search_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("EBI down")

        with pytest.raises(httpx.HTTPError):
            await handle_europepmc_search({"query": "anything"})


@pytest.mark.anyio
async def test_europepmc_search_requires_query():
    with pytest.raises(ValueError):
        await handle_europepmc_search({})


@pytest.mark.anyio
async def test_europepmc_get_article_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "result": {"id": "12345", "title": "A core paper", "authorList": {}},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_europepmc_get_article({"source": "MED", "id": "12345"})
        assert "A core paper" in result[0].text


@pytest.mark.anyio
async def test_europepmc_references_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "hitCount": 1,
            "referenceList": {"reference": [{"id": "999", "title": "Cited paper"}]},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_europepmc_references({"source": "MED", "id": "12345"})
        assert "Cited paper" in result[0].text


@pytest.mark.anyio
async def test_europepmc_citations_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "hitCount": 1,
            "citationList": {"citation": [{"id": "1001", "title": "Citing paper"}]},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_europepmc_citations({"source": "MED", "id": "12345"})
        assert "Citing paper" in result[0].text


@pytest.mark.anyio
async def test_europepmc_fulltext_xml_success():
    sample_xml = (
        '<?xml version="1.0"?>'
        "<article><front><title>Full text article</title></front></article>"
    )
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = sample_xml
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_europepmc_fulltext_xml({"source": "PMC", "id": "PMC1234"})
        assert "Full text article" in result[0].text


@pytest.mark.anyio
async def test_europepmc_supplementaryfiles_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "supplementaryFiles": [
                {"name": "table_s1.xlsx", "url": "http://example.com/s1.xlsx"}
            ]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_europepmc_supplementaryfiles(
            {"source": "PMC", "id": "PMC1234"}
        )
        assert "table_s1.xlsx" in result[0].text
