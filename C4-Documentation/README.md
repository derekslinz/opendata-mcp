# C4 Architecture Documentation — meta-data-mcp

This directory holds the [C4 model](https://c4model.com/) architecture
documentation for meta-data-mcp, generated bottom-up from the source.

## Start here

| Level | What it shows | File |
|---|---|---|
| **Context** | The system, its personas, its external dependencies | [c4-context.md](./c4-context.md) |
| **Container** | The single deployable process and its two transports | [c4-container.md](./c4-container.md) |
| **Component** | Seven internal components and how they relate | [c4-component.md](./c4-component.md) |
| **API** | JSON-RPC method catalog | [apis/meta-data-mcp-api.md](./apis/meta-data-mcp-api.md) |

Per the [C4 model docs](https://c4model.com/diagrams), most teams only
need Context + Container diagrams. Component and Code levels are
included here for completeness.

## Components

| Component | Detail |
|---|---|
| MCP Server Bootstrap | [c4-component-mcp-server.md](./c4-component-mcp-server.md) |
| Discovery Engine | [c4-component-discovery-engine.md](./c4-component-discovery-engine.md) |
| Provider Plugin Catalog | [c4-component-provider-plugins.md](./c4-component-provider-plugins.md) |
| HTTP Transport Kernel | [c4-component-transport-kernel.md](./c4-component-transport-kernel.md) |
| Output Pipeline | [c4-component-output-pipeline.md](./c4-component-output-pipeline.md) |
| MCP Apps UI Layer | [c4-component-mcp-apps.md](./c4-component-mcp-apps.md) |
| Plugin Generator & Release Tooling | [c4-component-tooling.md](./c4-component-tooling.md) |

## Code

Code-level docs are organized by architectural unit (not by literal
filesystem walk — the 75 provider plugins follow one pattern, so they
share one doc).

| Unit | Files covered | Detail |
|---|---|---|
| Server Bootstrap | `server.py`, `cli.py`, `utils.py`, `__init__.py` | [c4-code-server-bootstrap.md](./c4-code-server-bootstrap.md) |
| Discovery & Activation | `discovery/state.py`, `discovery/loader.py`, `providers/meta_data_mcp.py` | [c4-code-discovery-activation.md](./c4-code-discovery-activation.md) |
| Registry & Routing | `registry.py`, `routing.py` | [c4-code-registry-routing.md](./c4-code-registry-routing.md) |
| HTTP Transport Kernel | `transport.py`, `errors.py`, `health.py`, `provider_config.py`, `client.py` | [c4-code-transport-kernel.md](./c4-code-transport-kernel.md) |
| Serialization | `serialize.py`, `fields.py` | [c4-code-serialization.md](./c4-code-serialization.md) |
| Provenance | `provenance.py` | [c4-code-provenance.md](./c4-code-provenance.md) |
| Provider Plugins (pattern) | `providers/*.py` (75 modules + `__template__.py`) | [c4-code-provider-plugins.md](./c4-code-provider-plugins.md) |
| UI Resources | `ui_resources/*.py` (11 modules + aggregator) | [c4-code-ui-resources.md](./c4-code-ui-resources.md) |
| Plugin Generator & Scripts | `tools/`, `scripts/` | [c4-code-tooling.md](./c4-code-tooling.md) |

## Notes on this generation

- **Bottom-up generation.** Code-level docs were written first (one per
  architectural unit, in parallel), then components synthesized, then
  the container and context layers on top.
- **75 providers, one doc.** Generating one code-level doc per
  provider would produce ~75 nearly-identical files with no signal.
  Instead, [c4-code-provider-plugins.md](./c4-code-provider-plugins.md)
  documents the shared plugin contract and lists providers by domain
  category with examples.
- **Not OpenAPI for the API spec.** MCP is JSON-RPC 2.0, not REST.
  The API spec lives at
  [apis/meta-data-mcp-api.md](./apis/meta-data-mcp-api.md) as a
  method catalog with request/response schemas.
- **Diagrams are Mermaid.** All diagrams render natively on GitHub and
  most modern Markdown viewers. The system context diagram uses
  Mermaid's `C4Context` syntax.

## Cross-references to repository documentation

- [README.md](../README.md) — user-facing setup and env vars
- [docs/meta-data-mcp-architecture.md](../docs/meta-data-mcp-architecture.md)
- [docs/ROADMAP.md](../docs/ROADMAP.md)
- [docs/adrs/0001-no-persistence-v2.md](../docs/adrs/0001-no-persistence-v2.md) — the no-persistence decision (ADR-0001)
