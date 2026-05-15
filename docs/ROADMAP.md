# Meta-Data-MCP Roadmap

## Overview

Meta-data-mcp is evolving from a simple provider registry into an intelligent discovery and routing platform. This roadmap outlines the vision for the next 3 versions.

## Version History

### v1.0
- ✅ Basic provider registry
- ✅ find-providers (token-based matching)
- ✅ list-domains, list-regions, describe-provider tools
- ✅ CLI integration

### v1.1 (Current - Merged)
- ✅ Sophisticated multi-criteria routing (`RoutingEngine` in `meta_data_mcp/routing.py`)
- ✅ 4 scoring strategies: `TokenScorer`, `FuzzyScorer`, `MetadataScorer`, `SimpleSemanticScorer`
- ✅ LRU caching with TTL (`OrderedDict` in `RoutingEngine`, default `cache_size=1000`, `cache_ttl_seconds=3600`)
- ✅ Explanation tool: `opendata-explain-choice` (`providers/meta_data_mcp.py:789`)
- ✅ Discovery tools: `opendata-find-providers`, `opendata-list-domains`, `opendata-list-regions`, `opendata-describe-provider`, `opendata-list-providers`, `opendata-create-plugin`, `opendata-draft-spec`
- ✅ CLI: `run`, `version`, `list`, `info`, `setup`, `remove`, `clients`, `cleanup`, `inspect` (`meta_data_mcp/cli.py`)
- ✅ Backward compatibility maintained
- ✅ Provider rename: `opendata_mcp_meta` → `meta_data_mcp`

### v1.1.x — Infrastructure landed since v1.1 (Merged, not previously tracked here)

These shipped via PRs #40–#44 and are not yet reflected in any version label.
They are dependencies for v1.3's reliability story and are partially active today.

- ✅ **HTTP retry + auth-aware response cache** (`meta_data_mcp/utils.py`, PR #40)
  - Exponential backoff with `Retry-After` header parsing (RFC 7231 HTTP-date + delta-seconds)
  - Case-insensitive auth header detection; TTL response cache keyed by a `has_auth` boolean so anonymous and authenticated responses don't collide (note: not partitioned per-token — different tokens still share an entry)
- ✅ **`ProviderConfig` dataclass scaffold** (`meta_data_mcp/provider_config.py`, PR #41)
  - Consolidates `base_url`, `auth_env_var`, `contact_required`, `default_accept`, `rate_limit_per_minute`
  - **Adoption: 1 / 66 providers** (`au_data_gov`). Migrating the rest is tracked under v1.2 below.
- ✅ **Provider health registry + `HealthScorer`** (`meta_data_mcp/health.py`, `routing.py:179`, PR #42)
  - Thread-safe failure/success tracking with time-decay back to 1.0
  - Wired into `RoutingEngine.scorers`
  - Feed: `http_get` now invokes `translate_http_error` and `health.record_failure` / `health.record_success` automatically when callers pass `provider=` (kernel wiring landed; see "Kernel wiring" below)
  - **Default weight = 0.0** until enough providers feed the registry — bumping it before the migration sweep would lift unrecorded-but-healthy providers above no-match thresholds. Raised once the sweep below progresses.
- ✅ **`ProviderError` hierarchy + http→domain translator** (`meta_data_mcp/errors.py`, PR #43)
  - Subclasses: `BadRequestError` (400/422), `NotFoundError` (404), `AuthError` (401/403), `RateLimitError` (429 with `retry_after`), `UpstreamError` (5xx), `NetworkError` (httpx connect/read failures)
  - `translate_http_error(provider, exc)` maps `httpx.HTTPStatusError` / `httpx.RequestError` to the right subclass; `str(err)` is URL-free for safe LLM-client exposure
  - **Adoption: 1 / 66 providers** (`us_data_gov`). Sweep tracked under v1.2 below.
- ✅ **Shared Pydantic parameter types** (`meta_data_mcp/fields.py`, PR #44)
  - `NonEmptyStr`, `Slug` (`^[a-z0-9-]+$`), `PageInt` (`default=1, ge=1`), `PageSize` (`default=20, ge=1, le=1000`)
  - Project-wide validation policy: providers stop re-declaring `min_length=1` and `ge=1` inline
  - **Adoption: 4 / 66 providers** (`us_noaa_awc`, `us_federal_register`, `us_courtlistener`, `global_overpass`). Sweep tracked under v1.2 below.
- ✅ **Kernel wiring: `http_get` → `translate_http_error` + health feed** (`meta_data_mcp/utils.py`)
  - Added `provider: str | None = None` kwarg to `http_get`. When set, the kernel translates `httpx.HTTPStatusError` / `RequestError` into the appropriate `ProviderError` subclass and calls `health.record_success` / `health.record_failure` automatically. When unset, legacy raw-httpx behavior is preserved.
  - Migrated `us_data_gov.py` (the existing error-aware provider) onto `http_get(..., provider=PROVIDER_ID)`, removing its now-redundant handler-level `translate_http_error` calls.
  - Activates the dormant `HealthScorer` feed end-to-end; with `health` weight still `0.0`, routing behavior is unchanged until the sweep below progresses.
- ✅ **Kernel addition: `http_post`** (`meta_data_mcp/utils.py`)
  - Mirrors `http_get`'s defaults (User-Agent, Accept, retry on 429/5xx with `Retry-After`, follow_redirects, `provider=` translation + health feed) for POST requests with a JSON body. Does NOT cache (POST is non-idempotent).
  - Unlocks providers whose APIs require POST queries (e.g. OSV.dev's `/v1/query`).
- ✅ **Security domain expansion: 3 new providers** (registry +3 → 69 total)
  - `global_epss` — FIRST.org Exploit Prediction Scoring System; daily 30-day exploitation probability and percentile rank per CVE. No auth.
  - `us_cisa_kev` — CISA Known Exploited Vulnerabilities catalog; authoritative US-CISA list of actively-exploited vulns under BOD 22-01. No auth.
  - `global_osv_dev` — Google's Open Source Vulnerabilities database; aggregated advisories across GHSA, PYSEC, RustSec, Go, npm, Maven, etc. No auth. First provider to use the new `http_post` helper.
  - All three pass `provider=` to `http_get` / `http_post`, so they feed the health registry and receive translated `ProviderError` exceptions out of the box.
- ✅ **Lazy plugin activation (default tool surface 357 → 11)** (`meta_data_mcp/providers/meta_data_mcp.py`)
  - Previously, `meta-data-mcp run` eagerly imported every registered plugin and merged ~357 tool schemas into the catalog — ~210K tokens of overhead per MCP connection.
  - Now: server starts in **discovery-only mode**. Only the 11 meta tools (`opendata-find-providers`, `opendata-list-domains`, etc., plus the new activate/deactivate/list-active triad) are advertised at startup.
  - New tools: `opendata-activate-provider(provider_id)` and `opendata-deactivate-provider(provider_id)` hot-load and unload individual plugins at runtime, then send a `tools/list_changed` notification so clients refetch their tool catalogs.
  - `opendata-list-active-providers` reports which providers are currently advertised and which tools each contributes.
  - `opendata-find-providers` gains an opt-in `activate_top: int = Field(default=0, ge=0, le=10)` knob — when set, the top-N matches are auto-activated and the response describes what was loaded. Default 0 preserves the read-only semantics of discovery.
  - `META_DATA_MCP_PRELOAD` environment variable selects which providers to preload at startup: comma-separated ids, `*` for "load all" (legacy behavior, full escape hatch), or unset/empty for pure discovery (the new default).
  - `opendata-create-plugin` now uses the same shared activation tracker, so newly-generated plugins also send `tools/list_changed`.
  - Tests: `tests/providers/test_lazy_activation.py` (+15 cases) cover default startup state, activate/deactivate semantics, id-form normalization, `activate_top` opt-in behavior, and the `META_DATA_MCP_PRELOAD` env var.
- ✅ **Coverage gap closure: 5 new providers across 5 verticals** (registry +5 → 74 total; DOMAINS +3 → 30)
  - `global_openaq` — open global air-quality data (PM2.5, PM10, NO2, O3, etc.) from government monitors and low-cost sensors. Closes the *air-quality* vertical (no auth; optional `OPENAQ_API_KEY`).
  - `global_gdelt` — GDELT 2.0 news/events monitoring; article search and tone/volume time-series across 100+ languages. Closes the *news* vertical (no auth; new `news` domain).
  - `global_faostat` — UN FAO statistics: crop/livestock production, trade, food balances, prices, land use, fisheries, forestry, emissions since 1961. Closes the *agriculture* vertical (no auth; new `agriculture` domain).
  - `global_un_comtrade` — UN Comtrade bilateral merchandise/services trade (HS/SITC/BEC/EBOPS) since 1962. Closes the *trade* vertical (free anonymous tier; optional `UN_COMTRADE_API_KEY`; new `trade` domain).
  - `global_opensanctions` — sanctions/PEP/watchlist screening from 200+ official sources (OFAC SDN, UN, EU, UK HMT, national PEPs, ICIJ). Deepens the *security* vertical (no auth for low-volume; optional `OPENSANCTIONS_API_KEY`).
  - All five pass `provider=` to `http_get`, raising kernel-feedback adoption to **9 / 74 providers**.

## v1.2: Hierarchical Discovery + Health Activation (Planned, in design)

**Status as of 2026-05-15: 0% implemented.** Original ship-date estimate (2026-06-03)
is no longer realistic — design has not produced code. Re-baseline below.

### Goals
1. Enable structured browsing of providers by domain → subcategory → provider for users who don't know what they need.
2. Finish the v1.1.x infrastructure rollout so the v1.3 reliability story can land cleanly.

### Carry-over work from v1.1.x

- [x] Wire `translate_http_error` (from `errors.py`, PR #43) into `http_get`'s error path in `utils.py` so it classifies responses and calls `health.record_failure` / `health.record_success`, feeding the dormant `HealthScorer` *(landed via `provider=` kwarg in `http_get`; see v1.1.x "Kernel wiring" above)*
- [ ] Migrate the remaining 65 providers to pass `provider=` to `http_get` so the health feed reflects fleet-wide reliability (1/66 today: `us_data_gov`)
- [ ] Raise the default `health` weight in `RoutingEngine.weights` once enough providers feed the registry (currently `0.0` — see explanatory comment in `routing.py`)
- [ ] Migrate the remaining 65 providers to `ProviderConfig` (1/66 today: `au_data_gov`)
- [ ] Migrate the remaining 62 providers to use `NonEmptyStr` / `Slug` / `PageInt` / `PageSize` from `fields.py` (4/66 today: providers from PR #36 follow-up)
- [ ] Have `http_get` consume `ProviderConfig` directly instead of accepting `base_url`/auth per-call (noted as "future work" in `provider_config.py:6`)

### Scope

#### Data Model Enhancement
- **Subcategories**: Define domain-specific subcategories
  ```
  health/
    ├── epidemiology (disease tracking, outbreak data)
    ├── genomics (DNA, protein sequences)
    ├── clinical (clinical trials, adverse events)
    └── public-health (CDC, WHO datasets)
  
  finance/
    ├── markets (stocks, crypto, FX)
    ├── economic (GDP, inflation, employment)
    └── corporate (SEC filings, balance sheets)
  ```

- **Provider Hierarchy Mapping**: Assign each provider to domain + subcategory(ies)
  - Auto-mapping via description analysis
  - Manual refinement for edge cases

#### New Tools

1. **opendata-list-domains** (enhanced)
   - Input: (optional filters)
   - Output: List of domains with descriptions + subcategory counts
   ```json
   {
     "domains": [
       {
         "name": "health",
         "description": "Medical, epidemiological, and public health data",
         "subcategory_count": 4,
         "provider_count": 12
       }
     ]
   }
   ```

2. **opendata-list-subcategories** (new)
   - Input: domain
   - Output: Subcategories within that domain
   ```json
   {
     "domain": "health",
     "subcategories": [
       {
         "name": "epidemiology",
         "description": "Disease tracking and outbreak data",
         "provider_count": 3
       }
     ]
   }
   ```

3. **opendata-browse-providers** (new)
   - Input: domain, subcategory
   - Output: All providers in that subcategory with brief info
   ```json
   {
     "domain": "health",
     "subcategory": "epidemiology",
     "providers": [
       {
         "id": "global_disease_sh",
         "title": "disease.sh",
         "description": "COVID-19, influenza, vaccine aggregator"
       }
     ]
   }
   ```

#### UX Flow (Example)

```
User: "I need health data but don't know what's available"
↓
LLM calls opendata-list-domains
↓
LLM shows user domains (health, finance, earth-science, etc.)
↓
User: "Show me health"
↓
LLM calls opendata-list-subcategories("health")
↓
LLM shows subcategories (epidemiology, genomics, clinical, public-health)
↓
User: "Epidemiology, please"
↓
LLM calls opendata-browse-providers("health", "epidemiology")
↓
LLM shows disease.sh, disease tracking database, etc.
↓
User: "I'll use disease.sh"
↓
LLM installs and queries it
```

#### Implementation

1. **Extend ProviderEntry** in registry.py:
   ```python
   @dataclass(frozen=True)
   class ProviderEntry:
       # ... existing fields ...
       domain: str                    # Primary domain
       subdomain: str | None = None   # Subcategory within domain
       rank_in_domain: int = 999      # Popularity/recency ranking
   ```

2. **Hierarchical Index** in routing.py:
   ```python
   class HierarchicalIndex:
       domains: dict[str, list[str]]  # domain → [provider_ids]
       subdomains: dict[str, dict[str, list[str]]]  # domain → {subdomain → [provider_ids]}
   ```

3. **New RoutingEngine methods**:
   ```python
   async def browse_domain(domain: str) -> DomainInfo
   async def browse_subdomain(domain: str, subdomain: str) -> SubdomainInfo
   ```

### Testing
- Unit tests for hierarchy index
- Integration tests for browse workflows
- Verify backward compatibility with v1.1 tools

### Timeline (re-baselined 2026-05-15)
- Carry-over infra (health feed + ProviderConfig migration): 1 week
- Hierarchical discovery design: 1 week
- Implementation: 2 weeks
- Testing & docs: 1 week
- **Estimated ship date**: 2026-06-26

---

## v1.3: Agent-Driven Provider Generation (Planned, in design)

**Status as of 2026-05-15: 0% implemented.**

### Goal
Automatically create new providers when users ask for data that doesn't exist, closing gaps in coverage transparently.

### Prerequisites
- Provider generation tool must be hardened (consistent output, test generation)
- Needs agent framework for orchestration

### Scope

#### Hook Points in RoutingEngine
```python
class RoutingEngine:
    on_no_match: Optional[Callable[[Query], Coroutine[ProviderEntry]]]
    on_low_confidence: Optional[Callable[[Query, float], Coroutine[ProviderEntry]]]
```

#### Workflow

```
User: "Give me dark skies observatory data"
↓
RoutingEngine.route() → no matches, score = 0
↓
IF on_no_match configured:
  ├─ Detect intent: "dark skies" = astronomy + geography
  ├─ Call agent: generate_provider(intent)
  │  ├─ Search for dark sky observatories API
  │  ├─ Create provider module (dark_sky_observatories.py)
  │  ├─ Generate test cases
  │  ├─ Run consistency checks
  │  └─ Register in registry
  │
  └─ Re-run RoutingEngine.route()
     └─ Return new provider
↓
LLM: "I found dark sky observatory data! Installing now..."
↓
User gets results
```

#### Implementation

1. **Agent Orchestration**:
   ```python
   async def generate_provider(
       query: str,
       intent: Intent,
       registry: Registry
   ) -> ProviderEntry:
       # 1. Search for APIs matching intent
       # 2. Generate provider module code
       # 3. Generate test cases
       # 4. Validate (consistency, test coverage)
       # 5. Register + return
   ```

2. **Provider Generation Agent** (separate from meta-data-mcp):
   - Takes: intent, data requirements
   - Outputs: provider module code + tests
   - Validates: API accessibility, consistency

3. **Integration in meta_data_mcp.py**:
   ```python
   async def handle_find_providers(...):
       engine = RoutingEngine(
           on_no_match=generate_provider  # Hook
       )
       results = await engine.route(...)
       if not results:
           results = await engine.on_no_match(query)
       return results
   ```

#### New Tool

**opendata-generate-provider** (admin-only)
```python
class GenerateProviderParams(BaseModel):
    intent: str  # "I need climate data for Southeast Asia"
    max_wait_seconds: int = 300
    auto_register: bool = True

async def handle_generate_provider(arguments) -> ProviderGenerationResult:
    # Async provider generation with progress updates
```

### Design Questions (Pending)
- Who can trigger generation? (All users vs. admin only)
- Where does generated code live? (Main repo vs. external registry)
- Confidence threshold for auto-generation (0.5 vs. 0.8)
- Rollback strategy if generated provider has issues

### Testing
- Mock provider generation agent
- Integration tests for no-match hook
- Load testing (prevent DOS via generation requests)

### Timeline (re-baselined 2026-05-15)
- Design & validation: 2 weeks
- Implementation: 4 weeks
- Testing & stabilization: 2 weeks
- **Estimated ship date**: 2026-08-21 (depends on v1.2 ship)

---

## Future: v2.0+ Considerations

### Learning & Personalization
- Track which providers users choose for similar queries
- Rank by user's past success patterns
- Personalization via user profiles

### Advanced Semantics
- Replace SimpleSemanticScorer with embeddings (when deployed)
- Support multi-language queries (translate → search)
- Query reformulation suggestions ("I think you meant...")

### Scaling
- Redis backend for multi-instance deployments
- Pre-compute similarity matrices for 500+ providers
- Distributed caching strategy

### Observability
- Metrics: cache hit rate, latency, provider popularity
- Tracing: request flow through routing engine
- Feedback loops: surface ranking errors to maintainers

### Community
- Public provider registry/marketplace
- User-submitted provider improvements
- Provider quality ratings/reviews

---

## Success Metrics

| Metric | v1.1 | v1.2 | v1.3 |
|--------|------|------|------|
| Query latency (p99) | <100ms | <150ms | <500ms |
| Cache hit rate | >90% | >85% | >80% |
| Provider coverage | 74 | 74+ | Dynamic |
| `ProviderConfig` adoption | 1 / 74 | 74 / 74 | 74 / 74 |
| `errors.py` adoption | 1 / 74 | 74 / 74 | 74 / 74 |
| `fields.py` adoption | 4 / 74 | 74 / 74 | 74 / 74 |
| `http_get(provider=)` adoption | 9 / 74 | 74 / 74 | 74 / 74 |
| `HealthScorer` weight | 0.0 (feed live, weight gated) | >0 | >0 |
| User satisfaction | TBD | >4/5 | >4.5/5 |

---

## How to Contribute

### Filing Issues
- Feature requests: Use template `[ROADMAP]` prefix
- Bugs: Include version (v1.1, v1.2, etc.)
- Enhancement: Link to relevant roadmap section

### Contributing Code
- Pick an item from the roadmap
- Open an issue to discuss approach
- Submit PR with comprehensive tests

### Feedback
- Current experience with v1.1? File feedback issue
- Prioritization for v1.2? Comment on roadmap
- Missing a feature? Describe your use case

---

**Last Updated**: 2026-05-15  
**Maintained By**: meta-data-mcp team  
**Status**: v1.1 merged + v1.1.x infra (PRs #40–#44) merged; v1.2 in design phase, 0% implemented

> Note: `docs/development-roadmap.md` is the legacy OpenDataMCP-era roadmap and is
> superseded by this file. It should be removed in a follow-up cleanup.
