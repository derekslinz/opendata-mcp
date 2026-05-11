import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_smithsonian import (
    handle_smithsonian_search,
    handle_smithsonian_get_content,
    handle_smithsonian_list_terms,
    handle_smithsonian_search_category,
    handle_smithsonian_stats,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("SMITHSONIAN_API_KEY", "test-key-123")


@pytest.mark.anyio
async def test_smithsonian_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": 200,
            "response": {
                "rowCount": 1,
                "rows": [{"id": "abc", "title": "Apollo capsule"}],
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_smithsonian_search({"q": "apollo"})
        assert "Apollo capsule" in result[0].text


@pytest.mark.anyio
async def test_smithsonian_search_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Smithsonian down")

        with pytest.raises(httpx.HTTPError):
            await handle_smithsonian_search({"q": "anything"})


@pytest.mark.anyio
async def test_smithsonian_search_requires_api_key(monkeypatch):
    monkeypatch.delenv("SMITHSONIAN_API_KEY", raising=False)
    with pytest.raises(ValueError):
        await handle_smithsonian_search({"q": "apollo"})


@pytest.mark.anyio
async def test_smithsonian_get_content_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": 200,
            "response": {"id": "rec-1", "title": "Hope Diamond"},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_smithsonian_get_content({"id": "rec-1"})
        assert "Hope Diamond" in result[0].text


@pytest.mark.anyio
async def test_smithsonian_list_terms_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": 200,
            "response": {"terms": ["Apollo", "Aviation"]},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_smithsonian_list_terms(
            {"category": "topic", "starts_with": "Ap"}
        )
        assert "Apollo" in result[0].text


@pytest.mark.anyio
async def test_smithsonian_search_category_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": 200,
            "response": {"rowCount": 1, "rows": [{"title": "Modern art piece"}]},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_smithsonian_search_category(
            {"category": "art_design", "q": "modern"}
        )
        assert "Modern art piece" in result[0].text


@pytest.mark.anyio
async def test_smithsonian_stats_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "status": 200,
            "response": {"counts": {"total": 4500000}},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_smithsonian_stats({})
        assert "4500000" in result[0].text
