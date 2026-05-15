"""v2.0 shape primitive bundles served under ``ui://meta-data-mcp/shape/*/v1``.

This package is the home of the MCP Apps presentation-plane shape
primitives. Each primitive is a self-contained HTML + JS bundle that
the host renders in a sandboxed iframe per the MCP Apps spec
(https://modelcontextprotocol.io/docs/extensions/apps). Provider tools
opt into a primitive by setting ``_meta={"ui": {"resourceUri": <URI>}}``
on their ``types.Tool`` registration (see ``tests/test_ui_resource.py``
for the constructor footgun this avoids).

``register_shapes()`` is the single integration point the discovery
provider calls at server boot. Adding a new primitive means:

1. Drop ``shape_<name>_v<n>.html`` + ``shape_<name>_v<n>.py`` here.
2. Import the module's ``register`` callable below.
3. Call it from ``register_shapes`` so the resource lands in the
   server's catalog.

Versioning is baked into the URI (``/v1``, ``/v2``, ...) per Gotcha G13
of the v2.0 plan — once a primitive has provider adopters, the bundle
shape is frozen and breaking changes ship as ``v2``.
"""

from .shape_records_v1 import register as _register_records


def register_shapes(resources, resources_handlers):
    """Register all v2 shape primitives. Called from the discovery provider.

    The discovery provider (``meta_data_mcp/providers/meta_data_mcp.py``)
    invokes this once at module import so every ``ui://meta-data-mcp/shape/*``
    URI is in the catalog before any tool's ``_meta.ui.resourceUri`` can
    reference it. Calling twice on the same ``(resources, handlers)`` pair
    raises ``ValueError`` from ``register_ui_resource`` — boot-time
    registration is once-per-process; silent dedup would mask real bugs.

    Args:
        resources: The server's ``RESOURCES`` list. Mutated in place.
        resources_handlers: The server's ``RESOURCES_HANDLERS`` dict.
            Mutated in place.
    """
    _register_records(resources, resources_handlers)
    # NOTE to reviewers of parallel Phase 2 PRs: this function is the
    # merge point. Timeseries (PR #61) and geofeatures (PR #62) each add
    # their own ``_register`` import + call here. When this PR merges
    # after either of those, resolve the conflict by keeping all three
    # registrations.
