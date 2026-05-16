"""Discovery package — state and plugin-loading internals.

The meta server in :mod:`meta_data_mcp.providers.meta_data_mcp` used to
carry ~1,800 LoC mixing three concerns:

- mutable activation state (the in-process catalog of tools / handlers
  / active providers that backs the running MCP server)
- tool definitions (the ~13 discovery / activation / health tools)
- plugin loader plumbing (resolve id → import module → merge its
  ``TOOLS`` / ``TOOLS_HANDLERS`` into the live catalog)

The v2.1 hygiene pass (architecture review §H2) split the first and
third concerns out into :mod:`meta_data_mcp.discovery.state` and
:mod:`meta_data_mcp.discovery.loader`. Tool definitions stay in the
original module so the ~30 tests that ``patch()`` names inside it
(``_engine``, ``serialize_for_llm``, ``REGISTRY``, …) continue to work
without being rewritten.

This ``__init__`` is intentionally empty — neither sub-module has a
single-line public entry point worth re-exporting. Importers should
reach for ``meta_data_mcp.discovery.state`` and
``meta_data_mcp.discovery.loader`` directly.
"""
