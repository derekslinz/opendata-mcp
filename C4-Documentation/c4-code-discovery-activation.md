# C4-Code: Discovery & Activation

## Overview
- **Name**: Discovery & Activation
- **Description**: The meta server's ~13 MCP tools (find/list/describe/activate/health/draft/create) plus the plumbing that lazily imports data plugin modules and merges their tools into the live catalog.
- **Location**: `meta_data_mcp/discovery/`, `meta_data_mcp/providers/meta_data_mcp.py`
- **Language**: Python 3.12+
- **Purpose**: Owns the runtime catalog mutation — the discovery surface (find/list/describe/activate) and the activation state itself. The meta server starts in *discovery-only* mode and grows its advertised tool catalog on demand.

## Code Elements

### `discovery/state.py` — ActivationState

`ActivationState` dataclass (lines 41–86) — "All mutable state owned by the meta server's activation surface."

Fields:
| Field | Type | Purpose |
|---|---|---|
| `tools` | `list[types.Tool]` | Advertised tool catalog (line 56) |
| `tools_handlers` | `dict[str, Any]` | tool-name → async handler map (line 57) |
| `active_providers` | `set[str]` | Canonical ids currently activated (line 58) |
| `owner_by_tool` | `dict[str, str]` | tool-name → owning provider id; `"meta"` for the meta server's own tools (lines 59–60) |
| `server` | `Any \| None` | Reference to the running `Server`, set by `main()`; used for `tools/list_changed` best-effort notifications (lines 61–63) |

Methods:
- `snapshot()` (lines 65–73) — returns a 5-tuple `(tools, handlers, active, owner, server)` copy for test restoration.
- `restore(snap)` (lines 75–86) — mutates lists/dicts **in place** so any references held by `create_mcp_server` closures stay valid.

Singleton + back-compat aliases (lines 89–108):
- `_state = ActivationState()` (line 93) — process-wide singleton.
- `RESOURCES: List[Any] = []` (line 100) — independent list (resources don't change at runtime).
- `RESOURCES_HANDLERS: dict[str, Any] = {}` (line 101).
- `TOOLS: List[types.Tool] = _state.tools` (line 102) — alias to the **same list object**.
- `TOOLS_HANDLERS: dict[str, Any] = _state.tools_handlers` (line 103) — alias to the **same dict object**.
- `_active_providers = _state.active_providers` (line 107).
- `_owner_by_tool = _state.owner_by_tool` (line 108).

**Critical invariant** (quoted from module docstring, lines 25–30):

> `TOOLS` and `TOOLS_HANDLERS` are the *same* list and dict objects passed into `create_mcp_server`. Mutating them in place (`TOOLS.append(...)`, `TOOLS_HANDLERS[name] = handler`, `TOOLS[:] = [...]`) is the mechanism by which the running server's advertised catalog stays in sync with activation. Do not reassign either name.

### `discovery/loader.py` — Plugin loader

`_NON_PLUGIN_MODULES: frozenset[str]` (lines 53–59) — `{"__template__", "meta_data_mcp", "meta_data_mcp_all"}`. Module names that must never be loaded as data plugins.

| Function | Signature | Purpose | Lines |
|---|---|---|---|
| `_merge_plugin` | `(module, plugin_id, owner_by_tool=None) -> int` | Merge a plugin module's `TOOLS`/`TOOLS_HANDLERS` into the live catalog with collision detection. Returns count of tools added after filtering. | 62–105 |
| `_resolve_provider_id` | `(provider_id: str) -> str \| None` | Accept underscore (`us_data_gov`) or hyphen (`us-data-gov`) form; return canonical id or `None`. | 108–122 |
| `_notify_tools_changed` | `() -> None` (async) | Best-effort `tools/list_changed` broadcast via `_state.server.request_context.session.send_tool_list_changed()`. Silent on any failure. | 125–138 |
| `_activate_provider` | `(provider_id: str) -> dict[str, Any]` | Import plugin module via `importlib.import_module(f"meta_data_mcp.providers.{canonical}")`, merge its tools. Idempotent — returns `status: already_active` on repeat. Returns status report dict. | 141–191 |
| `_deactivate_provider` | `(provider_id: str) -> dict[str, Any]` | Remove plugin's tools from `TOOLS`/`TOOLS_HANDLERS`. Module stays in `sys.modules` (Python caches modules); only the advertisement is dropped. | 194–220 |
| `_load_all_plugins` | `() -> tuple[int, int]` | Startup bulk loader driven by `META_DATA_MCP_PRELOAD` env var. Empty/unset → load none. `"*"` → load every registered plugin. Comma-separated ids → load those. Returns `(plugins_loaded, tools_added)`. | 223–274 |

Activation report shape (from `_activate_provider`, lines 141–191):
- `status`: `activated` | `already_active` | `error`
- `provider_id`: canonical id
- `tools_added` (when activated): integer count from `_merge_plugin`
- `tools`: sorted list of tool names owned by this provider
- `error` (on failure): one of "unknown provider id — not in registry", "this id is not a data plugin", "plugin failed to import: ...", "plugin imported but exposed no usable tools"

### `providers/meta_data_mcp.py` — Meta server tools

Module-level singletons and constants:
- `_engine = RoutingEngine()` (line 89) — single `RoutingEngine` cached across tool calls.
- `DISCOVERY_TOOL_NAMES: tuple[str, ...]` (lines 79–86) — the 6 meta tools bound to the discovery UI app via `_meta={"ui": {"resourceUri": DISCOVERY_APP_URI}}`. Single source of truth for the binding test.

Imports at lines 39–57 re-export every loader/state symbol so out-of-tree call sites and the ~30 tests that patch by full dotted path (`meta_data_mcp.providers.meta_data_mcp._activate_provider`, etc.) keep working unchanged.

#### Discovery tools (read-only inspection of the registry)

| Tool name | Handler | Schema class | Purpose | Lines |
|---|---|---|---|---|
| `opendata-find-providers` | `handle_find_providers` | `FindProvidersParams` | Multi-criteria registry search (free-text + domain + region) via `_engine.route()`. Returns ranked matches with optional `breakdowns` per-strategy scores when a query is supplied. Optional `activate_top=N` short-circuits to immediate activation. When no match: returns `no_match: true` and a `next_step` pointing at `opendata-draft-spec` → `opendata-create-plugin`. Bound to discovery app. | 102–251 |
| `opendata-list-providers` | `handle_list_providers` | `ListProvidersParams` (limit/offset) | Paginated terse enumeration of every entry in `REGISTRY` — id, title, domains, regions, requires_env. | 1072–1124 |
| `opendata-list-domains` | `handle_list_domains` | `ListDomainsParams` (none) | Returns the controlled domain vocabulary via `list_domains()`. Bound to discovery app. | 957–985 |
| `opendata-list-regions` | `handle_list_regions` | `ListRegionsParams` (none) | Returns the controlled region vocabulary via `list_regions()`. Bound to discovery app. | 993–1021 |
| `opendata-describe-provider` | `handle_describe_provider` | `DescribeProviderParams` (provider_id) | Full registry entry lookup via `get_provider()`. | 1029–1064 |
| `opendata-explain-choice` | `handle_explain_choice` | `ExplainChoiceParams` (query/domain/region/limit) | Same routing call as find-providers but always with `explain=True`; surfaces per-strategy scoring breakdowns for the top-N. | 875–949 |

#### Activation tools (mutate the live catalog)

| Tool name | Handler | Schema class | Purpose | Lines |
|---|---|---|---|---|
| `opendata-activate-provider` | `handle_activate_provider` | `ActivateProviderParams` (provider_id) | Wraps `_activate_provider`; on `status == "activated"` fires `_notify_tools_changed()`. Idempotent. Bound to discovery app. | 1259–1302 |
| `opendata-deactivate-provider` | `handle_deactivate_provider` | `DeactivateProviderParams` (provider_id) | Wraps `_deactivate_provider`; on `status == "deactivated"` fires `_notify_tools_changed()`. | 1310–1343 |
| `opendata-list-active-providers` | `handle_list_active_providers` | `ListActiveProvidersParams` (none) | Reports `active_providers`, `tools_per_provider`, `meta_tool_count`, `plugin_tool_count`. Plugin tools = anything `_owner_by_tool` maps to a non-`"meta"` value. Bound to discovery app. | 1351–1391 |

#### Health tool

| Tool name | Handler | Schema class | Purpose | Lines |
|---|---|---|---|---|
| `opendata-health-snapshot` | `handle_health_snapshot` | `HealthSnapshotParams` (optional provider_ids) | Calls `health.snapshot(ids)`. Default scope is every entry in `iter_registry()` so the discovery UI gets a useful response from an empty call. Returns `snapshot`, `generated_at` (wall-clock), `generated_at_monotonic`. Two clocks exposed because `last_update_ts` is monotonic; mixing clocks would yield nonsense durations. Bound to discovery app. | 1399–1488 |

#### Generation tools (autonomous plugin authoring)

| Tool name | Handler | Schema class | Purpose | Lines |
|---|---|---|---|---|
| `opendata-draft-spec` | `handle_draft_spec` | `DraftSpecParams` (id/title/base_url/description/homepage/tools[...]/server_name?/domains?/regions?/keywords?/requires_env?) | Compose a validated plugin YAML spec from structured inputs. Validates `id` snake_case, `server_name` kebab-case, tool-name kebab-case, path-placeholder/param consistency, parameter types (`str`/`int`/`float`/`bool`), response_format (`json`/`text`). Returns spec_yaml ready to feed into `opendata-create-plugin`. | 659–867 |
| `opendata-create-plugin` | `handle_create_plugin` | `CreatePluginParams` (spec_yaml + domains/regions/keywords/license_note/requires_env) | 6-step pipeline: parse YAML → write `tools/specs/{id}.yaml` → invoke `tools/generate_provider.py --force` subprocess → `importlib.import_module` the freshly-written plugin → `register_plugin(ProviderEntry(...))` in dynamic registry → `_merge_plugin(...)` + `_notify_tools_changed()`. Requires source checkout (the generator script is not present in uvx installs). | 308–532 |

#### Auxiliary registrations in the same module (not discovery tools but live next to them)

- `RESOURCES.append(types.Resource(uri="registry://all-providers", ...))` + `handle_read_all_providers` (lines 1131–1146) — dumps every registry entry as JSON.
- `register_shapes(RESOURCES, RESOURCES_HANDLERS)` and `register_apps(RESOURCES, RESOURCES_HANDLERS)` (lines 1158–1161) — register the `ui://meta-data-mcp/shape/*` and `ui://meta-data-mcp/app/*` UI resource bundles for MCP Apps hosts.
- `PROMPTS` / `PROMPTS_HANDLERS` (lines 1169–1251) — one general `discover-providers` prompt + 4 pre-defined `usecase-*` prompts (financial, climate, healthcare, academic).
- `main(transport, port, host)` (lines 1513–1537) — `await _load_all_plugins()` → `create_mcp_server(...)` → `_state.server = server` → `run_server(...)`.

## Dependencies

### Internal
- `meta_data_mcp.registry` — `REGISTRY`, `get_provider`, `iter_registry`, `list_domains`, `list_regions`, `ProviderEntry`, `register_plugin` (read by every discovery tool; mutated by `opendata-create-plugin`).
- `meta_data_mcp.routing` — `RoutingEngine` (used by `_engine` for find-providers and explain-choice scoring).
- `meta_data_mcp.health` — `health.snapshot(ids)` (used by health-snapshot).
- `meta_data_mcp.utils` — `create_mcp_server`, `run_server`, `serialize_for_llm` (server construction + LLM-safe JSON serialization).
- `meta_data_mcp.ui_resources` — `register_shapes`, `register_apps`, `app_discovery_v1.URI` (UI resource registration + discovery app binding).
- `meta_data_mcp.discovery.state` — re-exported via the meta server module.
- `meta_data_mcp.discovery.loader` — re-exported via the meta server module.
- `tools/generate_provider.py` — subprocess invoked by `opendata-create-plugin`.
- `tools/specs/` — directory where created plugin YAML specs are written.

### External
- `mcp.types` — `Tool`, `Resource`, `Prompt`, `PromptArgument`, `PromptMessage`, `TextContent`, `GetPromptResult`.
- `pydantic` — `BaseModel`, `Field`, `AnyUrl` (input schemas for every tool).
- `pyyaml` — parsing in `opendata-create-plugin`, dumping in `opendata-draft-spec`.
- `importlib` — `import_module` for plugin loading.
- `subprocess`, `sys`, `os`, `re`, `time`, `logging`, `contextlib`, `pathlib` — standard library.
- `anyio` — top-level entry point under `if __name__ == "__main__"`.

## Relationships

```mermaid
flowchart TD
    subgraph META["providers/meta_data_mcp.py — meta server"]
        FIND["opendata-find-providers<br/>opendata-list-providers<br/>opendata-list-domains<br/>opendata-list-regions<br/>opendata-describe-provider<br/>opendata-explain-choice"]
        ACT["opendata-activate-provider<br/>opendata-deactivate-provider<br/>opendata-list-active-providers"]
        HEALTH["opendata-health-snapshot"]
        GEN["opendata-draft-spec<br/>opendata-create-plugin"]
        MAIN["main()<br/>line 1513"]
    end

    subgraph LOADER["discovery/loader.py"]
        ACTIVATE["_activate_provider"]
        DEACTIVATE["_deactivate_provider"]
        MERGE["_merge_plugin"]
        RESOLVE["_resolve_provider_id"]
        NOTIFY["_notify_tools_changed"]
        LOADALL["_load_all_plugins"]
    end

    subgraph STATE["discovery/state.py — ActivationState singleton _state"]
        TOOLS["TOOLS (list)"]
        HANDLERS["TOOLS_HANDLERS (dict)"]
        ACTIVE["_active_providers (set)"]
        OWNER["_owner_by_tool (dict)"]
        SERVERREF["_state.server"]
    end

    REGISTRY["registry.REGISTRY<br/>+ dynamic register_plugin()"]
    ROUTER["routing.RoutingEngine<br/>_engine"]
    HEALTHMOD["health.snapshot()"]
    SDK["mcp Server session"]
    PRELOAD["META_DATA_MCP_PRELOAD<br/>env var"]
    PLUGINMOD["meta_data_mcp.providers.&lt;id&gt;<br/>plugin module"]
    GENERATOR["tools/generate_provider.py"]

    FIND -->|read| REGISTRY
    FIND -->|"_engine.route()"| ROUTER
    HEALTH -->|snapshot(ids)| HEALTHMOD
    HEALTH -->|read ids| REGISTRY

    ACT --> ACTIVATE
    ACT --> DEACTIVATE
    ACT -->|read| ACTIVE
    ACT -->|read| OWNER

    ACTIVATE --> RESOLVE
    ACTIVATE -->|importlib.import_module| PLUGINMOD
    ACTIVATE --> MERGE
    ACTIVATE -->|".add(canonical)"| ACTIVE
    DEACTIVATE --> RESOLVE
    DEACTIVATE -->|"in-place mutation"| TOOLS
    DEACTIVATE -->|"pop"| HANDLERS
    DEACTIVATE -->|"pop / discard"| OWNER
    DEACTIVATE -->|"discard"| ACTIVE

    MERGE -->|"TOOLS.append()"| TOOLS
    MERGE -->|"HANDLERS[name] = h"| HANDLERS
    MERGE -->|"owner[name] = pid"| OWNER

    RESOLVE -->|"iter REGISTRY"| REGISTRY

    ACT -->|"if status == activated"| NOTIFY
    GEN -->|"after _merge_plugin"| NOTIFY
    FIND -->|"if any status == activated"| NOTIFY
    NOTIFY -->|"send_tool_list_changed()"| SDK
    NOTIFY -.->|reads| SERVERREF

    GEN -->|"register_plugin()"| REGISTRY
    GEN -->|subprocess| GENERATOR
    GENERATOR -->|writes file| PLUGINMOD
    GEN -->|importlib.import_module| PLUGINMOD
    GEN --> MERGE

    PRELOAD --> LOADALL
    MAIN -->|"await _load_all_plugins()"| LOADALL
    LOADALL -->|importlib.import_module per id| PLUGINMOD
    LOADALL --> MERGE
    LOADALL -->|".add(pid)"| ACTIVE

    MAIN -->|"create_mcp_server(tools=_state.tools, ...)"| SDK
    MAIN -->|"_state.server = server"| SERVERREF

    TOOLS -.->|same list object| SDK
    HANDLERS -.->|same dict object| SDK
```

Key relationship rules:

1. **Same-object aliasing is load-bearing.** `TOOLS`/`TOOLS_HANDLERS` are the *same* list/dict passed into `create_mcp_server` (state.py docstring lines 25–30, loader.py mutates them in place at lines 101–102, 211–213). Reassignment would silently desync the catalog.
2. **Notification gating.** `_notify_tools_changed` is only fired when the catalog actually changed (`status == "activated"` / `"deactivated"`). The `already_active` no-op deliberately skips it to avoid forcing client refetches — see comments at lines 209–211 and 1280–1283.
3. **`META_DATA_MCP_PRELOAD` semantics.** Unset/empty → 0 plugins (discovery-only mode). `"*"` → every plugin in `REGISTRY` minus `_NON_PLUGIN_MODULES`. Comma-separated ids (underscore or hyphen form, resolved via `_resolve_provider_id`) → just those. Owner-map is seeded with `"meta"` for the meta server's own tools before any plugin loads (loader.py lines 236–237).
4. **Hot-load path for created plugins.** `opendata-create-plugin` goes registry → disk → import → registry write → in-memory merge → notification, all in one tool call; new tools are callable on the next `tools/list` refresh.
