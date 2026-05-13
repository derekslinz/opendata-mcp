import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_arxiv import (
    handle_arxiv_query,
    handle_arxiv_search_by_title,
    handle_arxiv_search_by_author,
    handle_arxiv_search_by_category,
    handle_arxiv_get_paper,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


ATOM_SAMPLE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<feed xmlns="http://www.w3.org/2005/Atom">'
    "<entry><id>http://arxiv.org/abs/2104.08653</id>"
    "<title>Attention Is All You Need</title>"
    "<author><name>Ashish Vaswani</name></author>"
    '<category term="cs.LG"/>'
    "</entry></feed>"
)


@pytest.mark.anyio
async def test_arxiv_query_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_arxiv_query({"search_query": "all:attention"})
        assert "Attention Is All You Need" in result[0].text


@pytest.mark.anyio
async def test_arxiv_query_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("arXiv down")

        with pytest.raises(httpx.HTTPError):
            await handle_arxiv_query({"search_query": "all:anything"})


@pytest.mark.anyio
async def test_arxiv_query_requires_search_query():
    with pytest.raises(ValueError):
        await handle_arxiv_query({})


@pytest.mark.anyio
async def test_arxiv_search_by_title_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_arxiv_search_by_title({"title": "Attention"})
        assert "Attention Is All You Need" in result[0].text


@pytest.mark.anyio
async def test_arxiv_search_by_author_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_arxiv_search_by_author({"author": "Vaswani"})
        assert "Ashish Vaswani" in result[0].text


@pytest.mark.anyio
async def test_arxiv_search_by_category_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_arxiv_search_by_category({"category": "cs.LG"})
        assert "cs.LG" in result[0].text


@pytest.mark.anyio
async def test_arxiv_get_paper_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_arxiv_get_paper({"arxiv_id": "2104.08653"})
        assert "2104.08653" in result[0].text
