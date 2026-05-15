"""Tests for the global-gdelt provider."""

from unittest.mock import Mock, patch

import httpx
import pytest

from meta_data_mcp.providers.global_gdelt import (
    GdeltArticleSearchParams,
    GdeltVolumeTimelineParams,
    fetch_gdelt_article_search,
    fetch_gdelt_volume_timeline,
    handle_gdelt_article_search,
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


def test_article_search_sends_required_params():
    payload = {"articles": [{"url": "https://x.com/a", "title": "T"}]}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok(payload)
        params = GdeltArticleSearchParams(
            query='"supply chain" sourcelang:eng',
            timespan="7d",
            sort="DateDesc",
        )
        result = fetch_gdelt_article_search(params)
        assert len(result["articles"]) == 1
        sent = mock_get.call_args[1]["params"]
        assert sent["query"] == '"supply chain" sourcelang:eng'
        assert sent["mode"] == "ArtList"
        assert sent["format"] == "json"
        assert sent["timespan"] == "7d"
        assert sent["sort"] == "DateDesc"


def test_article_search_clamps_maxrecords():
    with pytest.raises(Exception):
        GdeltArticleSearchParams(query="x", maxrecords=0)
    with pytest.raises(Exception):
        GdeltArticleSearchParams(query="x", maxrecords=251)


def test_article_search_rejects_empty_query():
    with pytest.raises(Exception):
        GdeltArticleSearchParams(query="")


def test_volume_timeline_default_mode():
    payload = {"timeline": [{"date": "20260515", "value": 1.2}]}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok(payload)
        fetch_gdelt_volume_timeline(GdeltVolumeTimelineParams(query="floods"))
        sent = mock_get.call_args[1]["params"]
        assert sent["mode"] == "TimelineVol"


def test_volume_timeline_custom_mode():
    payload = {"timeline": []}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok(payload)
        fetch_gdelt_volume_timeline(
            GdeltVolumeTimelineParams(query="floods", timeline_mode="TimelineTone")
        )
        assert mock_get.call_args[1]["params"]["mode"] == "TimelineTone"


@pytest.mark.anyio
async def test_handle_article_search():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"articles": [{"title": "Hello GDELT"}]})
        result = await handle_gdelt_article_search({"query": "test"})
        assert "Hello GDELT" in result[0].text


@pytest.mark.anyio
async def test_handle_translates_503():
    from meta_data_mcp.errors import UpstreamError
    from meta_data_mcp import utils

    req = httpx.Request("GET", "https://api.gdeltproject.org/api/v2/doc/doc")
    resp = httpx.Response(status_code=503, request=req)
    status_err = httpx.HTTPStatusError("down", request=req, response=resp)

    with patch("httpx.get") as mock_get:
        mock_get.return_value.raise_for_status = Mock(side_effect=status_err)
        mock_get.return_value.status_code = 503
        mock_get.return_value.headers = {}
        with patch.object(utils.time, "sleep", lambda s: None):
            with pytest.raises(UpstreamError) as exc_info:
                await handle_gdelt_article_search({"query": "x"})
        assert exc_info.value.provider == "global-gdelt"
