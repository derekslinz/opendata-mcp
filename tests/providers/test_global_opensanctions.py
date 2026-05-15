"""Tests for the global-opensanctions provider."""

from unittest.mock import Mock, patch

import httpx
import pytest

from meta_data_mcp.providers.global_opensanctions import (
    OpenSanctionsGetEntityParams,
    OpenSanctionsSearchParams,
    fetch_opensanctions_get_entity,
    fetch_opensanctions_search,
    handle_opensanctions_search,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _ok(payload: dict) -> Mock:
    r = Mock()
    r.json.return_value = payload
    r.raise_for_status = Mock()
    r.status_code = 200
    r.headers = {}
    return r


def test_search_default_dataset_in_path():
    payload = {"results": [{"id": "NK-test", "schema": "Person"}]}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok(payload)
        result = fetch_opensanctions_search(OpenSanctionsSearchParams(query="putin"))
        assert result["results"][0]["id"] == "NK-test"
        assert "/search/default" in mock_get.call_args[0][0]
        assert mock_get.call_args[1]["params"]["q"] == "putin"


def test_search_custom_dataset():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"results": []})
        fetch_opensanctions_search(
            OpenSanctionsSearchParams(query="acme corp", dataset="us_ofac_sdn")
        )
        assert "/search/us_ofac_sdn" in mock_get.call_args[0][0]


def test_search_schema_alias_threads_through():
    """The schema_ field uses alias='schema' to avoid Python keyword collision."""
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"results": []})
        # By alias 'schema'
        params = OpenSanctionsSearchParams.model_validate(
            {"query": "x", "schema": "Person"}
        )
        fetch_opensanctions_search(params)
        assert mock_get.call_args[1]["params"]["schema"] == "Person"


@pytest.mark.anyio
async def test_handle_search_accepts_schema_alias_from_mcp_args():
    """LLM-supplied arguments will use the alias 'schema'; the handler must accept it.

    Previously the handler used OpenSanctionsSearchParams(**arguments) which
    would reject {'schema': 'Person'} because 'schema' is not a valid Python
    keyword arg even with populate_by_name. The fix uses model_validate.
    """
    from meta_data_mcp.providers.global_opensanctions import handle_opensanctions_search

    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"results": []})
        # Simulate an MCP client passing the alias name as the LLM saw it.
        result = await handle_opensanctions_search(
            {"query": "putin", "schema": "Person", "countries": "ru"}
        )
        assert "results" in result[0].text
        assert mock_get.call_args[1]["params"]["schema"] == "Person"
        assert mock_get.call_args[1]["params"]["countries"] == "ru"


def test_search_countries_and_topics():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"results": []})
        fetch_opensanctions_search(
            OpenSanctionsSearchParams(
                query="x", countries="ru,by", topics="sanction,role.pep"
            )
        )
        sent = mock_get.call_args[1]["params"]
        assert sent["countries"] == "ru,by"
        assert sent["topics"] == "sanction,role.pep"


def test_search_validates_query_and_limit():
    with pytest.raises(Exception):
        OpenSanctionsSearchParams(query="")
    with pytest.raises(Exception):
        OpenSanctionsSearchParams(query="x", limit=0)
    with pytest.raises(Exception):
        OpenSanctionsSearchParams(query="x", limit=101)


def test_get_entity_path_param():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"id": "NK-abc", "schema": "Person"})
        result = fetch_opensanctions_get_entity(
            OpenSanctionsGetEntityParams(entity_id="NK-abc")
        )
        assert result["id"] == "NK-abc"
        assert "/entities/NK-abc" in mock_get.call_args[0][0]


def test_get_entity_rejects_empty_id():
    with pytest.raises(Exception):
        OpenSanctionsGetEntityParams(entity_id="")


def test_auth_header_sent_when_env_set(monkeypatch):
    monkeypatch.setenv("OPENSANCTIONS_API_KEY", "the-key")
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"results": []})
        fetch_opensanctions_search(OpenSanctionsSearchParams(query="x"))
        sent = mock_get.call_args[1]["headers"]
        assert sent["Authorization"] == "ApiKey the-key"


@pytest.mark.anyio
async def test_handle_search_translates_404():
    from meta_data_mcp.errors import NotFoundError

    req = httpx.Request("GET", "https://api.opensanctions.org/search/missing")
    resp = httpx.Response(status_code=404, request=req)
    status_err = httpx.HTTPStatusError("nope", request=req, response=resp)

    with patch("httpx.get") as mock_get:
        mock_get.return_value.raise_for_status = Mock(side_effect=status_err)
        mock_get.return_value.status_code = 404
        mock_get.return_value.headers = {}
        with pytest.raises(NotFoundError) as exc_info:
            await handle_opensanctions_search(
                {"query": "x", "dataset": "no_such_dataset"}
            )
        assert exc_info.value.provider == "global-opensanctions"
