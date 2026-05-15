"""MCP Apps shape primitives (v2.0 Phase 2).

Each shape primitive is a self-contained HTML+JS bundle served as a
``ui://meta-data-mcp/shape/<name>/<version>`` resource. The MCP Apps
extension (https://modelcontextprotocol.io/docs/extensions/apps) lets
the host render the bundle in a sandboxed iframe alongside a tool's
result; providers bind to a primitive by declaring
``_meta={"ui": {"resourceUri": <URI>}}`` on the Tool.

The single public entry point is :func:`register_shapes`, called once
from the discovery provider during server boot. It registers every
shape primitive against the server's ``RESOURCES`` / ``RESOURCES_HANDLERS``.
"""

from __future__ import annotations

from typing import Callable

from mcp import types
from pydantic import AnyUrl

from .shape_geofeatures_v1 import register as _register_geofeatures

__all__ = ["register_shapes"]


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

    NOTE to reviewers of parallel Phase 2 PRs: this function is the
    merge point. Timeseries (Phase 2a) and records (Phase 2c) each add
    their own ``_register`` call here. Three near-identical lines, no
    coordination needed beyond filename / import ordering.
    """
    return {
        "geofeatures/v1": _register_geofeatures(resources, resources_handlers),
    }
