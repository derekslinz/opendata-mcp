from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import httpx
import pytest

from meta_data_mcp import utils


def _response(
    name: str = "ok",
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> Mock:
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = {"name": name}
    response.text = f'{{"name":"{name}"}}'
    if 400 <= status_code < 600:

        def _raise() -> None:
            raise httpx.HTTPStatusError(
                f"status {status_code}",
                request=Mock(spec=httpx.Request),
                response=response,
            )

        response.raise_for_status = Mock(side_effect=_raise)
    else:
        response.raise_for_status = Mock()
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


def test_cache_isolates_auth_from_anonymous(monkeypatch):
    """Authenticated and anonymous responses must never share a cache entry."""
    now = 300.0
    monkeypatch.setattr(utils.time, "monotonic", lambda: now)
    utils._response_cache.clear()

    anon_resp = _response("anonymous")
    auth_resp = _response("authenticated")
    mock_get = Mock(side_effect=[anon_resp, auth_resp])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    r_anon = utils.http_get("https://example.test/api", cache_ttl=60)
    r_auth = utils.http_get(
        "https://example.test/api",
        cache_ttl=60,
        headers={"Authorization": "Token abc"},
    )

    assert r_anon is anon_resp
    assert r_auth is auth_resp
    assert mock_get.call_count == 2

    # And confirm both are independently cached
    r_anon_cached = utils.http_get("https://example.test/api", cache_ttl=60)
    r_auth_cached = utils.http_get(
        "https://example.test/api",
        cache_ttl=60,
        headers={"Authorization": "Token abc"},
    )
    assert r_anon_cached is anon_resp
    assert r_auth_cached is auth_resp
    assert mock_get.call_count == 2


def test_http_get_retries_on_429_with_retry_after(monkeypatch):
    """A 429 followed by a 200 should result in two calls, returning success."""
    utils._response_cache.clear()
    monkeypatch.setenv("OPENDATA_MCP_HTTP_RETRIES", "2")
    sleeps: list[float] = []
    monkeypatch.setattr(utils.time, "sleep", lambda s: sleeps.append(s))

    rate_limited = _response(
        "rate-limited", status_code=429, headers={"Retry-After": "0"}
    )
    ok = _response("ok")
    mock_get = Mock(side_effect=[rate_limited, ok])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    result = utils.http_get("https://example.test/api")

    assert result is ok
    assert mock_get.call_count == 2
    assert sleeps == [0.0]


def test_http_get_retries_on_503(monkeypatch):
    """Two 503s followed by a 200 should result in three calls."""
    utils._response_cache.clear()
    monkeypatch.setenv("OPENDATA_MCP_HTTP_RETRIES", "2")
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    fail1 = _response("fail1", status_code=503)
    fail2 = _response("fail2", status_code=503)
    ok = _response("ok")
    mock_get = Mock(side_effect=[fail1, fail2, ok])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    result = utils.http_get("https://example.test/api")

    assert result is ok
    assert mock_get.call_count == 3


def test_http_get_gives_up_after_max_retries(monkeypatch):
    """When retries are exhausted, http_get must raise HTTPStatusError."""
    utils._response_cache.clear()
    monkeypatch.setenv("OPENDATA_MCP_HTTP_RETRIES", "1")
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    fail1 = _response("fail1", status_code=503)
    fail2 = _response("fail2", status_code=503)
    mock_get = Mock(side_effect=[fail1, fail2])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    with pytest.raises(httpx.HTTPStatusError):
        utils.http_get("https://example.test/api")

    assert mock_get.call_count == 2


def test_http_get_no_retry_on_404(monkeypatch):
    """4xx other than 429 should raise immediately without retry."""
    utils._response_cache.clear()
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    not_found = _response("nope", status_code=404)
    mock_get = Mock(side_effect=[not_found])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    with pytest.raises(httpx.HTTPStatusError):
        utils.http_get("https://example.test/api")

    assert mock_get.call_count == 1


def test_cache_isolates_lowercase_auth_header(monkeypatch):
    """Lowercase 'authorization' and 'cookie' must also be detected as auth."""
    now = 400.0
    monkeypatch.setattr(utils.time, "monotonic", lambda: now)
    utils._response_cache.clear()

    anon_resp = _response("anonymous")
    auth_resp = _response("authenticated-lower")
    mock_get = Mock(side_effect=[anon_resp, auth_resp])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    r_anon = utils.http_get("https://example.test/api", cache_ttl=60)
    r_auth = utils.http_get(
        "https://example.test/api",
        cache_ttl=60,
        headers={"authorization": "Token xyz"},
    )

    assert r_anon is anon_resp
    assert r_auth is auth_resp
    assert mock_get.call_count == 2


def test_http_get_retries_on_429_with_http_date_retry_after(monkeypatch):
    """Retry-After as HTTP-date should be honored and capped at 30 s."""
    utils._response_cache.clear()
    monkeypatch.setenv("OPENDATA_MCP_HTTP_RETRIES", "2")
    sleeps: list[float] = []
    monkeypatch.setattr(utils.time, "sleep", lambda s: sleeps.append(s))

    # An HTTP-date 5 seconds in the future → should sleep ~5 s (≤ 30 s cap)
    future = datetime.now(timezone.utc) + timedelta(seconds=5)
    retry_after_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")

    rate_limited = _response(
        "rate-limited", status_code=429, headers={"Retry-After": retry_after_date}
    )
    ok = _response("ok")
    mock_get = Mock(side_effect=[rate_limited, ok])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    result = utils.http_get("https://example.test/api")

    assert result is ok
    assert mock_get.call_count == 2
    assert len(sleeps) == 1
    assert 4.0 <= sleeps[0] <= 6.0


def test_http_get_retry_after_capped_at_30s(monkeypatch):
    """Retry-After values above 30 s must be capped to 30 s."""
    utils._response_cache.clear()
    monkeypatch.setenv("OPENDATA_MCP_HTTP_RETRIES", "2")
    sleeps: list[float] = []
    monkeypatch.setattr(utils.time, "sleep", lambda s: sleeps.append(s))

    # Retry-After: 120 should be clamped to 30
    rate_limited = _response(
        "rate-limited", status_code=429, headers={"Retry-After": "120"}
    )
    ok = _response("ok")
    mock_get = Mock(side_effect=[rate_limited, ok])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    result = utils.http_get("https://example.test/api")

    assert result is ok
    assert mock_get.call_count == 2
    assert sleeps == [30.0]


def test_http_get_retries_env_var_invalid_falls_back_to_default(monkeypatch):
    """Non-numeric OPENDATA_MCP_HTTP_RETRIES falls back to default (2 retries)."""
    utils._response_cache.clear()
    monkeypatch.setenv("OPENDATA_MCP_HTTP_RETRIES", "not-a-number")
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    fail1 = _response("fail1", status_code=503)
    fail2 = _response("fail2", status_code=503)
    ok = _response("ok")
    mock_get = Mock(side_effect=[fail1, fail2, ok])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    # Default 2 retries → 3 total attempts, third succeeds
    result = utils.http_get("https://example.test/api")
    assert result is ok
    assert mock_get.call_count == 3


def test_http_get_retries_env_var_negative_treated_as_zero(monkeypatch):
    """Negative OPENDATA_MCP_HTTP_RETRIES is clamped to 0 (no retries)."""
    utils._response_cache.clear()
    monkeypatch.setenv("OPENDATA_MCP_HTTP_RETRIES", "-1")
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    fail = _response("fail", status_code=503)
    mock_get = Mock(side_effect=[fail])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    with pytest.raises(httpx.HTTPStatusError):
        utils.http_get("https://example.test/api")

    assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# provider= kwarg: health-registry feedback + ProviderError translation
# ---------------------------------------------------------------------------


def test_http_get_with_provider_records_success(monkeypatch):
    """Successful response records a health success for the provider."""
    from meta_data_mcp import health

    health.reset()
    utils._response_cache.clear()

    ok = _response("ok", status_code=200)
    mock_get = Mock(side_effect=[ok])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    # Seed a failure so we can observe the success undoing it.
    health.record_failure("test-provider")
    assert health.health_score("test-provider") < 1.0

    result = utils.http_get("https://example.test/api", provider="test-provider")
    assert result is ok
    assert health.health_score("test-provider") == 1.0


def test_http_get_with_provider_translates_404(monkeypatch):
    """A 404 with provider= raises NotFoundError and records a failure."""
    from meta_data_mcp import health
    from meta_data_mcp.errors import NotFoundError

    health.reset()
    utils._response_cache.clear()
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    not_found = _response("nope", status_code=404)
    mock_get = Mock(side_effect=[not_found])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    with pytest.raises(NotFoundError) as exc_info:
        utils.http_get("https://example.test/missing", provider="test-provider")

    err = exc_info.value
    assert err.provider == "test-provider"
    assert err.status == 404
    assert "example.test" not in str(err)
    assert health.health_score("test-provider") < 1.0


def test_http_get_with_provider_translates_network_error(monkeypatch):
    """A pre-response network error raises NetworkError and records a failure."""
    from meta_data_mcp import health
    from meta_data_mcp.errors import NetworkError

    health.reset()
    utils._response_cache.clear()
    # Network errors are retried (NetworkError.retryable=True); patch sleep so
    # the retry loop runs at zero wall time.
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    def _boom(*_args, **_kwargs):
        raise httpx.ConnectError("connect refused")

    monkeypatch.setattr(utils.httpx, "get", _boom)

    with pytest.raises(NetworkError) as exc_info:
        utils.http_get("https://example.test/api", provider="test-provider")

    assert exc_info.value.provider == "test-provider"
    assert exc_info.value.status is None
    assert health.health_score("test-provider") < 1.0


def test_http_post_with_provider_translates_network_error(monkeypatch):
    """http_post must mirror http_get on RequestError: NetworkError + retry + health."""
    from meta_data_mcp import health
    from meta_data_mcp.errors import NetworkError

    health.reset()
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    calls: list[int] = []

    def _boom(*_args, **_kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("read timeout")

    monkeypatch.setattr(utils.httpx, "post", _boom)

    with pytest.raises(NetworkError) as exc_info:
        utils.http_post(
            "https://example.test/api", json={"x": 1}, provider="test-provider"
        )

    assert exc_info.value.provider == "test-provider"
    assert exc_info.value.status is None
    # NetworkError.retryable=True is now honored at the kernel level — the
    # post helper should have retried before giving up.
    assert len(calls) >= 2
    assert health.health_score("test-provider") < 1.0


def test_http_get_without_provider_keeps_raw_httpx_errors(monkeypatch):
    """Without provider=, http_get preserves legacy raw-httpx behavior.

    The control here: seed a known degraded score for a *different* provider
    id, then call ``http_get`` without ``provider=`` and confirm the seeded
    score is unchanged. A bug that wrongly recorded failures under a default
    id would degrade *some* provider's score; seeding the only score in the
    registry lets us prove the call left health state untouched.
    """
    from meta_data_mcp import health

    health.reset()
    utils._response_cache.clear()
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)
    # Pin the health clock so the time-decay between record_failure and the
    # final score readback can't move the baseline; we want to assert the call
    # itself made no change.
    monkeypatch.setattr(health, "_clock", lambda: 1000.0)

    health.record_failure("control-provider", status=500)
    baseline = health.health_score("control-provider")
    assert baseline < 1.0  # sanity: seeded failure actually degraded the score.

    not_found = _response("nope", status_code=404)
    mock_get = Mock(side_effect=[not_found])
    monkeypatch.setattr(utils.httpx, "get", mock_get)

    # No provider= → raw httpx.HTTPStatusError, no health side-effect.
    with pytest.raises(httpx.HTTPStatusError):
        utils.http_get("https://example.test/missing")

    assert health.health_score("control-provider") == baseline
