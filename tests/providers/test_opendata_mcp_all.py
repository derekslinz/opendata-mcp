"""Tests for the dynamic aggregator provider ``meta_data_mcp_all``."""

from __future__ import annotations

import importlib
import types as pytypes

import mcp.types as types
import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_module_imports_cleanly():
    """Importing the aggregator must not pull in any provider modules."""
    module = importlib.import_module("meta_data_mcp.providers.meta_data_mcp_all")
    assert module is not None
    # main() must be an async callable
    assert callable(module.main)


def test_module_level_tools_empty():
    """TOOLS / TOOLS_HANDLERS are populated lazily inside main(), not at import."""
    from meta_data_mcp.providers import meta_data_mcp_all

    assert meta_data_mcp_all.TOOLS == []
    assert meta_data_mcp_all.TOOLS_HANDLERS == {}
    assert meta_data_mcp_all.RESOURCES == []
    assert meta_data_mcp_all.RESOURCES_HANDLERS == {}


def test_split_csv_env_handles_empty_and_padded(monkeypatch):
    from meta_data_mcp.providers.meta_data_mcp_all import _split_csv_env

    monkeypatch.delenv("FAKE_ENV_VAR", raising=False)
    assert _split_csv_env("FAKE_ENV_VAR") == []

    monkeypatch.setenv("FAKE_ENV_VAR", "  a, b ,, c  ")
    assert _split_csv_env("FAKE_ENV_VAR") == ["a", "b", "c"]


def test_resolve_provider_ids_returns_all_when_no_filters():
    from meta_data_mcp.providers.meta_data_mcp_all import _resolve_provider_ids
    from meta_data_mcp.registry import REGISTRY

    ids = _resolve_provider_ids([], [])
    assert ids == [entry.id for entry in REGISTRY]


def test_resolve_provider_ids_filters_by_domain():
    """Domain filter must restrict results to providers tagged with that domain."""
    from meta_data_mcp.providers.meta_data_mcp_all import _resolve_provider_ids
    from meta_data_mcp.registry import find_providers

    expected = {
        entry.id for entry in find_providers(domain="earth-science", limit=10_000)
    }
    assert expected, "registry has no earth-science providers — test premise broken"

    ids = set(_resolve_provider_ids(["earth-science"], []))
    assert ids == expected


def test_resolve_provider_ids_unions_domain_and_explicit():
    from meta_data_mcp.providers.meta_data_mcp_all import _resolve_provider_ids
    from meta_data_mcp.registry import find_providers

    health_ids = {entry.id for entry in find_providers(domain="health", limit=10_000)}
    ids = set(_resolve_provider_ids(["health"], ["us_nasa"]))
    assert ids == health_ids | {"us_nasa"}


def _make_fake_provider_module(name: str, tool_name: str) -> pytypes.ModuleType:
    """Construct a synthetic provider module exposing one tool."""
    module = pytypes.ModuleType(name)

    async def handler(arguments):  # pragma: no cover - signature only
        return []

    module.TOOLS = [
        types.Tool(
            name=tool_name,
            description=f"tool from {name}",
            inputSchema={"type": "object", "properties": {}},
        )
    ]
    module.TOOLS_HANDLERS = {tool_name: handler}
    module.RESOURCES = []
    module.RESOURCES_HANDLERS = {}
    return module


def test_merge_provider_detects_collision(caplog):
    """When two providers register the same tool name, only the first wins."""
    from meta_data_mcp.providers.meta_data_mcp_all import _merge_provider

    mod_a = _make_fake_provider_module("fake_a", "shared-tool")
    mod_b = _make_fake_provider_module("fake_b", "shared-tool")

    merged_tools: list[types.Tool] = []
    merged_handlers: dict = {}
    owner_by_tool: dict = {}

    added_a = _merge_provider(
        mod_a, "fake_a", merged_tools, merged_handlers, owner_by_tool
    )

    with caplog.at_level("WARNING"):
        added_b = _merge_provider(
            mod_b, "fake_b", merged_tools, merged_handlers, owner_by_tool
        )

    assert added_a == 1
    assert added_b == 0
    assert [t.name for t in merged_tools] == ["shared-tool"]
    assert owner_by_tool == {"shared-tool": "fake_a"}
    # The winning handler must be the first provider's handler
    assert merged_handlers["shared-tool"] is mod_a.TOOLS_HANDLERS["shared-tool"]
    # And a collision warning naming both providers must have been emitted
    collision_msgs = [r.message for r in caplog.records if r.levelname == "WARNING"]
    assert any(
        "shared-tool" in msg and "fake_a" in msg and "fake_b" in msg
        for msg in collision_msgs
    ), f"expected collision warning, got: {collision_msgs}"


def test_merge_provider_distinct_tools_both_kept():
    from meta_data_mcp.providers.meta_data_mcp_all import _merge_provider

    mod_a = _make_fake_provider_module("fake_a", "tool-a")
    mod_b = _make_fake_provider_module("fake_b", "tool-b")

    merged_tools: list[types.Tool] = []
    merged_handlers: dict = {}
    owner_by_tool: dict = {}

    _merge_provider(mod_a, "fake_a", merged_tools, merged_handlers, owner_by_tool)
    _merge_provider(mod_b, "fake_b", merged_tools, merged_handlers, owner_by_tool)

    assert {t.name for t in merged_tools} == {"tool-a", "tool-b"}
    assert owner_by_tool == {"tool-a": "fake_a", "tool-b": "fake_b"}


@pytest.mark.anyio
async def test_main_domain_filter_loads_only_earth_science(monkeypatch):
    """End-to-end: setting OPENDATA_MCP_DOMAINS restricts imported providers."""
    from meta_data_mcp.providers import meta_data_mcp_all
    from meta_data_mcp.registry import find_providers

    monkeypatch.setenv("OPENDATA_MCP_DOMAINS", "earth-science")
    monkeypatch.delenv("OPENDATA_MCP_PROVIDERS", raising=False)

    expected_ids = {
        entry.id for entry in find_providers(domain="earth-science", limit=10_000)
    }
    assert expected_ids, "registry has no earth-science providers — test premise broken"

    imported: list[str] = []
    real_import = importlib.import_module

    def fake_import(name, *args, **kwargs):
        if name.startswith("meta_data_mcp.providers."):
            imported.append(name.rsplit(".", 1)[-1])
            # Return a harmless stub instead of touching the real module
            stub = pytypes.ModuleType(name)
            stub.TOOLS = []
            stub.TOOLS_HANDLERS = {}
            stub.RESOURCES = []
            stub.RESOURCES_HANDLERS = {}
            return stub
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(
        "meta_data_mcp.providers.meta_data_mcp_all.importlib.import_module",
        fake_import,
    )

    captured: dict = {}

    def fake_create_mcp_server(name, **kwargs):
        captured["server_name"] = name
        captured["tools"] = kwargs.get("tools")
        return object()

    async def fake_run_server(server, transport, port, host):
        captured["ran"] = True

    monkeypatch.setattr("meta_data_mcp.utils.create_mcp_server", fake_create_mcp_server)
    monkeypatch.setattr("meta_data_mcp.utils.run_server", fake_run_server)

    await meta_data_mcp_all.main()

    assert set(imported) == expected_ids
    assert captured["server_name"] == "opendata-mcp-all"
    assert captured["ran"] is True
