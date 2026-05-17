# C4-Component: Discovery Engine

## Overview
- **Name**: Discovery Engine
- **Description**: Static + dynamic provider catalog (Registry), five-scorer relevance engine (RoutingEngine), and the ~12 MCP tools that expose them as the "meta" surface — find/list/describe providers, activate/deactivate plugins, draft specs, snapshot health.
- **Type**: Service (in-process)
- **Technology**: Python 3.12+, MCP SDK Tool/Handler model, Pydantic schemas

## Purpose
- Provides the 11-tool default catalog the LLM sees on connect, *before* any provider plugin activates.
- Implements lazy activation so `tools/list` stays small until the user (or LLM) actually needs a specific provider.
- Offers algorithm-driven relevance ranking with explainable per-scorer breakdowns — the "smart layer" that answers *what providers exist*, *which match this query*, and *how do I turn them on*.

## Software Features
- 75-entry seed catalog with controlled `DOMAINS` (29 tags) and `REGIONS` (11 tags) vocabularies.
- Five-strategy scoring pipeline: `TokenScorer`, `FuzzyScorer`, `MetadataScorer`, `SimpleSemanticScorer`, `HealthScorer`.
- Default weights `0.30 / 0.20 / 0.25 / 0.25 / 0.05` — the `0.05` health weight is pinned by `tests/test_health.py::test_default_engine_health_weight_is_nonzero` so reverts must be intentional.
- `OrderedDict`-backed LRU score cache keyed by MD5 of `(query|domain|region|explain)` with TTL guard under `asyncio.Lock`.
- `has_relevance` gate prevents the health-only baseline (`1.0` for unrecorded providers) from making every entry match nonsense queries.
- `ScoredProvider.breakdown` carries the per-scorer raw `0.0–1.0` values, surfaced verbatim by `opendata-explain-choice`.
- Imperative activation pipeline: `_activate_provider` → `importlib.import_module(...)` → `_merge_plugin` → in-place mutation of `TOOLS` / `TOOLS_HANDLERS` → `_notify_tools_changed`.
- `META_DATA_MCP_PRELOAD` env var enables startup-time bulk activation (`""` = none, `"*"` = all, comma-separated ids = subset).
- Dynamic plugin generation: `opendata-draft-spec` composes a validated YAML spec → `opendata-create-plugin` writes the new `.py`, hot-imports it, registers a `ProviderEntry`, and merges its tools live.

## Code Elements
- [c4-code-discovery-activation.md](./c4-code-discovery-activation.md) — `discovery/state.py` (`ActivationState`, `_state`, `TOOLS`/`TOOLS_HANDLERS` aliases), `discovery/loader.py` (`_activate_provider`, `_deactivate_provider`, `_merge_plugin`, `_resolve_provider_id`, `_notify_tools_changed`, `_load_all_plugins`), `providers/meta_data_mcp.py` (the meta server's ~12 tools).
- [c4-code-registry-routing.md](./c4-code-registry-routing.md) — `registry.py` (`Registry`, `ProviderEntry`, `REGISTRY` singleton, `_STATIC_ENTRIES`, `iter_registry`, `find_providers`, `get_provider`, `list_domains`, `list_regions`), `routing.py` (`RoutingEngine`, `Scorer` strategies, `ScoredProvider`, `find_providers_sophisticated`).

## Interfaces

### Meta tools (exposed via MCP, always available before activation)
- **Discovery**: `opendata-find-providers`, `opendata-list-providers`, `opendata-list-domains`, `opendata-list-regions`, `opendata-describe-provider`, `opendata-explain-choice`
- **Activation**: `opendata-activate-provider`, `opendata-deactivate-provider`, `opendata-list-active-providers`
- **Health**: `opendata-health-snapshot`
- **Generation**: `opendata-draft-spec`, `opendata-create-plugin`

Six of these (`find-providers`, `list-domains`, `list-regions`, `activate-provider`, `list-active-providers`, `health-snapshot`) are bound to the discovery UI app via `_meta={"ui": {"resourceUri": DISCOVERY_APP_URI}}` and listed in `DISCOVERY_TOOL_NAMES`.

### Python API (internal, used by other components and tests)
- `iter_registry() -> Iterable[ProviderEntry]` — every static + dynamic entry in insertion order.
- `find_providers(query, domain, region, limit=20) -> list[ProviderEntry]` — legacy integer-score search.
- `RoutingEngine.route(query=None, domain=None, region=None, limit=20, explain=False) -> list[ScoredProvider]` — five-scorer weighted routing.
- `_activate_provider(provider_id) -> dict` / `_deactivate_provider(provider_id) -> dict` — imperative activation report.
- `register_plugin(entry: ProviderEntry) -> None` — idempotent runtime registration of a new `ProviderEntry`.
- `_load_all_plugins() -> tuple[int, int]` — startup bulk loader driven by `META_DATA_MCP_PRELOAD`.

## Dependencies

### Components used
- **HTTP Transport Kernel** — `HealthScorer` lazy-imports `meta_data_mcp.health.health_score(provider_id)`; `opendata-health-snapshot` calls `health.snapshot(ids)`.
- **Provider Plugins** — `_activate_provider` invokes `importlib.import_module(f"meta_data_mcp.providers.{canonical}")`; each plugin must expose `TOOLS` / `TOOLS_HANDLERS` for `_merge_plugin` to absorb.
- **Plugin Generator** — `opendata-create-plugin` shells out to `tools/generate_provider.py --force` to materialize the new `.py` file before importing it.
- **UI Resources** — `register_shapes` / `register_apps` populate `RESOURCES` / `RESOURCES_HANDLERS`; `app_discovery_v1.URI` is the discovery app binding.
- **Server / Transport** — `main()` calls `create_mcp_server(tools=_state.tools, ...)` then `run_server(...)`, and stores the running `Server` on `_state.server` so `_notify_tools_changed` can call `send_tool_list_changed()`.

### External
- `mcp.types` (`Tool`, `Resource`, `Prompt`, `TextContent`, `GetPromptResult`).
- `pydantic` (`BaseModel`, `Field`, `AnyUrl`) — input schemas for every tool.
- `pyyaml` — spec parse/dump for the generation tools.
- Stdlib: `importlib`, `subprocess`, `dataclasses`, `difflib`, `hashlib`, `asyncio`, `collections.OrderedDict`, `re`, `time`, `logging`, `contextlib`, `pathlib`.

## Component Diagram

```mermaid
flowchart TD
    LLM["LLM / MCP client"]

    subgraph DISC["Discovery Engine"]
        subgraph TOOLS_GRP["Meta tools (providers/meta_data_mcp.py)"]
            FIND["opendata-find-providers"]
            EXPLAIN["opendata-explain-choice"]
            LISTING["opendata-list-providers<br/>opendata-list-domains<br/>opendata-list-regions<br/>opendata-describe-provider"]
            ACTIVATE_T["opendata-activate-provider"]
            DEACTIVATE_T["opendata-deactivate-provider"]
            LIST_ACTIVE["opendata-list-active-providers"]
            HEALTH_T["opendata-health-snapshot"]
            DRAFT["opendata-draft-spec"]
            CREATE["opendata-create-plugin"]
        end

        ENGINE["RoutingEngine _engine<br/>(routing.py)"]
        REG[("REGISTRY singleton<br/>75 static + N dynamic<br/>(registry.py)")]

        subgraph SCORERS["Five-scorer pipeline (weights normalized)"]
            T["TokenScorer 0.30"]
            FZ["FuzzyScorer 0.20"]
            M["MetadataScorer 0.25"]
            SEM["SimpleSemanticScorer 0.25"]
            HS["HealthScorer 0.05"]
        end

        subgraph STATE["ActivationState _state (discovery/state.py)"]
            TOOLS_L["TOOLS (list)"]
            HANDLERS["TOOLS_HANDLERS (dict)"]
            OWNER["_owner_by_tool"]
            ACTIVE_SET["_active_providers"]
            SREF["_state.server"]
        end

        subgraph LOADER["discovery/loader.py"]
            ACT_FN["_activate_provider"]
            MERGE["_merge_plugin"]
            NOTIFY["_notify_tools_changed"]
            PRELOAD_FN["_load_all_plugins"]
        end
    end

    HEALTH_MOD["health module<br/>(HTTP Transport Kernel)"]
    PLUGIN_MOD["meta_data_mcp.providers.&lt;id&gt;"]
    GEN_SCRIPT["tools/generate_provider.py"]
    SDK["mcp SDK Server session"]
    PRELOAD_ENV["META_DATA_MCP_PRELOAD env"]

    LLM -->|tools/call| FIND
    LLM --> EXPLAIN
    LLM --> LISTING
    LLM --> ACTIVATE_T
    LLM --> DEACTIVATE_T
    LLM --> LIST_ACTIVE
    LLM --> HEALTH_T
    LLM --> DRAFT
    LLM --> CREATE

    FIND -->|route(query)| ENGINE
    EXPLAIN -->|route(explain=True)| ENGINE
    LISTING -->|iter_registry / get_provider| REG

    ENGINE -->|iter_registry + filters| REG
    ENGINE --> T
    ENGINE --> FZ
    ENGINE --> M
    ENGINE --> SEM
    ENGINE --> HS
    HS -.lazy import.-> HEALTH_MOD
    HEALTH_T --> HEALTH_MOD
    HEALTH_T -->|default scope| REG

    ACTIVATE_T --> ACT_FN
    DEACTIVATE_T --> ACT_FN
    LIST_ACTIVE -->|read| ACTIVE_SET
    LIST_ACTIVE -->|read| OWNER

    ACT_FN -->|importlib.import_module| PLUGIN_MOD
    ACT_FN --> MERGE
    MERGE -->|in-place append| TOOLS_L
    MERGE -->|in-place write| HANDLERS
    MERGE -->|owner[name]=pid| OWNER
    ACT_FN -->|add canonical id| ACTIVE_SET

    ACTIVATE_T -->|"if activated"| NOTIFY
    DEACTIVATE_T -->|"if deactivated"| NOTIFY
    CREATE -->|"after merge"| NOTIFY
    FIND -->|"if activate_top fired"| NOTIFY
    NOTIFY -->|send_tool_list_changed()| SDK
    NOTIFY -.reads.-> SREF

    DRAFT -->|composes YAML| CREATE
    CREATE -->|subprocess --force| GEN_SCRIPT
    GEN_SCRIPT -->|writes .py| PLUGIN_MOD
    CREATE -->|importlib.import_module| PLUGIN_MOD
    CREATE -->|register_plugin| REG
    CREATE --> MERGE

    PRELOAD_ENV --> PRELOAD_FN
    PRELOAD_FN -->|per id| ACT_FN

    TOOLS_L -.same list object.-> SDK
    HANDLERS -.same dict object.-> SDK
    SDK -->|tools/list| LLM
```

### Two canonical flows

**Query flow** — LLM calls `opendata-find-providers` → `RoutingEngine.route(query)` checks LRU cache → on miss, iterates `REGISTRY` applying hard `domain`/`region` filters → for each survivor runs the five scorers, weighting `0.30 / 0.20 / 0.25 / 0.25 / 0.05`, dropping any whose only positive signal is health (the `has_relevance` gate) → sorts by `(-score, id)` → caches → returns the top-`limit` `ScoredProvider` list (with `breakdown` populated when `explain=True`).

**Activation flow** — LLM calls `opendata-activate-provider` → `_activate_provider` resolves the id (underscore or hyphen form) via `_resolve_provider_id` → `importlib.import_module("meta_data_mcp.providers.<id>")` → `_merge_plugin` appends to the live `TOOLS` list, writes into `TOOLS_HANDLERS`, and stamps `_owner_by_tool[name] = provider_id` — all *in place* on the same objects passed into `create_mcp_server` → `_active_providers.add(canonical)` → on `status == "activated"`, `_notify_tools_changed()` calls `send_tool_list_changed()` on the SDK session → the client refetches `tools/list` and now sees the plugin's tools alongside the meta surface.
