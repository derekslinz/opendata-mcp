"""
OpenData MCP All — Dynamic Aggregator Server

A single MCP server that exposes the tools of many (or all) opendata-mcp
providers under one process. Useful when a host environment can only attach a
single MCP server, or when you want one combined namespace for exploration.

At import time this module does NOT import any provider modules — it stays
cheap and side-effect free. Provider discovery, import, and tool merging all
happen inside :func:`main` so the cost is paid only when the server actually
runs.

Filtering is controlled by two environment variables (union of both filters
is taken when both are set):

- ``OPENDATA_MCP_DOMAINS``
    Comma-separated list of domain names (see ``opendata_mcp.registry.DOMAINS``)
    such as ``"health,finance"``. Providers tagged with any listed domain are
    loaded.

- ``OPENDATA_MCP_PROVIDERS``
    Comma-separated list of provider ids (e.g. ``"us_nasa,global_gbif"``).
    These specific providers are loaded directly.

If neither variable is set (or both are empty), **all** registered providers
are loaded.

Tool-name collisions across providers are detected and logged as warnings; the
first provider to register a given tool name wins and subsequent registrations
are skipped.
"""

from __future__ import annotations

import importlib
import logging
import os
from typing import Any, List

import mcp.types as types

from opendata_mcp.registry import REGISTRY, find_providers

log = logging.getLogger(__name__)


# Registration Variables — populated lazily inside main(), kept empty at
# module-import time so that simply importing this module is cheap.
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


# Module names within ``opendata_mcp.providers`` that should never be treated
# as data providers by the aggregator.
_SKIP_MODULES: frozenset[str] = frozenset(
    {
        "__template__",
        "meta_data_mcp",
        "opendata_mcp_all",
    }
)


def _split_csv_env(name: str) -> list[str]:
    """Parse a comma-separated environment variable into a clean list."""
    raw = os.getenv(name, "") or ""
    return [piece.strip() for piece in raw.split(",") if piece.strip()]


def _resolve_provider_ids(
    domains: list[str],
    provider_ids: list[str],
) -> list[str]:
    """Compute the set of provider ids to load given the two env filters.

    - If both ``domains`` and ``provider_ids`` are empty: return every id in
      the registry.
    - Otherwise: union of (a) all providers in any listed domain and
      (b) all explicitly named provider ids.
    """
    if not domains and not provider_ids:
        return [entry.id for entry in REGISTRY]

    selected: dict[str, None] = {}  # ordered set
    for domain in domains:
        for entry in find_providers(domain=domain, limit=10_000):
            selected.setdefault(entry.id, None)
    for pid in provider_ids:
        selected.setdefault(pid, None)
    return list(selected.keys())


def _merge_provider(
    module: Any,
    provider_name: str,
    merged_tools: list[types.Tool],
    merged_handlers: dict[str, Any],
    owner_by_tool: dict[str, str],
) -> int:
    """Merge a provider module's TOOLS/TOOLS_HANDLERS into the aggregate.

    Returns the number of tools actually added (after collision filtering).
    """
    tools = getattr(module, "TOOLS", None) or []
    handlers = getattr(module, "TOOLS_HANDLERS", None) or {}

    added = 0
    for tool in tools:
        name = tool.name
        if name in owner_by_tool:
            log.warning(
                "Tool name collision: '%s' already registered by '%s'; "
                "skipping duplicate from '%s'.",
                name,
                owner_by_tool[name],
                provider_name,
            )
            continue
        handler = handlers.get(name)
        if handler is None:
            log.warning(
                "Provider '%s' lists tool '%s' but has no matching handler; skipping.",
                provider_name,
                name,
            )
            continue
        merged_tools.append(tool)
        merged_handlers[name] = handler
        owner_by_tool[name] = provider_name
        added += 1
    return added


async def main(
    transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"
) -> None:
    """Entry point — discover, import, merge, then serve."""
    # Local import keeps module-import cheap.
    from opendata_mcp.utils import create_mcp_server, run_server

    domains = _split_csv_env("OPENDATA_MCP_DOMAINS")
    provider_ids = _split_csv_env("OPENDATA_MCP_PROVIDERS")

    selected_ids = _resolve_provider_ids(domains, provider_ids)

    merged_tools: list[types.Tool] = []
    merged_handlers: dict[str, Any] = {}
    owner_by_tool: dict[str, str] = {}
    loaded_count = 0

    for provider_id in selected_ids:
        if provider_id in _SKIP_MODULES:
            continue
        module_path = f"opendata_mcp.providers.{provider_id}"
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            log.warning("Could not import provider '%s': %s", provider_id, exc)
            continue
        except Exception as exc:  # noqa: BLE001 — never block other providers
            log.warning("Error importing provider '%s': %s", provider_id, exc)
            continue

        _merge_provider(
            module,
            provider_id,
            merged_tools,
            merged_handlers,
            owner_by_tool,
        )
        loaded_count += 1

    log.info(
        "OpenData MCP All — loaded %d providers, %d tools",
        loaded_count,
        len(merged_tools),
    )

    server = create_mcp_server(
        "opendata-mcp-all",
        resources=RESOURCES,
        resources_handlers=RESOURCES_HANDLERS,
        tools=merged_tools,
        tools_handlers=merged_handlers,
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
