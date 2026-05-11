import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_open_library import (
    handle_openlibrary_search_books,
    handle_openlibrary_search_authors,
    handle_openlibrary_get_work,
    handle_openlibrary_get_edition,
    handle_openlibrary_get_author,
    handle_openlibrary_isbn_lookup,
    handle_openlibrary_subject,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_openlibrary_search_books_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "numFound": 1,
            "docs": [
                {
                    "title": "The Lord of the Rings",
                    "author_name": ["J.R.R. Tolkien"],
                    "key": "/works/OL27448W",
                }
            ],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openlibrary_search_books(
            {"title": "lord of the rings", "limit": 1}
        )
        assert "Tolkien" in result[0].text


@pytest.mark.anyio
async def test_openlibrary_search_books_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("openlibrary down")

        with pytest.raises(httpx.HTTPError):
            await handle_openlibrary_search_books({"q": "anything"})


@pytest.mark.anyio
async def test_openlibrary_search_authors_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "numFound": 1,
            "docs": [{"name": "J.R.R. Tolkien", "key": "OL26320A"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openlibrary_search_authors({"q": "tolkien"})
        assert "Tolkien" in result[0].text


@pytest.mark.anyio
async def test_openlibrary_search_authors_missing_q():
    with pytest.raises(Exception):
        await handle_openlibrary_search_authors({})


@pytest.mark.anyio
async def test_openlibrary_get_work_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "title": "The Lord of the Rings",
            "key": "/works/OL27448W",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openlibrary_get_work({"work_id": "OL27448W"})
        assert "Lord of the Rings" in result[0].text


@pytest.mark.anyio
async def test_openlibrary_get_edition_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "title": "The Fellowship of the Ring",
            "isbn_13": ["9780261103573"],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openlibrary_get_edition({"edition_id": "OL7353617M"})
        assert "Fellowship of the Ring" in result[0].text


@pytest.mark.anyio
async def test_openlibrary_get_author_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "name": "J.R.R. Tolkien",
            "birth_date": "3 January 1892",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openlibrary_get_author({"author_id": "OL26320A"})
        assert "Tolkien" in result[0].text


@pytest.mark.anyio
async def test_openlibrary_isbn_lookup_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "title": "The Hobbit",
            "isbn_13": ["9780261103283"],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openlibrary_isbn_lookup({"isbn": "9780261103283"})
        assert "Hobbit" in result[0].text


@pytest.mark.anyio
async def test_openlibrary_subject_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "name": "science_fiction",
            "work_count": 12345,
            "works": [{"title": "Dune"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_openlibrary_subject(
            {"subject": "science_fiction", "limit": 5}
        )
        assert "Dune" in result[0].text
