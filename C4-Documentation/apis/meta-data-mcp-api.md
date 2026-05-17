# API Catalog: meta-data-mcp

> **Why this isn't an OpenAPI spec.** MCP is JSON-RPC 2.0, not REST.
> Endpoints, paths, and HTTP verbs aren't the abstraction — methods
> and their `params` schemas are. OpenAPI would require contorting
> the protocol's actual shape. This document is the equivalent: a
> complete catalog of every JSON-RPC method the server handles, with
> request/response schemas and notes on dynamic namespaces (tools,
> resources).

## Transport binding

| Transport | Wire format | Endpoints | Auth |
|---|---|---|---|
| **stdio** | Line-delimited JSON-RPC 2.0 on stdin/stdout | n/a | None (process-local trust) |
| **SSE** | JSON-RPC 2.0 framed inside Server-Sent Events | `GET /`, `GET /sse`, `POST /messages` | `Authorization: Bearer <token>` when `META_DATA_MCP_AUTH_TOKEN` is set |

The `GET /` SSE endpoint returns a JSON health response (no auth) for
uptime probes:

```json
{ "status": "running", "server": "meta-data-mcp",
  "transport": "sse",
  "endpoints": { "sse": "/sse", "messages": "/messages" } }
```

## Static JSON-RPC methods

Every MCP server implements a fixed set of methods. meta-data-mcp wires
all six on the SDK's low-level `Server`:

### `initialize`
Standard MCP handshake. Server returns capabilities (resources, tools,
prompts) and protocol version. Handled entirely by the SDK.

### `tools/list`
Returns the currently-advertised tool catalog.

**Request**: `{}`
**Response**: `{ tools: [Tool] }`

Each `Tool` has `name`, `description`, `inputSchema` (JSON Schema), and
optional `_meta` (e.g. `{ ui: { resourceUri: "ui://..." } }` for MCP
Apps wiring).

A fresh server returns ~11 meta tools (see "Meta tools" below). After
`opendata-activate-provider` activates a plugin, the response grows by
that plugin's tools — the SDK emits `tools/list_changed` so clients
re-fetch.

### `tools/call`
Invokes a tool by name. The hot path; everything else exists to support
this.

**Request**: `{ name: string, arguments?: object }`
**Response**: `{ content: [TextContent | ImageContent | EmbeddedResource], isError?: boolean }`

Server-side flow:
1. Dispatcher resolves `name` in `TOOLS_HANDLERS`.
2. Handler runs (async). May make outbound HTTP via the kernel.
3. Result is `[Content]`.
4. **If** `META_DATA_MCP_PROVENANCE` is truthy, the dispatcher calls
   `provenance.attach(result, tool_name=name, arguments=arguments)`.
   The first content block gets `_meta["meta-data-mcp/provenance"]
   = { sha256, timestamp }`.
5. Result returned.

Errors translate via `errors.translate_http_error`. URLs are redacted
from error messages so they don't leak credentials.

### `resources/list`
Returns the currently-advertised resource catalog. meta-data-mcp ships
~11 `ui://` resources from the MCP Apps UI Layer plus any plugin-local
resources.

**Request**: `{}`
**Response**: `{ resources: [Resource] }`

Each `Resource` has `uri`, `name`, `description`, and `mimeType`.

### `resources/read`
Returns the bytes of one resource.

**Request**: `{ uri: string }`
**Response**: `{ contents: [ReadResourceContents] }`

meta-data-mcp pins the MIME on read via a precomputed `_mime_by_uri`
lookup — without that, the SDK's default `read_resource` decorator
ships `ui://` resources as `text/plain` and the host refuses to mount
them. UI resources are served with `text/html;profile=mcp-app` (the
`;profile=mcp-app` parameter is required — hosts reject anything
without it as "Unsupported UI resource content format").

### `prompts/list` and `prompts/get`
Both handlers are wired, but meta-data-mcp ships no prompts. `list`
returns `[]`; `get` raises `AttributeError`.

## Dynamic method namespace: `tools/call`

`tools/call` dispatches into ~366 distinct tools when fully activated.
They split into two groups:

### Meta tools (always present, ~12)

Always advertised. Defined in
`meta_data_mcp/providers/meta_data_mcp.py`. See
[c4-component-discovery-engine.md](../c4-component-discovery-engine.md)
for the full breakdown.

| Tool | Purpose |
|---|---|
| `opendata-find-providers` | Free-text query → ranked `ScoredProvider[]` with breakdowns |
| `opendata-list-providers` | List all providers (paginated, filterable) |
| `opendata-list-domains` | List the DOMAINS vocabulary (29 tags) |
| `opendata-list-regions` | List the REGIONS vocabulary (11 tags) |
| `opendata-describe-provider` | Full metadata for one provider by id |
| `opendata-explain-choice` | Why did the engine rank provider X above Y? |
| `opendata-activate-provider` | Import + merge a plugin into the live catalog |
| `opendata-deactivate-provider` | Remove a plugin from the live catalog |
| `opendata-list-active-providers` | What's currently activated |
| `opendata-health-snapshot` | `{provider_id: health_score}` for every active provider |
| `opendata-draft-spec` | LLM-assisted YAML spec scaffolding |
| `opendata-create-plugin` | Generate + hot-load a new plugin module |

### Plugin tools (lazy-loaded, ~355 across 75 plugins)

Available only after the relevant plugin has been activated. Each
plugin contributes 1-N tools; counts are per-provider (see
[c4-component-provider-plugins.md](../c4-component-provider-plugins.md)
for the categorized inventory). Tool names follow the convention
`<provider-short>-<verb>`, e.g.:

- `world-bank-indicators`
- `nvd-search-cves` / `nvd-get-cve` / `nvd-cve-history`
- `overpass-query`
- `crossref-search`

Each plugin tool's handler is required to:
- Use `http_get(url, *, provider=PROVIDER_ID)` for all outbound HTTP (NOT `httpx` directly)
- Return a size-bounded `[TextContent]` via one of `serialize_for_llm` / `to_records_text` / `to_timeseries_text` / `to_geofeatures_text` / `to_entity_graph_text`
- Validate arguments via a Pydantic schema using the shared field types (`NonEmptyStr`, `Slug`, `PageInt`, `PageSize`)

## Dynamic method namespace: `resources/read`

`resources/read` dispatches into ~11 `ui://meta-data-mcp/...` resources
(plus any plugin-local non-UI resources). All UI resources are served
with `text/html;profile=mcp-app`. See
[c4-component-mcp-apps.md](../c4-component-mcp-apps.md) for the full
catalog of `ui://` URIs.

### Bidirectional postMessage (MCP Apps extension)

Apps (the 8 interactive `ui://app/...` resources) communicate with the
host via `postMessage` events from inside the sandboxed iframe. This
is a client-side protocol (not a JSON-RPC method) — the host receives
the event and proxies it as a `tools/call` to the server. From the
server's perspective these are normal `tools/call` invocations; the
server has no knowledge that they originated in an iframe.

## Notifications (server → client)

### `tools/list_changed`
Emitted by `_notify_tools_changed()` after `_activate_provider` or
`_deactivate_provider` mutates `TOOLS` in place. Best-effort — the
function silently no-ops if no session is available, since activation
already succeeded locally.

### `resources/list_changed`
The MCP spec defines this; meta-data-mcp's static UI resources are
registered at boot and never change at runtime, so this notification
is not emitted today.

## Auth model

| Property | Value |
|---|---|
| **Discovery / list / read** | Always allowed (within the bearer-auth perimeter, if any) |
| **Tool invocation** | Always allowed (within the bearer-auth perimeter) |
| **Activation tools** | Always allowed — there's no user-vs-admin distinction; anyone with a connection can activate |
| **stdio transport** | Trust-on-connect (no auth — process-local) |
| **SSE transport** | Bearer-token auth via `META_DATA_MCP_AUTH_TOKEN` if set, otherwise unauthenticated (a `warning` is logged at boot) |

## Audit / provenance contract

When `META_DATA_MCP_PROVENANCE` is truthy, every successful
`tools/call` response carries:

```json
{
  "content": [
    {
      "type": "text",
      "text": "...",
      "_meta": {
        "meta-data-mcp/provenance": {
          "sha256": "<64-char lowercase hex>",
          "timestamp": "YYYY-MM-DDTHH:MM:SS.mmmZ"
        }
      }
    }
  ]
}
```

The digest covers a canonical envelope `{tool, arguments, content}` —
content blocks dumped with `model_dump(mode="json", by_alias=True,
exclude_none=True)` with `_meta` stripped from each, JSON-serialized
with `sort_keys=True, separators=(",",":"), ensure_ascii=True`. Every
kwarg is load-bearing; see `meta_data_mcp/provenance.py` for the
verbatim receiver verification recipe.

## Versioning

The server's version is the package `__version__` (currently
`2.1.0`). MCP protocol version is negotiated via the SDK's
`initialize` handler; meta-data-mcp does not pin a specific protocol
version.

Tool names and resource URIs include explicit versions where
meaningful (e.g. `ui://meta-data-mcp/shape/timeseries/v1`); a breaking
shape change ships as `v2` alongside `v1` rather than replacing.

## Related Documentation

- [../c4-container.md](../c4-container.md) — single-container deployment view
- [../c4-component.md](../c4-component.md) — seven-component master index
- [../c4-context.md](../c4-context.md) — personas + user journeys
