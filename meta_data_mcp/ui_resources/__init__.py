"""MCP Apps (``ui://``) shape primitives for meta-data-mcp v2.0.

This package houses the reusable HTML/JS bundles served as ``ui://`` resources.
Each shape primitive is a single self-contained bundle plus a tiny Python
registration module that wires it through ``register_ui_resource``.

The discovery provider (``meta_data_mcp/providers/meta_data_mcp.py``) calls
:func:`register_shapes` once at module import time to mount every primitive
into the server's resource catalog.

NOTE to reviewers of parallel Phase 2 PRs: :func:`register_shapes` is the
merge point. Phase 2b (geofeatures) and Phase 2c (records) each add their
own ``_register_<shape>`` call here.
"""

from __future__ import annotations

from typing import Callable

from mcp import types
from pydantic import AnyUrl

from .shape_timeseries_v1 import register as _register_timeseries

__all__ = ["register_shapes"]


def register_shapes(
    resources: list[types.Resource],
    resources_handlers: dict[str, Callable[[AnyUrl], str | bytes]],
) -> None:
    """Register all v2 shape primitives on the given resource catalog.

    Called from the discovery provider at module load. Mutates ``resources``
    and ``resources_handlers`` in place; raises :class:`ValueError` if any
    primitive's URI is already registered (i.e. boot-time idempotency is
    explicitly NOT guaranteed — calling this twice on the same state is a
    bug, not a no-op).
    """
    _register_timeseries(resources, resources_handlers)
    # Phase 2b/2c will add:
    # _register_geofeatures(resources, resources_handlers)
    # _register_records(resources, resources_handlers)
