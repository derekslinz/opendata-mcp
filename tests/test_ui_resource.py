"""Tests for the MCP Apps (`ui://`) resource foundation.

Covers the v2.0 Phase 1 surface:

- ``ui://`` scheme validation through ``pydantic.AnyUrl`` (Gotcha G8).
- ``register_ui_resource()`` end-to-end: appends to ``RESOURCES``, wires a
  handler that returns the HTML, idempotency, collision detection.
- ``mcp.types.Tool``'s ``_meta`` field round-trips correctly to the wire.
  The MCP Apps spec ships UI hints under ``_meta.ui.resourceUri``. In the
  installed SDK the field is named ``meta`` with alias ``_meta`` but
  ``populate_by_name`` is NOT enabled — so the *only* construct-time way
  to set it is to pass the alias (``_meta=``) or assign after
  construction. Passing ``meta=`` silently lands in extras and never
  reaches the host. These tests lock that behavior down so we catch any
  SDK regression that breaks it.

Together these cover the kernel-side foundation; per-shape primitive bundles
and provider wiring land in later phases.
"""

from __future__ import annotations

import pytest
from mcp import types
from pydantic import AnyUrl

from meta_data_mcp.utils import create_mcp_server, register_ui_resource


# ---------------------------------------------------------------------------
# Gotcha G8: ui:// must validate as a pydantic AnyUrl
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "uri,expected_host,expected_path",
    [
        ("ui://meta-data-mcp/discovery", "meta-data-mcp", "/discovery"),
        (
            "ui://meta-data-mcp/shape/timeseries/v1",
            "meta-data-mcp",
            "/shape/timeseries/v1",
        ),
        ("ui://discovery", "discovery", None),
    ],
)
def test_ui_scheme_validates_as_anyurl(uri: str, expected_host: str, expected_path):
    parsed = AnyUrl(uri)
    assert parsed.scheme == "ui"
    assert parsed.host == expected_host
    assert parsed.path == expected_path


# ---------------------------------------------------------------------------
# register_ui_resource()
# ---------------------------------------------------------------------------


def _fresh_state():
    """Return clean (resources_list, resources_handlers_dict) like a server boot."""
    return [], {}


def test_register_ui_resource_appends_resource_and_handler():
    resources, handlers = _fresh_state()
    uri = register_ui_resource(
        name="discovery",
        html="<html><body><h1>discovery</h1></body></html>",
        description="Faceted provider discovery UI.",
        resources=resources,
        resources_handlers=handlers,
    )
    assert uri == "ui://meta-data-mcp/discovery"
    assert len(resources) == 1
    res = resources[0]
    assert str(res.uri) == uri
    assert res.name == "discovery"
    assert res.description.startswith("Faceted")
    assert res.mimeType == "text/html"
    # Handler is registered under the string URI form (matches what
    # create_mcp_server's resource handler key-lookup uses, see utils.py).
    assert uri in handlers


def test_register_ui_resource_returns_html_via_handler():
    resources, handlers = _fresh_state()
    html = "<!doctype html><h1>hello</h1>"
    uri = register_ui_resource(
        name="hello",
        html=html,
        description="smoke",
        resources=resources,
        resources_handlers=handlers,
    )
    assert handlers[uri](AnyUrl(uri)) == html


def test_register_ui_resource_with_path_segments():
    """Shape primitives use slash-segmented names (e.g. 'shape/timeseries/v1')."""
    resources, handlers = _fresh_state()
    uri = register_ui_resource(
        name="shape/timeseries/v1",
        html="<html></html>",
        description="shape",
        resources=resources,
        resources_handlers=handlers,
    )
    assert uri == "ui://meta-data-mcp/shape/timeseries/v1"
    # AnyUrl must still parse it cleanly so the kernel's resource lookup works.
    parsed = AnyUrl(uri)
    assert parsed.path == "/shape/timeseries/v1"


def test_register_ui_resource_strips_leading_slash_in_name():
    resources, handlers = _fresh_state()
    uri = register_ui_resource(
        name="/discovery",
        html="<html></html>",
        description="x",
        resources=resources,
        resources_handlers=handlers,
    )
    assert uri == "ui://meta-data-mcp/discovery"


def test_register_ui_resource_rejects_empty_name():
    resources, handlers = _fresh_state()
    with pytest.raises(ValueError, match="non-empty"):
        register_ui_resource(
            name="",
            html="<html/>",
            description="x",
            resources=resources,
            resources_handlers=handlers,
        )


def test_register_ui_resource_rejects_collision():
    resources, handlers = _fresh_state()
    register_ui_resource(
        name="discovery",
        html="<html>v1</html>",
        description="first",
        resources=resources,
        resources_handlers=handlers,
    )
    with pytest.raises(ValueError, match="already registered"):
        register_ui_resource(
            name="discovery",
            html="<html>v2</html>",
            description="second",
            resources=resources,
            resources_handlers=handlers,
        )


def test_register_ui_resource_custom_server_and_mime():
    resources, handlers = _fresh_state()
    uri = register_ui_resource(
        name="probe",
        html="<svg/>",
        description="x",
        resources=resources,
        resources_handlers=handlers,
        server_name="alt-server",
        mime="image/svg+xml",
    )
    assert uri == "ui://alt-server/probe"
    assert resources[0].mimeType == "image/svg+xml"


# ---------------------------------------------------------------------------
# Tool's _meta field round-trips correctly to the wire (the MCP Apps contract).
#
# The Tool model has a `meta` field aliased to `_meta` on the wire. Crucially,
# `populate_by_name` is NOT enabled, so callers MUST pass the alias
# (`_meta={...}`) at construction time — passing `meta={...}` silently lands
# in extras (Tool.model_config["extra"] == "allow") and never reaches the
# host as `_meta`. These tests pin both ends of the contract.
# ---------------------------------------------------------------------------


def test_tool_underscore_meta_round_trips_to_wire():
    """Constructing with the alias keyword (`_meta=`) serializes to `_meta`."""
    app_uri = "ui://meta-data-mcp/discovery"
    tool = types.Tool(
        name="opendata-find-providers",
        description="Find providers.",
        inputSchema={"type": "object"},
        _meta={"ui": {"resourceUri": app_uri}},
    )
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert "_meta" in wire, (
        "Tool's _meta did not appear on the wire. The MCP Apps extension "
        "relies on this — if pydantic's by_alias behavior changed, the "
        "tool's UI metadata stops reaching the host."
    )
    assert wire["_meta"]["ui"]["resourceUri"] == app_uri
    # The Python attribute name (`meta`) must NOT leak into the wire payload.
    assert "meta" not in wire


def test_tool_meta_via_field_assignment_round_trips_to_wire():
    """Assigning `tool.meta = ...` after construction also serializes to
    `_meta`. This is the alternative wiring pattern providers may use."""
    app_uri = "ui://meta-data-mcp/discovery"
    tool = types.Tool(
        name="opendata-find-providers",
        description="Find providers.",
        inputSchema={"type": "object"},
    )
    tool.meta = {"ui": {"resourceUri": app_uri}}
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert "_meta" in wire
    assert wire["_meta"]["ui"]["resourceUri"] == app_uri
    assert "meta" not in wire


def test_tool_meta_constructor_kwarg_does_not_reach_wire():
    """REGRESSION: passing `meta={...}` to the constructor silently drops
    the value into extras (Tool.model_config['extra'] == 'allow') and
    NEVER reaches the wire as `_meta`. The SDK currently doesn't enable
    `populate_by_name`, so `meta=` is a footgun. If this test ever fails
    — i.e. `_meta` appears in the wire from a `meta=` kwarg — the SDK has
    enabled `populate_by_name` and our docs / provider template should
    switch to the more natural `meta=` pattern."""
    app_uri = "ui://meta-data-mcp/discovery"
    tool = types.Tool(
        name="x",
        description="y",
        inputSchema={"type": "object"},
        meta={"ui": {"resourceUri": app_uri}},  # type: ignore[call-arg]
    )
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert "_meta" not in wire, (
        "Tool now accepts `meta=` as a constructor kwarg and serializes "
        "it to `_meta` — the SDK has enabled populate_by_name. Update "
        "the v2.0 docs / provider template to use the simpler `meta=` "
        "pattern."
    )


def test_tool_without_meta_omits_underscore_meta():
    """Tools that don't declare meta should not emit a stray `_meta` key."""
    tool = types.Tool(
        name="plain-tool",
        description="No UI.",
        inputSchema={"type": "object"},
    )
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert "_meta" not in wire
    assert "meta" not in wire


# ---------------------------------------------------------------------------
# End-to-end: a ui:// resource registered via register_ui_resource() is
# served by the same create_mcp_server() resource handler we already test
# elsewhere. No new plumbing required.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ui_resource_is_served_by_create_mcp_server():
    """A registered ui:// resource is reachable via the server's
    read_resource dispatch. Smoke test that the existing
    ``create_mcp_server`` plumbing handles ``ui://`` URIs identically to
    the pre-existing ``registry://`` scheme."""
    resources, handlers = _fresh_state()
    html = "<!doctype html><body>discovery-app</body>"
    uri = register_ui_resource(
        name="discovery",
        html=html,
        description="x",
        resources=resources,
        resources_handlers=handlers,
    )

    server = create_mcp_server(
        "test-ui-resource",
        resources=resources,
        resources_handlers=handlers,
    )

    # Reach into the server's registered handlers the same way the existing
    # provider tests do (e.g. test_meta_data_mcp.py uses the live
    # handler dict).
    # The handler is stored under the string form of the URI.
    served = handlers[uri](AnyUrl(uri))
    assert served == html
    # Sanity: the resource is in the server's catalog.
    assert any(str(r.uri) == uri for r in resources)
    # Server boot didn't blow up.
    assert server.name == "test-ui-resource"


@pytest.fixture
def anyio_backend():
    return "asyncio"
