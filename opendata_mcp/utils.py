import hashlib
import json
import logging
import os
import threading
import time
from typing import Any, Callable, Sequence

import httpx
from mcp import types
from mcp.server import Server
from pydantic import AnyUrl

from opendata_mcp import __version__

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
    ``ttl`` seconds are treated as absent and evicted on next access.
    """

    def __init__(self, maxsize: int = _CACHE_MAX_SIZE, ttl: float = 60.0) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            ts, val = entry
            if time.monotonic() - ts > self._ttl:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, val: Any) -> None:
        with self._lock:
            if len(self._cache) >= self._maxsize:
                oldest = min(self._cache, key=lambda k: self._cache[k][0])
                del self._cache[oldest]
            self._cache[key] = (time.monotonic(), val)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


_response_cache = _TTLCache(maxsize=_CACHE_MAX_SIZE, ttl=max(_CACHE_DEFAULT_TTL, 1.0))


def _cache_key(url: str, params: dict | None, accept: str) -> str:
    payload = json.dumps(
        {"url": url, "params": sorted((params or {}).items()), "accept": accept},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _default_user_agent() -> str:
    """Return the default User-Agent string for outbound HTTP requests.

    Several open-data APIs (Crossref, Europe PMC, OSM Nominatim, SEC EDGAR)
    require an identifiable User-Agent including a contact address. Callers
    may override `OPENDATA_MCP_CONTACT` via environment variable.
    """
    contact = os.getenv("OPENDATA_MCP_CONTACT", "opendata-mcp@example.org")
    return f"opendata-mcp/{__version__} (+https://github.com/derekslinz/opendata-mcp; {contact})"


def http_get(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    cache_ttl: float | None = None,
) -> httpx.Response:
    """Perform a GET request with sensible defaults for open-data APIs.

    - Sets a default User-Agent identifying opendata-mcp (override via
      ``OPENDATA_MCP_CONTACT`` env var or ``headers`` argument).
    - Sets ``Accept: application/json`` by default; override via ``headers``.
    - Calls ``raise_for_status()`` so handlers see a clean exception path.
    - Optional response caching: pass ``cache_ttl=<seconds>`` to cache the
      response body. The global ``OPENDATA_MCP_CACHE_TTL`` env var sets the
      default TTL (default 0 = disabled). Only successful (2xx) responses
      are cached; auth headers are excluded from cache keys.

    Args:
        url: The endpoint URL.
        params: Optional query parameters.
        timeout: Request timeout in seconds (default 10.0).
        headers: Optional header overrides merged on top of defaults.
        cache_ttl: Seconds to cache this response. ``None`` uses the global
            default (``OPENDATA_MCP_CACHE_TTL`` env var, default 0 = off).

    Returns:
        The httpx.Response (already status-checked). When served from cache
        the object is a lightweight stand-in with ``.json()`` and ``.text``
        populated from the cached data.
    """
    merged_headers = {
        "User-Agent": _default_user_agent(),
        "Accept": "application/json",
    }
    if headers:
        merged_headers.update(headers)

    effective_ttl = _CACHE_DEFAULT_TTL if cache_ttl is None else cache_ttl

    if effective_ttl > 0:
        key = _cache_key(url, params, merged_headers.get("Accept", ""))
        cached = _response_cache.get(key)
        if cached is not None:
            log.debug("Cache hit for %s", url)
            return cached

    response = httpx.get(url, params=params, timeout=timeout, headers=merged_headers)
    response.raise_for_status()

    if effective_ttl > 0:
        # Update TTL on the shared cache instance if caller specified a different one.
        if cache_ttl is not None and cache_ttl != _response_cache._ttl:
            _response_cache._ttl = cache_ttl
        _response_cache.set(key, response)  # type: ignore[possibly-undefined]

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

    # register resources handlers
    # TODO: handle better the resource handler we probably dont want to have a handler per URI...
    @server.read_resource()
    async def handle_read_resource(resource_uri: AnyUrl) -> str | bytes:
        resource_key = str(resource_uri)

        if resource_key not in _resources_handlers:
            log.error(f"Resource {resource_uri} not found")
            raise AttributeError(f"Resource {resource_uri} not found")

        return _resources_handlers[resource_key](resource_uri)

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


async def run_server(
    server: Server, transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"
):
    """
    Run the MCP server with the specified transport.
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
