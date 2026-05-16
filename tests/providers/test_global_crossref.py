import json

import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_crossref import (
    TOOLS,
    _crossref_works_to_shape_payload,
    handle_crossref_works_search,
    handle_crossref_get_work,
    handle_crossref_works_by_author,
    handle_crossref_works_by_title,
    handle_crossref_journals_search,
    handle_crossref_get_journal,
    handle_crossref_funders_search,
)
from meta_data_mcp.ui_resources.shape_records_v1 import URI as RECORDS_URI


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_crossref_works_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "message": {
                "total-results": 1,
                "items": [
                    {
                        "DOI": "10.1038/nature12373",
                        "title": ["The structure of something"],
                    }
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_crossref_works_search({"query": "structure"})
        assert "10.1038/nature12373" in result[0].text


@pytest.mark.anyio
async def test_crossref_works_search_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Crossref down")

        with pytest.raises(httpx.HTTPError):
            await handle_crossref_works_search({"query": "anything"})


@pytest.mark.anyio
async def test_crossref_get_work_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "message": {
                "DOI": "10.1038/nature12373",
                "title": ["Specific paper"],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_crossref_get_work({"doi": "10.1038/nature12373"})
        assert "Specific paper" in result[0].text


@pytest.mark.anyio
async def test_crossref_get_work_url_encodes_doi():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok", "message": {}}
        mock_get.return_value.raise_for_status = Mock()

        await handle_crossref_get_work({"doi": "10.1038/nature12373"})

        called_url = mock_get.call_args[0][0]
        # Slash in DOI must be URL-encoded as %2F
        assert "10.1038%2Fnature12373" in called_url


@pytest.mark.anyio
async def test_crossref_works_by_author_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "message": {
                "total-results": 1,
                "items": [{"DOI": "10.1/abc", "author": [{"family": "Hinton"}]}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_crossref_works_by_author({"author": "Hinton"})
        assert "Hinton" in result[0].text


@pytest.mark.anyio
async def test_crossref_works_by_title_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "message": {
                "total-results": 1,
                "items": [{"title": ["Deep Learning"]}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_crossref_works_by_title({"title": "Deep Learning"})
        assert "Deep Learning" in result[0].text


@pytest.mark.anyio
async def test_crossref_journals_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "message": {
                "total-results": 1,
                "items": [{"title": "Nature", "ISSN": ["1476-4687"]}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_crossref_journals_search({"query": "nature"})
        assert "Nature" in result[0].text


@pytest.mark.anyio
async def test_crossref_get_journal_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "message": {"title": "Nature", "ISSN": ["1476-4687"]},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_crossref_get_journal({"issn": "1476-4687"})
        assert "Nature" in result[0].text


@pytest.mark.anyio
async def test_crossref_funders_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "message": {
                "total-results": 1,
                "items": [{"name": "National Science Foundation"}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_crossref_funders_search({"query": "science"})
        assert "National Science Foundation" in result[0].text


# ---------------------------------------------------------------------------
# Phase 4: MCP Apps shape primitive binding for crossref-works-search.
# ---------------------------------------------------------------------------


def test_crossref_adapter_flattens_message_items_to_rows():
    raw = {
        "status": "ok",
        "message": {
            "total-results": 1,
            "items": [
                {
                    "DOI": "10.1038/nature12373",
                    "title": ["The structure of something"],
                    "author": [
                        {"given": "Alice", "family": "Smith"},
                        {"given": "Bob", "family": "Jones"},
                    ],
                    "container-title": ["Nature"],
                    "publisher": "Springer",
                    "type": "journal-article",
                    "published-print": {"date-parts": [[2023, 5, 1]]},
                    "is-referenced-by-count": 42,
                }
            ],
        },
    }
    payload = _crossref_works_to_shape_payload(raw)
    assert payload["total_results"] == 1
    row = payload["rows"][0]
    assert row["DOI"] == "10.1038/nature12373"
    assert row["title"] == "The structure of something"
    assert "Alice Smith" in row["authors"] and "Bob Jones" in row["authors"]
    assert row["container_title"] == "Nature"
    assert row["type"] == "journal-article"
    assert row["is_referenced_by_count"] == 42
    assert payload["default_facets"] == ["type", "publisher", "container_title"]


def test_crossref_adapter_handles_missing_items():
    assert _crossref_works_to_shape_payload({})["rows"] == []
    assert _crossref_works_to_shape_payload({"message": {}})["rows"] == []


def test_works_search_tool_binds_to_records_shape_primitive():
    tool = next(t for t in TOOLS if t.name == "crossref-works-search")
    assert tool.meta == {"ui": {"resourceUri": RECORDS_URI}}
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert wire.get("_meta", {}).get("ui", {}).get("resourceUri") == RECORDS_URI


@pytest.mark.anyio
async def test_crossref_works_search_returns_shape_payload():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": "ok",
            "message": {
                "total-results": 1,
                "items": [
                    {
                        "DOI": "10.1038/nature12373",
                        "title": ["The structure of something"],
                    }
                ],
            },
        }
        mock_get.return_value.raise_for_status = Mock()
        result = await handle_crossref_works_search({"query": "structure"})
        body = json.loads(result[0].text)
        assert body["rows"][0]["DOI"] == "10.1038/nature12373"
        assert "schema" in body
