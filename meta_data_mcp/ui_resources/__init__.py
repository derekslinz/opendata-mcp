"""MCP Apps shape primitives and apps (v2.0 Phases 2 & 3).

Two flavors of UI resource live here:

- ``ui://meta-data-mcp/shape/<name>/<version>`` — *primitives*: passive
  renderers for the three canonical payload contracts (timeseries,
  geofeatures, records). Phase 2.

- ``ui://meta-data-mcp/app/<name>/<version>`` — *apps*: interactive
  panels that issue outbound ``tool_call`` messages back to the host.
  Phase 3 shipped ``discovery``; Phase 5 adds ``vulnerability`` /
  ``museum`` / ``molecular`` / ``news-tone`` / ``network-topology``
  and will add ``entity-graph`` / ``trade-flows`` / etc. as follow-ups.

The two public entry points are :func:`register_shapes` and
:func:`register_apps`, called once from the discovery provider during
server boot. Each registers its resources against the server's shared
``RESOURCES`` / ``RESOURCES_HANDLERS`` collections.
"""

from __future__ import annotations

from typing import Callable

from mcp import types
from pydantic import AnyUrl

from .app_discovery_v1 import register as _register_discovery_app
from .app_entity_graph_v1 import register as _register_entity_graph_app
from .app_molecular_v1 import register as _register_molecular_app
from .app_museum_v1 import register as _register_museum_app
from .app_network_topology_v1 import register as _register_network_topology_app
from .app_news_tone_v1 import register as _register_news_tone_app
from .app_trade_flows_v1 import register as _register_trade_flows_app
from .app_vulnerability_v1 import register as _register_vulnerability_app
from .shape_geofeatures_v1 import register as _register_geofeatures
from .shape_records_v1 import register as _register_records
from .shape_timeseries_v1 import register as _register_timeseries

__all__ = ["register_apps", "register_shapes"]


def register_shapes(
    resources: list[types.Resource],
    resources_handlers: dict[str, Callable[[AnyUrl], str | bytes]],
) -> dict[str, str]:
    """Register all v2 shape primitives on the given server state.

    Called once from the discovery provider (``providers/meta_data_mcp.py``)
    at module import time.

    Returns a dict mapping shape name → URI for callers that want to
    log or surface the wiring; the return value is advisory and may be
    ignored.
    """
    return {
        "timeseries/v1": _register_timeseries(resources, resources_handlers),
        "geofeatures/v1": _register_geofeatures(resources, resources_handlers),
        "records/v1": _register_records(resources, resources_handlers),
    }


def register_apps(
    resources: list[types.Resource],
    resources_handlers: dict[str, Callable[[AnyUrl], str | bytes]],
) -> dict[str, str]:
    """Register all v2 apps on the given server state.

    Apps are split from shapes because they're conceptually different:
    shapes render passively, apps issue outbound ``tool_call`` messages
    back to the host. Splitting the registration entry points makes it
    obvious which discovery-provider tools should bind to which class
    of resource.

    Returns a dict mapping app name → URI; the return value is advisory.
    """
    return {
        "discovery/v1": _register_discovery_app(resources, resources_handlers),
        "trade-flows/v1": _register_trade_flows_app(resources, resources_handlers),
        "vulnerability/v1": _register_vulnerability_app(resources, resources_handlers),
        "entity-graph/v1": _register_entity_graph_app(resources, resources_handlers),
        "museum/v1": _register_museum_app(resources, resources_handlers),
        "molecular/v1": _register_molecular_app(resources, resources_handlers),
        "news-tone/v1": _register_news_tone_app(resources, resources_handlers),
        "network-topology/v1": _register_network_topology_app(
            resources, resources_handlers
        ),
    }
