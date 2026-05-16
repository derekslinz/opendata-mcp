import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Sequence

import httpx
from mcp import types
from mcp.server import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from pydantic import AnyUrl

from meta_data_mcp import __version__

log = logging.getLogger(__name__)

# Maximum character length for tool/resource text responses.
MAX_RESPONSE_CHARS = 20_000

# ---------------------------------------------------------------------------
# TTL response cache
# ---------------------------------------------------------------------------

_CACHE_DEFAULT_TTL: float = float(os.getenv("OPENDATA_MCP_CACHE_TTL", "0"))
_CACHE_MAX_SIZE: int = 256


class _TTLCache:
    """Thread-safe in-memory TTL cache for HTTP responses.

    Evicts the oldest entry when the cache is full. Entries older than
    their individual TTL (or the default TTL) are treated as absent and
    evicted on next access.
    """

    def __init__(self, maxsize: int = _CACHE_MAX_SIZE, ttl: float = 60.0) -> None:
        self._cache: dict[str, tuple[float, Any, float]] = {}
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            ts, val, entry_ttl = entry
            if time.monotonic() - ts > entry_ttl:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, val: Any, ttl: float | None = None) -> None:
        with self._lock:
            if len(self._cache) >= self._maxsize:
                oldest = min(self._cache, key=lambda k: self._cache[k][0])
                del self._cache[oldest]
            self._cache[key] = (
                time.monotonic(),
                val,
                ttl if ttl is not None else self._ttl,
            )

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


_response_cache = _TTLCache(maxsize=_CACHE_MAX_SIZE, ttl=max(_CACHE_DEFAULT_TTL, 1.0))


def _cache_key(
    url: str, params: dict | None, accept: str, has_auth: bool = False
) -> str:
    """Hash a stable cache key. ``has_auth`` partitions authenticated and
    anonymous responses so they never share a cache entry — see the
    auth-aware cache key rationale in ``http_get``."""
    payload = json.dumps(
        {
            "url": url,
            "params": sorted((params or {}).items()),
            "accept": accept,
            "has_auth": bool(has_auth),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# HTTP retry helpers (429 / 5xx with Retry-After support)
# ---------------------------------------------------------------------------

_RETRY_AFTER_CAP_SECONDS: float = 30.0
_RETRY_BACKOFF_BASE: float = 0.5
_RETRY_BACKOFF_CAP_SECONDS: float = 8.0


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header value into seconds.

    Supports both formats from RFC 7231 section 7.1.3:
    - delta-seconds (e.g. ``"120"``)
    - HTTP-date (e.g. ``"Fri, 31 Dec 1999 23:59:59 GMT"``)

    Returns ``None`` if the value is missing or unparseable. Caller is
    responsible for capping the result.
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (dt - datetime.now(timezone.utc)).total_seconds()
    return max(0.0, delta)


def _retry_sleep_seconds(attempt: int, retry_after: str | None) -> float:
    """Compute the seconds to sleep before the next retry.

    ``Retry-After`` is honored when present (capped at 30s); otherwise an
    exponential backoff ``0.5 * 2**attempt`` is used (capped at 8s).
    """
    parsed = _parse_retry_after(retry_after)
    if parsed is not None:
        return min(parsed, _RETRY_AFTER_CAP_SECONDS)
    return min(_RETRY_BACKOFF_BASE * (2**attempt), _RETRY_BACKOFF_CAP_SECONDS)


def _default_user_agent() -> str:
    """Return the default User-Agent string for outbound HTTP requests.

    Several open-data APIs (Crossref, Europe PMC, OSM Nominatim, SEC EDGAR)
    require an identifiable User-Agent including a contact address. Callers
    may override `OPENDATA_MCP_CONTACT` via environment variable.
    """
    contact = os.getenv("OPENDATA_MCP_CONTACT")
    base = f"meta-data-mcp/{__version__} (+https://github.com/derekslinz/meta-data-mcp"
    if contact:
        return f"{base}; {contact})"
    return f"{base})"


def http_get(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    provider: str,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    cache_ttl: float | None = None,
) -> httpx.Response:
    """Perform a GET request with sensible defaults for open-data APIs.

    ``provider`` is **mandatory** — every kernel guarantee (typed errors,
    health feedback, URL-redacted exception messages) is keyed on a stable
    provider id. There is intentionally no anonymous path; callers that
    don't want the kernel contract should use ``httpx`` directly and
    accept full responsibility for the consequences.

    - Sets a default User-Agent identifying opendata-mcp (override via
      ``OPENDATA_MCP_CONTACT`` env var or ``headers`` argument).
    - Sets ``Accept: application/json`` by default; override via ``headers``.
    - Calls ``raise_for_status()`` so handlers see a clean exception path.
    - Optional response caching: pass ``cache_ttl=<seconds>`` to cache the
      response body. The global ``OPENDATA_MCP_CACHE_TTL`` env var sets the
      default TTL (default 0 = disabled). Only successful (2xx) responses
      are cached. Cache keys are partitioned by presence of ``Authorization``
      / ``Cookie`` headers so authenticated and anonymous responses never
      share an entry.
    - Retries on ``429`` and ``5xx`` responses and on ``httpx.RequestError``
      pre-response failures (configurable via ``OPENDATA_MCP_HTTP_RETRIES``
      env var, default 2 retries = 3 attempts). Honors ``Retry-After`` when
      present (capped at 30s); otherwise uses capped exponential backoff.
    - Translates ``httpx.HTTPStatusError`` and ``httpx.RequestError`` to the
      :mod:`meta_data_mcp.errors` ``ProviderError`` hierarchy and feeds
      :mod:`meta_data_mcp.health` (``record_success`` on 2xx, ``record_failure``
      on non-recoverable error).

    Args:
        url: The endpoint URL.
        params: Optional query parameters.
        provider: Stable provider id (e.g. ``"us-data-gov"``). Required.
        timeout: Request timeout in seconds (default 10.0).
        headers: Optional header overrides merged on top of defaults.
        cache_ttl: Seconds to cache this response. ``None`` uses the global
            default (``OPENDATA_MCP_CACHE_TTL`` env var, default 0 = off).

    Returns:
        The httpx.Response (already status-checked). When served from cache
        the object is a lightweight stand-in with ``.json()`` and ``.text``
        populated from the cached data.

    Raises:
        meta_data_mcp.errors.ProviderError: subclass appropriate to the
            failure mode (``BadRequestError``, ``NotFoundError``,
            ``AuthError``, ``RateLimitError``, ``UpstreamError``, or
            ``NetworkError``). Never raises raw ``httpx`` exceptions.
    """
    from meta_data_mcp import health
    from meta_data_mcp.errors import translate_http_error

    merged_headers = {
        "User-Agent": _default_user_agent(),
        "Accept": "application/json",
    }
    if headers:
        merged_headers.update(headers)

    has_auth = any(k.lower() in {"authorization", "cookie"} for k in merged_headers)

    effective_ttl = _CACHE_DEFAULT_TTL if cache_ttl is None else cache_ttl

    cache_key: str | None = None
    if effective_ttl > 0:
        cache_key = _cache_key(
            url, params, merged_headers.get("Accept", ""), has_auth=has_auth
        )
        cached = _response_cache.get(cache_key)
        if cached is not None:
            log.debug("Cache hit for %s", url)
            return cached

    _DEFAULT_HTTP_RETRIES = 2
    try:
        _configured = int(
            os.getenv("OPENDATA_MCP_HTTP_RETRIES", str(_DEFAULT_HTTP_RETRIES))
        )
        max_attempts = max(0, _configured) + 1
    except (ValueError, TypeError):
        max_attempts = _DEFAULT_HTTP_RETRIES + 1
    response: httpx.Response | None = None
    for attempt in range(max_attempts):
        try:
            response = httpx.get(
                url,
                params=params,
                timeout=timeout,
                headers=merged_headers,
                follow_redirects=True,
            )
        except httpx.RequestError as e:
            # Pre-response network failure. NetworkError.retryable=True, so
            # retry with backoff until exhausted, then translate.
            if attempt < max_attempts - 1:
                sleep_for = _retry_sleep_seconds(attempt, None)
                log.debug(
                    "Retrying %s after %.2fs (attempt %d/%d, network error: %s)",
                    url,
                    sleep_for,
                    attempt + 1,
                    max_attempts,
                    e,
                )
                time.sleep(sleep_for)
                continue
            health.record_failure(provider, status=None)
            raise translate_http_error(provider, e) from e
        status = getattr(response, "status_code", None)
        is_retryable = isinstance(status, int) and (
            status == 429 or 500 <= status < 600
        )
        if not is_retryable or attempt == max_attempts - 1:
            break
        retry_after = None
        try:
            retry_after = response.headers.get("Retry-After")
        except AttributeError:
            retry_after = None
        sleep_for = _retry_sleep_seconds(attempt, retry_after)
        log.debug(
            "Retrying %s after %.2fs (attempt %d/%d, status %d)",
            url,
            sleep_for,
            attempt + 1,
            max_attempts,
            status,
        )
        time.sleep(sleep_for)

    assert response is not None  # loop runs at least once
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        status_code = getattr(e.response, "status_code", None)
        # V12 fix (Phase 3): 401/403 indicate caller-side credential misconfig,
        # not upstream fault. Penalizing the provider's health score would
        # bias routing away from a provider that's actually healthy — the
        # right outcome is for the caller to fix their env vars. Translate
        # the error (so the caller still sees a structured AuthError) but
        # don't degrade health. Pinned by
        # tests/test_health.py::test_record_failure_skipped_for_401_403.
        if status_code not in (401, 403):
            health.record_failure(provider, status=status_code)
        raise translate_http_error(provider, e) from e

    health.record_success(provider)

    if effective_ttl > 0 and cache_key is not None:
        _response_cache.set(cache_key, response, ttl=effective_ttl)

    return response


def http_post(
    url: str,
    json: Any | None = None,
    *,
    provider: str,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Perform a POST request with the same kernel guarantees as ``http_get``.

    ``provider`` is **mandatory**, mirroring ``http_get``. Same retry,
    health-feedback, and ProviderError-translation contract.

    Cache behavior is intentionally NOT implemented — POST is non-idempotent
    in the general case, so caching responses would be incorrect. Callers
    that need caching on idempotent POST queries should layer their own
    semantic cache on top.

    Args:
        url: The endpoint URL.
        json: Optional JSON-serializable body. ``None`` sends no body.
        provider: Stable provider id. Required.
        timeout: Request timeout in seconds (default 10.0).
        headers: Optional header overrides merged on top of defaults.

    Returns:
        The httpx.Response (already status-checked).

    Raises:
        meta_data_mcp.errors.ProviderError: subclass appropriate to the
            failure mode. Never raises raw ``httpx`` exceptions.
    """
    from meta_data_mcp import health
    from meta_data_mcp.errors import translate_http_error

    merged_headers = {
        "User-Agent": _default_user_agent(),
        "Accept": "application/json",
    }
    if headers:
        merged_headers.update(headers)

    _DEFAULT_HTTP_RETRIES = 2
    try:
        _configured = int(
            os.getenv("OPENDATA_MCP_HTTP_RETRIES", str(_DEFAULT_HTTP_RETRIES))
        )
        max_attempts = max(0, _configured) + 1
    except (ValueError, TypeError):
        max_attempts = _DEFAULT_HTTP_RETRIES + 1

    response: httpx.Response | None = None
    for attempt in range(max_attempts):
        try:
            response = httpx.post(
                url,
                json=json,
                timeout=timeout,
                headers=merged_headers,
                follow_redirects=True,
            )
        except httpx.RequestError as e:
            if attempt < max_attempts - 1:
                sleep_for = _retry_sleep_seconds(attempt, None)
                log.debug(
                    "Retrying POST %s after %.2fs (attempt %d/%d, network error: %s)",
                    url,
                    sleep_for,
                    attempt + 1,
                    max_attempts,
                    e,
                )
                time.sleep(sleep_for)
                continue
            health.record_failure(provider, status=None)
            raise translate_http_error(provider, e) from e
        status = getattr(response, "status_code", None)
        is_retryable = isinstance(status, int) and (
            status == 429 or 500 <= status < 600
        )
        if not is_retryable or attempt == max_attempts - 1:
            break
        retry_after = None
        try:
            retry_after = response.headers.get("Retry-After")
        except AttributeError:
            retry_after = None
        sleep_for = _retry_sleep_seconds(attempt, retry_after)
        log.debug(
            "Retrying POST %s after %.2fs (attempt %d/%d, status %d)",
            url,
            sleep_for,
            attempt + 1,
            max_attempts,
            status,
        )
        time.sleep(sleep_for)

    assert response is not None
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        status_code = getattr(e.response, "status_code", None)
        # V12 fix (Phase 3): see the matching comment in ``http_get``. 401/403
        # is caller misconfig, not upstream fault — don't degrade health.
        if status_code not in (401, 403):
            health.record_failure(provider, status=status_code)
        raise translate_http_error(provider, e) from e

    health.record_success(provider)

    return response


def serialize_for_llm(data: Any) -> str:
    """Serialize ``data`` to a JSON string truncated to ``MAX_RESPONSE_CHARS``.

    Uses ``json.dumps`` so that LLMs receive valid JSON (``true``/``false``,
    ``null``, double-quoted keys) instead of Python's ``repr`` output.

    ``default=str`` is used as a fallback serializer for types that are not
    natively JSON-serializable (e.g. ``datetime``, ``UUID``).
    """
    return json.dumps(data, default=str, ensure_ascii=False)[:MAX_RESPONSE_CHARS]


def _json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
        sort_keys=True,
        separators=(",", ":"),
    )


def to_json_text(payload: Any, max_chars: int | None = None) -> str:
    """Serialize data to deterministic JSON text for MCP responses."""
    text = _json_dumps(payload)
    if max_chars is None or len(text) <= max_chars:
        return text
    if max_chars < 2:
        raise ValueError("max_chars must be >= 2")

    truncated_payload = {
        "truncated": True,
        "original_length": len(text),
        "max_chars": max_chars,
        "preview": text,
    }
    truncated_text = _json_dumps(truncated_payload)
    if len(truncated_text) <= max_chars:
        return truncated_text

    preview = text
    while preview:
        truncated_payload["preview"] = preview
        truncated_text = _json_dumps(truncated_payload)
        if len(truncated_text) <= max_chars:
            return truncated_text
        preview = preview[:-1]

    minimal_truncated_payload = {
        "truncated": True,
        "original_length": len(text),
        "max_chars": max_chars,
    }
    minimal_truncated_text = _json_dumps(minimal_truncated_payload)
    if len(minimal_truncated_text) <= max_chars:
        return minimal_truncated_text

    # Ordered from most informative to smallest object-shaped JSON to preserve
    # context while still honoring strict max_chars limits.
    for fallback_payload in ({"truncated": True}, {}):
        fallback = _json_dumps(fallback_payload)
        if len(fallback) <= max_chars:
            return fallback

    raise ValueError("max_chars is too small for a valid JSON object fallback")


def _max_prefix_json_text(
    items: Sequence[Any],
    build_payload: Callable[[Sequence[Any]], Any],
    max_chars: int,
) -> str | None:
    """Return the largest prefix payload that still fits within ``max_chars``."""
    low = 0
    high = len(items)
    best_text: str | None = None
    while low <= high:
        mid = (low + high) // 2
        candidate_text = _json_dumps(build_payload(items[:mid]))
        if len(candidate_text) <= max_chars:
            best_text = candidate_text
            low = mid + 1
        else:
            high = mid - 1
    return best_text


def to_records_text(payload: Any, max_chars: int = MAX_RESPONSE_CHARS) -> str:
    """Serialize a records-shape payload while preserving valid shape JSON.

    Mirrors :func:`to_geofeatures_text` for the
    ``ui://meta-data-mcp/shape/records/v1`` envelope. If the serialized
    payload exceeds ``max_chars``, the ``rows`` list is trimmed to the
    largest prefix that still fits while keeping the records contract
    intact — i.e. the result is always a valid JSON object with
    ``rows`` (possibly empty) plus the original ``schema`` /
    ``default_facets`` metadata.

    Why this exists instead of ``serialize_for_llm``: the records bundle
    parses the response with ``JSON.parse``; a truncated-by-slicing JSON
    string raises and the table renders empty. Why this exists instead of
    ``to_json_text(max_chars=...)``: that helper replaces the payload with
    ``{"truncated": true, "preview": "..."}`` when over budget, which
    drops the ``rows`` key and again leaves the bundle with nothing to
    render.

    Returns valid JSON within ``max_chars`` in every code path. Falls
    back to ``to_json_text`` only when the payload is not a records-shape
    dict (the dict envelope itself doesn't have a ``rows`` list).
    """
    text = _json_dumps(payload)
    if len(text) <= max_chars:
        return text
    if not isinstance(payload, dict):
        return to_json_text(payload, max_chars=max_chars)

    rows = payload.get("rows")
    if isinstance(rows, list):
        bounded_text = _max_prefix_json_text(
            rows,
            lambda bounded_rows: {**payload, "rows": list(bounded_rows)},
            max_chars,
        )
        if bounded_text is not None:
            return bounded_text

    return to_json_text(payload, max_chars=max_chars)


def to_geofeatures_text(payload: Any, max_chars: int = MAX_RESPONSE_CHARS) -> str:
    """Serialize a geofeatures payload while preserving valid shape JSON.

    If the payload exceeds ``max_chars``, this trims the feature list to the
    largest prefix that still fits while keeping the geofeatures contract
    intact. Supports both option B payloads
    (``{"features": [{lat, lon, attrs}, ...]}``) and option A native GeoJSON
    payloads (``{"features": {"type": "FeatureCollection", "features": [...]}}``).
    Falls back to ``to_json_text`` only when the payload is not recognized as a
    geofeatures envelope.
    """
    text = _json_dumps(payload)
    if len(text) <= max_chars:
        return text
    if not isinstance(payload, dict):
        return to_json_text(payload, max_chars=max_chars)

    features = payload.get("features")
    if isinstance(features, list):
        bounded_text = _max_prefix_json_text(
            features,
            lambda bounded_features: {**payload, "features": list(bounded_features)},
            max_chars,
        )
        if bounded_text is not None:
            return bounded_text
        return to_json_text(payload, max_chars=max_chars)

    if (
        isinstance(features, dict)
        and features.get("type") == "FeatureCollection"
        and isinstance(features.get("features"), list)
    ):
        collection_features = features["features"]
        bounded_text = _max_prefix_json_text(
            collection_features,
            lambda bounded_features: {
                **payload,
                "features": {**features, "features": list(bounded_features)},
            },
            max_chars,
        )
        if bounded_text is not None:
            return bounded_text

    return to_json_text(payload, max_chars=max_chars)


# ---------------------------------------------------------------------------
# MCP Apps (`ui://`) resource helper
# ---------------------------------------------------------------------------


def register_ui_resource(
    *,
    name: str,
    html: str,
    description: str,
    resources: list[types.Resource],
    resources_handlers: dict[str, Callable[[AnyUrl], str | bytes]],
    server_name: str = "meta-data-mcp",
    mime: str = "text/html;profile=mcp-app",
) -> str:
    """Register a ``ui://<server_name>/<name>`` resource backed by static HTML.

    The MCP Apps extension (https://modelcontextprotocol.io/docs/extensions/apps)
    lets a server return interactive UIs by:

    1. Declaring a ``ui://`` resource that holds the HTML (optionally with
       inlined JS and CSS).
    2. Binding a tool to it via ``_meta={"ui": {"resourceUri": ...}}`` so
       the host renders that resource in a sandboxed iframe alongside the
       tool's result. Pass the alias keyword ``_meta=`` — NOT ``meta=``.
       The SDK's ``Tool`` model has ``meta`` aliased to ``_meta`` but does
       not enable ``populate_by_name``, so ``meta=`` silently lands in
       extras and never reaches the wire. See ``tests/test_ui_resource.py``
       for the regression that pins this footgun.

    This helper covers step 1. It appends a ``types.Resource`` to the caller's
    ``resources`` list and registers a handler in ``resources_handlers`` that
    returns the HTML string when the host calls ``resources/read``.

    Args:
        name: Path component for the URI (e.g. ``"discovery"``,
            ``"shape/timeseries/v1"``). Slashes are allowed.
        html: The full resource body. Usually HTML with inlined `<script>`
            and `<style>` for self-contained delivery.
        description: Short human-readable description that surfaces in the
            host's resource catalog.
        resources: The server's ``RESOURCES`` list (mutated in place).
        resources_handlers: The server's ``RESOURCES_HANDLERS`` dict
            (mutated in place).
        server_name: Authority component of the URI. Defaults to
            ``"meta-data-mcp"``; override per server if reusing this helper
            from outside the meta server.
        mime: Content-Type of the resource. Defaults to
            ``"text/html;profile=mcp-app"`` — the MCP Apps standard MIME
            type. Hosts use the ``;profile=mcp-app`` parameter to
            distinguish renderable MCP-UI bundles from arbitrary HTML;
            without it they reject the resource with
            ``"Unsupported UI resource content format"``. See
            https://mcpui.dev/guide/protocol-details.html.

    Returns:
        The fully-qualified ``ui://`` URI as a string, suitable for passing
        as ``_meta={"ui": {"resourceUri": <returned>}}`` on a Tool.

    Raises:
        ValueError: If ``name`` is empty or the resulting URI collides with
            an already-registered handler.
    """
    if not name:
        raise ValueError("name must be non-empty")
    uri = f"ui://{server_name}/{name.lstrip('/')}"
    if uri in resources_handlers:
        raise ValueError(f"ui resource already registered: {uri}")
    resources.append(
        types.Resource(
            uri=AnyUrl(uri),
            name=name,
            description=description,
            mimeType=mime,
        )
    )

    def _handler(_uri: AnyUrl) -> str:
        return html

    resources_handlers[uri] = _handler
    return uri


def create_mcp_server(
    server_name: str,
    resources: list[types.Resource] | None = None,
    resources_handlers: dict[str, Callable[[AnyUrl], str | bytes]] | None = None,
    tools: list[types.Tool] | None = None,
    tools_handlers: dict[
        str,
        Callable[
            [dict[str, Any] | None],
            Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource],
        ],
    ]
    | None = None,
    prompts: list[types.Prompt] | None = None,
    prompts_handlers: dict[
        str,
        Callable[
            [dict[str, str] | None],
            types.GetPromptResult,
        ],
    ]
    | None = None,
    resource_templates: list[types.ResourceTemplate] | None = None,
) -> Server:
    """
    Create a MCP server with the given resources, tools, and prompts.

    Args:
        server_name: The name of the server.
        resources: The list of resources to register.
        resources_handlers: The dictionary of resource handlers.
        tools: The list of tools to register.
        tools_handlers: The dictionary of tools handlers.
        prompts: The list of prompts to register.
        prompts_handlers: The dictionary of prompt handlers.
        resource_templates: The list of resource templates to register.

    Returns:
        The created MCP server.
    """
    _resources = resources or []
    _resources_handlers = resources_handlers or {}
    _tools = tools or []
    _tools_handlers = tools_handlers or {}
    _prompts = prompts or []
    _prompts_handlers = prompts_handlers or {}
    _resource_templates = resource_templates or []

    # instantiate the server
    server = Server(server_name)

    # register resources
    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        return _resources

    # Build a fast (URI → mimeType) lookup once so the read handler can
    # propagate the registered MIME without rescanning ``_resources`` on
    # every call. Falls back to ``text/plain`` only when a resource was
    # registered without a ``mimeType`` (defensive — every codepath in
    # this repo sets one explicitly).
    _mime_by_uri: dict[str, str] = {
        str(r.uri): (r.mimeType or "text/plain") for r in _resources
    }

    @server.read_resource()
    async def handle_read_resource(
        resource_uri: AnyUrl,
    ) -> list[ReadResourceContents]:
        """Return resource contents with the registered MIME type attached.

        The MCP SDK's ``read_resource`` decorator wraps a bare ``str`` /
        ``bytes`` return into a content envelope, but it defaults the
        envelope's ``mimeType`` to ``text/plain`` (or
        ``application/octet-stream`` for bytes) — completely independent
        of whatever the registered ``Resource.mimeType`` declares. The
        host reads the envelope's ``mimeType``, not the catalog entry's,
        when deciding how to render. An HTML ``ui://`` resource
        registered as ``text/html`` was therefore being served as
        ``text/plain`` on read, and the host refused to mount it.

        Returning ``Iterable[ReadResourceContents]`` lets us pin the
        correct MIME and also silences the SDK's deprecation warning
        about returning bare strings.

        See:
        - ``register_ui_resource`` for where each resource declares its MIME
        - the SDK ``read_resource`` decorator (``mcp.server.lowlevel``)
        - tests/test_ui_resource.py::test_read_resource_returns_text_html_mime
        """
        resource_key = str(resource_uri)

        if resource_key not in _resources_handlers:
            log.error(f"Resource {resource_uri} not found")
            raise AttributeError(f"Resource {resource_uri} not found")

        payload = _resources_handlers[resource_key](resource_uri)
        mime = _mime_by_uri.get(resource_key, "text/plain")
        return [ReadResourceContents(content=payload, mime_type=mime)]

    # register resource templates
    @server.list_resource_templates()
    async def handle_list_resource_templates() -> list[types.ResourceTemplate]:
        return _resource_templates

    # register the tools
    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return _tools

    # register the tools handlers
    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None = None
    ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name not in _tools_handlers:
            log.error(f"Tool {name} not found")
            raise AttributeError(f"Tool {name} not found")

        try:
            return await _tools_handlers[name](arguments)
        except Exception as e:
            log.error(f"Error calling tool {name}: {e}")
            raise

    # register the prompts
    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        return _prompts

    # register the prompts handlers
    @server.get_prompt()
    async def handle_get_prompt(
        name: str, arguments: dict[str, str] | None = None
    ) -> types.GetPromptResult:
        if name not in _prompts_handlers:
            log.error(f"Prompt {name} not found")
            raise AttributeError(f"Prompt {name} not found")

        try:
            return await _prompts_handlers[name](arguments)
        except Exception as e:
            log.error(f"Error getting prompt {name}: {e}")
            raise

    return server


class BearerAuthMiddleware:
    """Require ``Authorization: Bearer <token>`` on protected ASGI paths.

    Pure ASGI middleware (not BaseHTTPMiddleware) so it does not buffer
    streaming SSE responses. The health check at ``/`` is left open so
    uptime probes work without credentials.
    """

    def __init__(
        self,
        app: Any,
        token: str,
        protected_prefixes: Sequence[str] = ("/sse", "/messages"),
    ) -> None:
        self.app = app
        self.token = token
        self.protected_prefixes = tuple(protected_prefixes)

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http" or not any(
            scope.get("path", "").startswith(p) for p in self.protected_prefixes
        ):
            await self.app(scope, receive, send)
            return

        auth_header = ""
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                auth_header = value.decode("latin-1")
                break

        scheme = ""
        presented = ""
        parts = auth_header.split(" ", 1)
        if len(parts) == 2:
            scheme, presented = parts
        if (
            scheme.casefold() != "bearer"
            or not presented
            or not hmac.compare_digest(presented, self.token)
        ):
            from starlette.responses import JSONResponse

            response = JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="meta-data-mcp"'},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


async def run_server(
    server: Server, transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"
):
    """
    Run the MCP server with the specified transport.

    SSE auth: if ``META_DATA_MCP_AUTH_TOKEN`` is set, requests to ``/sse``
    and ``/messages`` must include ``Authorization: Bearer <token>``. When
    unset, SSE is served unauthenticated (logs a startup warning).
    """
    if transport == "stdio":
        from mcp.server.stdio import stdio_server

        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )
    elif transport == "sse":
        import uvicorn
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.middleware.cors import CORSMiddleware
        from starlette.responses import JSONResponse
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages")

        class SseApp:
            async def __call__(self, scope, receive, send):
                log.info(f"New SSE connection request from {scope.get('client')}")
                try:
                    async with sse.connect_sse(scope, receive, send) as streams:
                        log.info("SSE connection established, running server...")
                        await server.run(
                            streams[0],
                            streams[1],
                            server.create_initialization_options(),
                        )
                except Exception as e:
                    # Connection closed by client is common and can be ignored or logged at debug
                    log.debug(f"SSE connection error: {e}")
                finally:
                    log.info("SSE connection closed")

        async def root(request):
            return JSONResponse(
                {
                    "status": "running",
                    "server": server.name,
                    "transport": "sse",
                    "endpoints": {"sse": "/sse", "messages": "/messages"},
                }
            )

        app = Starlette(
            debug=False,
            routes=[
                Route("/", endpoint=root),
                Route("/sse", endpoint=SseApp()),
                Mount("/messages", app=sse.handle_post_message),
            ],
        )

        auth_token = os.getenv("META_DATA_MCP_AUTH_TOKEN")
        if auth_token:
            app.add_middleware(BearerAuthMiddleware, token=auth_token)
            log.info(
                "SSE bearer auth enabled (META_DATA_MCP_AUTH_TOKEN set; "
                "protecting /sse and /messages)"
            )
        else:
            log.warning(
                "SSE bearer auth DISABLED — set META_DATA_MCP_AUTH_TOKEN to "
                "require Authorization: Bearer <token> on /sse and /messages"
            )

        # CORSMiddleware must be added last so it is outermost; this ensures
        # that OPTIONS preflight requests receive CORS headers before reaching
        # BearerAuthMiddleware (which would otherwise reject them with 401).
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="debug",
            timeout_keep_alive=65,
            timeout_notify=60,
        )
        uvicorn_server = uvicorn.Server(config)
        await uvicorn_server.serve()
    else:
        raise ValueError(f"Unknown transport: {transport}")
