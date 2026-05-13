import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_openalex import (
    handle_openalex_search_works,
    handle_openalex_get_work,
    handle_openalex_search_authors,
    handle_openalex_get_author,
    handle_openalex_search_institutions,
    handle_openalex_search_sources,
    handle_openalex_search_concepts,
    handle_openalex_search_publishers,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_openalex_search_works_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "meta": {"count": 1},
            "results": [
                {
                    "id": "https://openalex.org/W123",
                    "title": "Attention Is All You Need",
                }
            ],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openalex_search_works({"search": "attention"})
        assert "Attention Is All You Need" in result[0].text


@pytest.mark.anyio
async def test_openalex_search_works_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("OpenAlex down")

        with pytest.raises(httpx.HTTPError):
            await handle_openalex_search_works({"search": "x"})


@pytest.mark.anyio
async def test_openalex_search_works_adds_mailto():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"meta": {}, "results": []}
        mock_get.return_value.raise_for_status = Mock()

        await handle_openalex_search_works({"search": "x"})

        params = mock_get.call_args.kwargs.get("params", {})
        assert "mailto" in params
        assert params["mailto"]  # non-empty


@pytest.mark.anyio
async def test_openalex_search_works_respects_contact_env(monkeypatch):
    monkeypatch.setenv("OPENDATA_MCP_CONTACT", "test@example.com")
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"meta": {}, "results": []}
        mock_get.return_value.raise_for_status = Mock()

        await handle_openalex_search_works({"search": "x"})

        params = mock_get.call_args.kwargs.get("params", {})
        assert params.get("mailto") == "test@example.com"


@pytest.mark.anyio
async def test_openalex_get_work_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1/abc",
            "title": "Specific work",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openalex_get_work({"id": "W123"})
        assert "Specific work" in result[0].text


@pytest.mark.anyio
async def test_openalex_get_work_requires_id():
    with pytest.raises(ValueError):
        await handle_openalex_get_work({})


@pytest.mark.anyio
async def test_openalex_search_authors_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "meta": {"count": 1},
            "results": [
                {"id": "https://openalex.org/A1", "display_name": "Geoffrey Hinton"}
            ],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openalex_search_authors({"search": "hinton"})
        assert "Geoffrey Hinton" in result[0].text


@pytest.mark.anyio
async def test_openalex_get_author_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "id": "https://openalex.org/A1",
            "display_name": "Geoffrey Hinton",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openalex_get_author({"id": "A1"})
        assert "Geoffrey Hinton" in result[0].text


@pytest.mark.anyio
async def test_openalex_search_institutions_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "meta": {"count": 1},
            "results": [{"display_name": "University of Toronto"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openalex_search_institutions({"search": "toronto"})
        assert "University of Toronto" in result[0].text


@pytest.mark.anyio
async def test_openalex_search_sources_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "meta": {"count": 1},
            "results": [{"display_name": "Nature"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openalex_search_sources({"search": "nature"})
        assert "Nature" in result[0].text


@pytest.mark.anyio
async def test_openalex_search_concepts_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "meta": {"count": 1},
            "results": [{"display_name": "Machine learning"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openalex_search_concepts({"search": "machine learning"})
        assert "Machine learning" in result[0].text


@pytest.mark.anyio
async def test_openalex_search_publishers_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "meta": {"count": 1},
            "results": [{"display_name": "Springer Nature"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openalex_search_publishers({"search": "springer"})
        assert "Springer Nature" in result[0].text
