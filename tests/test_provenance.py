"""Tests for the optional sha256 + timestamp provenance on tool results.

The provenance layer is opt-in via the ``META_DATA_MCP_PROVENANCE``
environment variable. When enabled, ``call_tool`` responses gain a
``meta-data-mcp/provenance`` entry on the first content block's
``_meta`` field carrying a sha256 of the canonical content and an ISO
8601 UTC timestamp; when disabled (the default), results are passed
through untouched.

These tests cover three things:

1. The env-var parser — truthy / falsy / unset, with surrounding
   whitespace and mixed case.
2. The ``attach()`` helper — adds a fingerprint to the first block,
   doesn't mutate the input, synthesizes a stub for empty content,
   preserves any pre-existing ``_meta`` keys, serializes to the wire
   under the ``_meta`` alias, and produces a digest the caller can
   reproduce externally (without seeing the provenance metadata
   itself).
3. End-to-end through the SDK dispatcher — when enabled, the wrapped
   ``handle_call_tool`` returns content with provenance; when disabled,
   it does not.

Why an external-reproducibility test (``test_sha256_is_reproducible_externally``)
is load-bearing: the tamper-evidence story only works if a caller can
recompute the digest from what they see. Stripping ``_meta`` before
hashing is the mechanism that makes that round-trip work, and the test
pins it.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import pytest
from mcp import types

from meta_data_mcp import provenance
from meta_data_mcp.server import create_mcp_server


def _txt(s: str) -> types.TextContent:
    return types.TextContent(type="text", text=s)


# ---------------------------------------------------------------------------
# is_enabled()
# ---------------------------------------------------------------------------


def test_is_enabled_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(provenance._ENV_VAR, raising=False)
    assert provenance.is_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "On", " tRuE "])
def test_is_enabled_truthy(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(provenance._ENV_VAR, value)
    assert provenance.is_enabled() is True


@pytest.mark.parametrize(
    "value", ["", "0", "false", "no", "off", "disabled", "maybe", " "]
)
def test_is_enabled_falsy(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(provenance._ENV_VAR, value)
    assert provenance.is_enabled() is False


# ---------------------------------------------------------------------------
# attach() — structural correctness
# ---------------------------------------------------------------------------


def test_attach_adds_provenance_to_first_block_only() -> None:
    out = provenance.attach([_txt("hello"), _txt("world")])
    assert len(out) == 2

    meta = out[0].meta
    assert meta is not None
    fp = meta[provenance.PROVENANCE_META_KEY]
    assert set(fp.keys()) == {"sha256", "timestamp"}

    # Second block is left alone — provenance is intentionally on the
    # FIRST block only so callers know exactly where to look.
    assert out[1].meta is None


def test_attach_does_not_mutate_input() -> None:
    original = [_txt("hello")]
    out = provenance.attach(original)
    assert out is not original
    assert original[0].meta is None


def test_attach_empty_content_synthesizes_stub() -> None:
    out = provenance.attach([])
    assert len(out) == 1
    block = out[0]
    assert isinstance(block, types.TextContent)
    assert block.text == ""
    assert block.meta is not None
    assert provenance.PROVENANCE_META_KEY in block.meta


def test_attach_preserves_existing_meta() -> None:
    block = types.TextContent(type="text", text="hi", _meta={"existing": "x"})
    out = provenance.attach([block])
    meta = out[0].meta
    assert meta is not None
    assert meta["existing"] == "x"
    assert provenance.PROVENANCE_META_KEY in meta


# ---------------------------------------------------------------------------
# attach() — digest & timestamp semantics
# ---------------------------------------------------------------------------


def test_sha256_is_deterministic() -> None:
    a = provenance.attach([_txt("hello")])
    b = provenance.attach([_txt("hello")])
    assert _sha(a) == _sha(b)


def test_sha256_changes_with_content() -> None:
    a = provenance.attach([_txt("hello")])
    b = provenance.attach([_txt("world")])
    assert _sha(a) != _sha(b)


def test_sha256_excludes_existing_meta_from_digest() -> None:
    """Running ``attach`` on its own output must yield the same digest;
    that requires the provenance metadata itself to be excluded from
    the canonical bytes the hash covers."""
    once = provenance.attach([_txt("hello")])
    twice = provenance.attach(once)
    assert _sha(once) == _sha(twice)


def test_sha256_is_reproducible_externally() -> None:
    """A caller that receives the response must be able to recompute
    the advertised digest from the visible content — this is what makes
    the fingerprint useful for tamper-evidence."""
    out = provenance.attach([_txt("hello"), _txt("world")])
    advertised = _sha(out)

    stripped: list[dict[str, Any]] = []
    for block in out:
        dumped = block.model_dump(by_alias=True, exclude_none=True)
        dumped.pop("_meta", None)
        stripped.append(dumped)
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    expected = hashlib.sha256(canonical).hexdigest()

    assert advertised == expected


def test_timestamp_format_is_iso_utc_with_ms() -> None:
    out = provenance.attach([_txt("hi")])
    ts = out[0].meta[provenance.PROVENANCE_META_KEY]["timestamp"]  # type: ignore[index]
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", ts), (
        f"timestamp {ts!r} does not match YYYY-MM-DDTHH:MM:SS.mmmZ"
    )


def test_meta_serializes_under_wire_alias() -> None:
    """The first block must serialize the provenance under the ``_meta``
    alias (not the python ``meta`` attribute name) — that's what the MCP
    wire format requires, and the SDK's ``populate_by_name`` posture
    means we'd silently drop the metadata on the floor if we used the
    wrong key."""
    out = provenance.attach([_txt("hi")])
    dumped = out[0].model_dump(by_alias=True, exclude_none=True)
    assert "_meta" in dumped
    assert "meta" not in dumped
    assert provenance.PROVENANCE_META_KEY in dumped["_meta"]


# ---------------------------------------------------------------------------
# Dispatcher integration — wire it together through create_mcp_server
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatcher_attaches_provenance_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(provenance._ENV_VAR, "1")
    server = _server_with_echo()
    result = await _call_echo(server, "ping")
    contents = result.root.content
    assert len(contents) == 1
    assert contents[0].meta is not None
    assert provenance.PROVENANCE_META_KEY in contents[0].meta


@pytest.mark.anyio
async def test_dispatcher_skips_provenance_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(provenance._ENV_VAR, raising=False)
    server = _server_with_echo()
    result = await _call_echo(server, "ping")
    contents = result.root.content
    assert len(contents) == 1
    assert contents[0].meta is None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _sha(
    content: list[types.TextContent | types.ImageContent | types.EmbeddedResource],
) -> str:
    meta = content[0].meta
    assert meta is not None
    return meta[provenance.PROVENANCE_META_KEY]["sha256"]


def _server_with_echo():
    tools = [types.Tool(name="echo", description="", inputSchema={"type": "object"})]

    async def echo(args: dict[str, Any] | None):
        text = (args or {}).get("text", "default")
        return [types.TextContent(type="text", text=text)]

    return create_mcp_server(
        "test-provenance",
        tools=tools,
        tools_handlers={"echo": echo},
    )


async def _call_echo(server, text: str):
    handler = server.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(name="echo", arguments={"text": text}),
    )
    return await handler(req)
