import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.us_courtlistener import (
    CourtListenerListCourtsParams,
    CourtListenerListDocketsParams,
    CourtListenerListJudgesParams,
    CourtListenerSearchParams,
    handle_courtlistener_search,
    handle_courtlistener_list_courts,
    handle_courtlistener_get_opinion,
    handle_courtlistener_get_cluster,
    handle_courtlistener_list_judges,
    handle_courtlistener_get_judge,
    handle_courtlistener_list_dockets,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_courtlistener_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [{"id": 99, "caseName": "Foo v. Bar"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_courtlistener_search({"q": "Foo v. Bar"})
        assert "Foo v. Bar" in result[0].text


@pytest.mark.anyio
async def test_courtlistener_search_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("CourtListener down")

        with pytest.raises(httpx.HTTPError):
            await handle_courtlistener_search({"q": "anything"})


@pytest.mark.anyio
async def test_courtlistener_search_sends_auth_header_when_token_set(monkeypatch):
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "secret-token")
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"count": 0, "results": []}
        mock_get.return_value.raise_for_status = Mock()

        await handle_courtlistener_search({"q": "x"})

        # http_get is invoked with keyword args; inspect them.
        headers = mock_get.call_args.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Token secret-token"


@pytest.mark.anyio
async def test_courtlistener_search_omits_auth_header_when_no_token(monkeypatch):
    monkeypatch.delenv("COURTLISTENER_API_TOKEN", raising=False)
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"count": 0, "results": []}
        mock_get.return_value.raise_for_status = Mock()

        await handle_courtlistener_search({"q": "x"})

        headers = mock_get.call_args.kwargs.get("headers", {})
        assert "Authorization" not in headers


@pytest.mark.anyio
async def test_courtlistener_list_courts_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 2,
            "results": [{"id": "scotus"}, {"id": "ca9"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_courtlistener_list_courts({})
        assert "scotus" in result[0].text
        assert "ca9" in result[0].text


@pytest.mark.anyio
async def test_courtlistener_get_opinion_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "id": 1234,
            "plain_text": "The opinion of the court...",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_courtlistener_get_opinion({"opinion_id": 1234})
        assert "1234" in result[0].text
        assert "opinion of the court" in result[0].text


@pytest.mark.anyio
async def test_courtlistener_get_opinion_requires_id():
    with pytest.raises(ValueError):
        await handle_courtlistener_get_opinion({})


@pytest.mark.anyio
async def test_courtlistener_get_cluster_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "id": 555,
            "case_name": "Roe v. Wade",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_courtlistener_get_cluster({"cluster_id": 555})
        assert "Roe v. Wade" in result[0].text


@pytest.mark.anyio
async def test_courtlistener_list_judges_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [{"id": 7, "name_first": "Ruth", "name_last": "Ginsburg"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_courtlistener_list_judges({"name_last": "Ginsburg"})
        assert "Ginsburg" in result[0].text


@pytest.mark.anyio
async def test_courtlistener_get_judge_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "id": 42,
            "name_first": "Sonia",
            "name_last": "Sotomayor",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_courtlistener_get_judge({"person_id": 42})
        assert "Sotomayor" in result[0].text


@pytest.mark.anyio
async def test_courtlistener_list_dockets_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "count": 1,
            "results": [{"id": 9001, "docket_number": "21-1234"}],
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_courtlistener_list_dockets(
            {"court": "scotus", "docket_number": "21-1234"}
        )
        assert "21-1234" in result[0].text


@pytest.mark.parametrize(
    "model_cls",
    [
        CourtListenerSearchParams,
        CourtListenerListCourtsParams,
        CourtListenerListJudgesParams,
        CourtListenerListDocketsParams,
    ],
)
def test_courtlistener_page_schema_keeps_default_and_optional(model_cls):
    schema = model_cls.model_json_schema()
    assert schema["properties"]["page"]["default"] == 1
    assert "required" not in schema or "page" not in schema["required"]
