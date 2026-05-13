from unittest.mock import Mock

import httpx

from opendata_mcp import utils


def _response(name: str) -> Mock:
    response = Mock(spec=httpx.Response)
    response.raise_for_status = Mock()
    response.json.return_value = {"name": name}
    response.text = f'{{"name":"{name}"}}'
    return response


def test_http_get_cache_hit_and_expiry(monkeypatch):
    now = 100.0
    monkeypatch.setattr(utils.time, "monotonic", lambda: now)
    utils._response_cache.clear()

    first = _response("first")
    second = _response("second")
    mock_get = Mock(side_effect=[first, second])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    r1 = utils.http_get("https://example.test/api", cache_ttl=10)
    r2 = utils.http_get("https://example.test/api", cache_ttl=10)

    assert r1 is first
    assert r2 is first
    assert mock_get.call_count == 1

    now = 111.0
    r3 = utils.http_get("https://example.test/api", cache_ttl=10)
    assert r3 is second
    assert mock_get.call_count == 2


def test_http_get_custom_ttl_does_not_change_default_ttl(monkeypatch):
    now = 200.0
    monkeypatch.setattr(utils.time, "monotonic", lambda: now)
    monkeypatch.setattr(utils, "_CACHE_DEFAULT_TTL", 5.0)
    utils._response_cache.clear()

    resp_a1 = _response("a1")
    resp_b1 = _response("b1")
    resp_a2 = _response("a2")
    mock_get = Mock(side_effect=[resp_a1, resp_b1, resp_a2])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    utils.http_get("https://example.test/a", cache_ttl=1)
    utils.http_get("https://example.test/b")

    now = 202.0
    a = utils.http_get("https://example.test/a", cache_ttl=1)
    b = utils.http_get("https://example.test/b")

    assert a is resp_a2
    assert b is resp_b1
    assert mock_get.call_count == 3
