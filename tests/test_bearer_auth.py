"""Tests for BearerAuthMiddleware used by the SSE transport."""

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from meta_data_mcp.utils import BearerAuthMiddleware


def _build_app(token: str) -> Starlette:
    async def root(request):
        return PlainTextResponse("ok")

    async def sse(request):
        return PlainTextResponse("sse-ok")

    async def messages(request):
        return PlainTextResponse("messages-ok")

    app = Starlette(
        routes=[
            Route("/", endpoint=root),
            Route("/sse", endpoint=sse),
            Route("/messages", endpoint=messages, methods=["GET", "POST"]),
        ],
    )
    app.add_middleware(BearerAuthMiddleware, token=token)
    return app


@pytest.mark.asyncio
async def test_health_check_is_unauthenticated():
    app = _build_app("secret")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.text == "ok"


@pytest.mark.asyncio
async def test_sse_without_auth_returns_401():
    app = _build_app("secret")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/sse")
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")


@pytest.mark.asyncio
async def test_sse_with_wrong_token_returns_401():
    app = _build_app("secret")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/sse", headers={"Authorization": "Bearer wrong-token"}
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sse_with_correct_token_passes_through():
    app = _build_app("secret")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/sse", headers={"Authorization": "Bearer secret"}
        )
    assert response.status_code == 200
    assert response.text == "sse-ok"


@pytest.mark.asyncio
async def test_messages_endpoint_is_protected():
    app = _build_app("secret")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauth = await client.post("/messages")
        authed = await client.post(
            "/messages", headers={"Authorization": "Bearer secret"}
        )
    assert unauth.status_code == 401
    assert authed.status_code == 200


@pytest.mark.asyncio
async def test_non_bearer_scheme_is_rejected():
    app = _build_app("secret")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/sse", headers={"Authorization": "Basic c2VjcmV0"}
        )
    assert response.status_code == 401
