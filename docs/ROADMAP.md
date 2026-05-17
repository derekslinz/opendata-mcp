# Meta-Data-MCP Roadmap

## Overview

Meta-data-mcp evolved from a simple provider registry into an
intelligent discovery and routing platform, then a structured-data
**presentation layer** built on the MCP Apps protocol extension. This
roadmap captures actual shipped history (v1.0 → v2.1) and what's next.

---

## Shipped

### v1.0 — Provider registry
- ✅ Basic provider registry + static seed list
- ✅ `opendata-find-providers` (token-based matching)
- ✅ `opendata-list-domains`, `-list-regions`, `-describe-provider`
- ✅ CLI integration (`meta-data-mcp` binary, `run` / `setup` / `inspect`)

### v1.1 — Sophisticated routing
- ✅ Multi-criteria `RoutingEngine` (`meta_data_mcp/routing.py`)
- ✅ Five scorers: `TokenScorer`, `FuzzyScorer`, `MetadataScorer`, `SimpleSemanticScorer`, `HealthScorer`
- ✅ LRU + TTL cache (OrderedDict, default `cache_size=1000`, `cache_ttl=3600s`)
- ✅ `opendata-explain-choice` (score-breakdown introspection)
- ✅ Full meta-tool surface: find / list-domains / list-regions / describe / list-providers / activate / deactivate / list-active / draft-spec / create-plugin

### v1.1.x — Infrastructure landed (PRs #40–#44, plus follow-ups)
- ✅ **HTTP retry + auth-aware response cache** (`transport.py`) — exponential backoff with RFC 7231 `Retry-After`, TTL response cache keyed by auth-presence
- ✅ **`ProviderConfig` dataclass scaffold** (`provider_config.py`) — adoption stayed at 1/75 and was deferred (see "Abandoned scope" below)
- ✅ **Provider health registry + `HealthScorer`** (`health.py`) — thread-safe failure/success tracking with exp-decay (τ=300s) back to 1.0, wired into `RoutingEngine.scorers`
- ✅ **`ProviderError` hierarchy + `translate_http_error`** (`errors.py`) — `BadRequestError`, `NotFoundError`, `AuthError`, `RateLimitError`, `UpstreamError`, `NetworkError`; URL-redacted messages safe for LLM exposure
- ✅ **Shared Pydantic parameter types** (`fields.py`) — `NonEmptyStr`, `Slug`, `PageInt`, `PageSize`
- ✅ **Kernel wiring: `http_get(provider=)`** — mandatory contract; automatic error translation + health feed when set
- ✅ **`http_post` kernel addition** — same retries/translation/health feed; **not cached** (POST is non-idempotent)
- ✅ **Security-domain expansion** — +3 providers (`global_epss`, `us_cisa_kev`, `global_osv_dev`)
- ✅ **Lazy plugin activation** — default tool surface 357 → 11; `opendata-activate-provider` / `-deactivate` triad; `tools/list_changed` notification; `META_DATA_MCP_PRELOAD` env var
- ✅ **Coverage-gap closure** — +5 providers (`global_openaq`, `global_gdelt`, `global_faostat`, `global_un_comtrade`, `global_opensanctions`) closing air-quality, news, agriculture, trade, and sanctions verticals

### v1.2 — Absorbed into v2.0

The originally-planned v1.2 ("hierarchical discovery") **was not
shipped as planned**. Its UX goal — browse providers by domain →
subcategory → provider — was delivered differently via the v2.0
**Discovery App** (`ui://meta-data-mcp/app/discovery/v1`), which
renders the same browse experience as an interactive panel rather
than as new tools. The carry-over migration sweep (`provider=`,
`ProviderConfig`, `fields.py`) ran opportunistically and partially —
see "Migration adoption" in metrics below.

### v1.3 — Partial / absorbed

The originally-planned v1.3 ("agent-driven provider generation") was
shipped in **runtime form** as two meta tools that let an LLM scaffold
new providers at conversation time:

- ✅ `opendata-draft-spec` — LLM-assisted YAML spec scaffolding
- ✅ `opendata-create-plugin` — generates the provider module from a spec, hot-loads it, registers it dynamically, emits `tools/list_changed`

The "no-match hook" with autonomous background generation was not
shipped — the LLM driving the meta tools provides the orchestration
loop directly. The version bump to 1.3.0 covered these two tools.

### v2.0 — MCP Apps presentation layer
**Released as `v2.0.0`** (commit `deb863d`).

v1.x was a structured-data dispenser. v2.0 turned it into a
structured-data **presentation layer** via the [MCP Apps protocol
extension](https://modelcontextprotocol.io/docs/extensions/apps):
tools declare `_meta.ui.resourceUri` pointing at a `ui://` resource
the host renders in a sandboxed iframe alongside the tool's result.

- ✅ **Phase 1 — Foundation primitives**
  - `register_ui_resource()` helper in `server.py`
  - `_meta=` constructor-kwarg pattern documented (the `populate_by_name=False` footgun is pinned by regression test)
- ✅ **Phase 2 — Three shape primitives**
  - `ui://meta-data-mcp/shape/timeseries/v1` (Plotly via CDN)
  - `ui://meta-data-mcp/shape/geofeatures/v1` (Leaflet self-hosted)
  - `ui://meta-data-mcp/shape/records/v1` (dependency-free table + facets)
- ✅ **Phase 3 — Discovery App**
  - `ui://meta-data-mcp/app/discovery/v1` — interactive discovery panel
  - Closes the v1.2 hierarchical-browse UX gap (this is why v1.2 was absorbed)
  - Activates HealthScorer end-to-end: `errors.translate_http_error` no longer penalizes 401/403 (V12 fix); `RoutingEngine.weights["health"]` raised from 0.0 to **0.05**
- ✅ **Phase 4 — Provider shape adoption**
  - 71 of 75 plugins bind to a shape primitive via `ui_resources.shape_*` URI
- ✅ **Phase 5 — Custom apps for special-shape providers** (7 apps)
  - `app/vulnerability/v1` (NVD + CISA KEV + OSV + EPSS — CVSS radar, severity heatmap)
  - `app/museum/v1` (Met Museum image grid + provenance)
  - `app/molecular/v1` (PubChem + RCSB PDB 3Dmol viewer)
  - `app/news-tone/v1` (GDELT tone timeline)
  - `app/entity-graph/v1` (OpenAlex + Wikidata + OpenSanctions force-directed graph)
  - `app/trade-flows/v1` (UN Comtrade Sankey)
  - `app/network-topology/v1` (RIPE Stat ASN graph)
- ✅ **Phase 6 — Generator + tooling**
  - Generator `response_shape` field auto-wires shape URIs in scaffolded plugins
  - `test_ui_bundle_sizes.py` CI gate (warn at 100KB, error at 1MB)
  - Headless smoke-test coverage for `ui://` resources
  - `make pr-check N=<num>` 7-step merge gate

### v2.1 — Architecture hygiene + version bump
**Released as `v2.1.0`** (commit `34f5946`).

A 5-PR pass driven by the architecture review's H/M/L priority list,
ending with version bump to 2.1.0.

- ✅ **Repo invariants test** (PR #85) — generator-TODO lint + bundle CDN-origin allowlist
- ✅ **H1: `utils.py` split** (PR #86) — extracted `serialize.py`, `transport.py`, `server.py`; `utils.py` becomes a back-compat re-export shim
- ✅ **M2: ADR 0001** (PR #87) — no persistent state in v2.x; revisit triggers documented
- ✅ **H2: Discovery extraction** (PR #88) — `discovery/state.py` + `discovery/loader.py` split out of `providers/meta_data_mcp.py`
- ✅ **M1: `URIS` aggregator** (PR #89) — flat catalog mapping every `ui://` resource with 3-way alignment test
- ✅ **L3: HealthScorer weight = 0.05** confirmed (was the 0.0 → 0.05 raise from v2.0 Phase 3; kept after review)

---

## In flight

### v2.2 — Optional provenance (on branch `feat/provenance-meta`, PR #90)

Opt-in tamper-evident provenance metadata on every `tools/call`
result, attached to the first content block's `_meta` under the
`meta-data-mcp/provenance` key:

- `sha256` of the canonical `(tool, arguments, content)` envelope
- `timestamp` (ISO 8601 UTC, millisecond precision)

Enabled by `META_DATA_MCP_PROVENANCE` env var. Default off — zero
per-call overhead until opted in. Designed for downstream audit /
compliance pipelines that need to verify "tool A returned X" vs.
"tool B returned X" using only data the receiver already has.

**Status**: feature complete, 34 dedicated tests, full receiver
verification recipe in module docstring + README. CI green; awaiting
merge decision.

---

## Planned

### v2.3 — Security & maturity track (committed)

Concrete items with target effort, prioritized for the next minor.
See ADR 0002 and PROVENANCE_SPEC.md for the docs-side anchors.

| Priority | Item | Effort |
|---|---|---|
| **P0** | **ADR 0002 — autogen plugin security posture.** Per-session ephemeral plugins by default; persistent plugins require explicit promotion; `META_DATA_MCP_AUTOGEN_BASE_URL_ALLOWLIST` env var; plugin-output content-type sniffing. **ADR shipped** at [`docs/adrs/0002-autogen-security.md`](./adrs/0002-autogen-security.md). Framework change to follow: ephemeral-by-default in `_activate_provider`, new `opendata-promote-plugin` tool, allow-list check, content-type warning. | Doc landed; small framework change pending |
| **P0** | **OAuth2/OIDC support + scoped bearer tokens.** Today's `META_DATA_MCP_AUTH_TOKEN` is a single all-or-nothing bearer. Replace with scoped tokens: `read` (discovery + safe tool calls), `write` (activate/deactivate plugins), `admin` (promote plugin, modify allow-list). OAuth2 / OIDC provider integration for token issuance. **Prerequisite** for safe SSE deployment per ADR 0002. | 1–2 days |
| **P1** | **Provenance canonicalization spec — standalone document.** The receiver recipe was previously in the `provenance.py` module docstring + README only. Promoted to [`docs/PROVENANCE_SPEC.md`](./PROVENANCE_SPEC.md) so audit pipelines have a stable URL to cite without source-diving. | Done |
| **P1** | **Per-provider rate-limit governance + cost-class metadata.** Add `rate_limit_per_minute` and `cost_class` (free / metered / paid) fields to `ProviderEntry`; surface in `opendata-describe-provider`; enforce in `http_get` via per-provider semaphore. Lets operators bound expensive upstream calls and lets the LLM make cost-aware tool choices. | 2–3 days |
| **P2** | **Streamable HTTP transport migration plan.** MCP is moving toward Streamable HTTP as the SSE successor. Design the transport-pluggability seam *now* (the `run_server` dispatch in `server.py` already has a transport arg) so the migration is a new branch in the dispatch, not a rewrite. Ship the design doc; defer implementation until upstream stabilizes. | 1 week (design + scaffold) |
| **P2** | **Subprocess / sandbox isolation for autogen plugins.** The enforcement layer for ADR 0002. Options: firejail / nsjail (Linux), `subprocess` + restricted Python (cross-platform but weaker), JS-style V8-isolate equivalent. Decide on tradeoffs; ship the simplest viable. | 1–2 weeks |
| **P3** | **New-domain proposal queue with similarity-check gate.** When `opendata-create-plugin` proposes a `ProviderEntry` whose `domain` value isn't in the static DOMAINS vocabulary, route it through a similarity-check gate (Levenshtein vs. existing entries) so we don't accumulate `health` / `healthcare` / `medical` duplicates. Maintainer reviews queued proposals before they enter the vocabulary. | 1 day |

### v2.x opportunistic — no fixed timeline

These ship as the codebase asks for them.

- **Completion of the `provider=` migration sweep** — 41/75 providers
  pass `provider=` to `http_get`/`http_post` today; the remaining 34
  bypass the health/error pipeline and route around the kernel
  guarantees. Goal: 75/75 so health weight can be raised above 0.05.
- **Generator hardening** — round-trip parity test (regenerate every
  provider from its spec, diff against committed module) to catch
  drift between spec and hand-tuned code.
- **Additional MCP Apps** — domain-specific apps as new providers
  arrive (no committed list).
- **Provenance HMAC variant** — current sha256 is integrity-only; a
  keyed-HMAC mode would add authenticity. Gated on a concrete user
  ask.
- **Hosted deployment** — public SSE endpoint so non-Claude clients
  can use the server remotely. Systemd installer already in `scripts/`;
  the missing piece is the public deployment + ops story. Promotion
  of v2.3 P0 items from "planned" to "shipped" is a prerequisite
  for safe hosted SSE — see ADR 0002.

### v3.0 — only if real demand justifies it

The ADR-0001 revisit triggers double as v3.0 entry conditions:

- **Persistent state.** Multi-tenant deployment or HA requirement →
  health/cache need Redis or equivalent.
- **Cold-start complaints.** Currently health weight is 0.05 across a
  fresh process; if users notice ranking inversions in the first hour,
  pre-warm or persist the registry.
- **Health weight > 0.15.** Would require enough providers feeding the
  registry and enough confidence in the decay model to make health a
  dominant scorer.
- **Multi-language SDK clients.** Discovery tools surface that non-MCP
  integrations could benefit from — would require a more language-
  neutral protocol surface.

---

## Abandoned scope

Decisions to drop work that was originally on the roadmap, with
reasons:

| Item | Why dropped |
|---|---|
| `ProviderConfig` fleet migration (1/75 today) | The dataclass scaffold landed but didn't propagate. ADR-0001 implicitly accepts this — providers stay simple, kernel arguments stay per-call. Revisit only if a concrete pattern demands it. |
| `opendata-list-subcategories` / `opendata-browse-providers` tools | The v1.2 browse UX shipped instead via the Discovery App (v2.0 Phase 3). Adding separate tools would duplicate the App's surface. |
| Autonomous "no-match hook" provider generation (v1.3 design) | The runtime tools (`opendata-draft-spec`, `opendata-create-plugin`) put the LLM in the orchestration seat. Background-agent generation would require trust-boundary work that isn't on the critical path. |
| Public provider marketplace (v2.0+ ideas section) | Out of scope until the hosted deployment story exists; tracked under "Hosted deployment" above. |
| Embedding-based semantic scorer | `SimpleSemanticScorer` works well enough for the current 75-provider catalog. Revisit if the catalog grows past ~200 or query patterns shift. |
| Redis-backed multi-instance scaling | Gated on HA requirement — see ADR-0001 revisit triggers. |

---

## Migration adoption (actual state — 2026-05-17)

| Adoption metric | v1.1 baseline | v2.1 actual |
|---|---|---|
| `http_get(provider=)` adoption | 10 / 75 | **41 / 75** |
| `ProviderConfig` adoption | 1 / 75 | 1 / 75 (scope dropped — see above) |
| `fields.py` adoption | 4 / 75 | 5 / 75 (partial, opportunistic) |
| `HealthScorer` weight | 0.0 | **0.05** (raised in v2.0 Phase 3, kept after L3 review) |
| Plugins binding to `ui://shape/*` | 0 / 75 | **71 / 75** (v2.0 Phase 4) |
| Lazy activation default | n/a | ✅ default surface 357 → 11 (v1.1.x) |
| MCP Apps coverage | 0 | 11 ui:// resources (3 shapes + 8 apps) |

---

## Operational targets

| Metric | v1.1 actual | v2.1 actual | Goal |
|---|---|---|---|
| Query latency (p99) | <100ms | <100ms | <100ms |
| Cache hit rate | >90% | >90% | >85% |
| Provider coverage | 75 | 75 | grow only when a real coverage gap exists |
| Default tool catalog size | 357 | 11 (lazy) | keep <20 by default |
| UI bundle weight per resource | n/a | <100KB warn / <1MB error | <100KB |

---

## How to Contribute

### Filing Issues
- Feature requests: prefix with `[ROADMAP]`
- Bugs: include the running version (`meta-data-mcp version`)
- Enhancements: link to the relevant roadmap section above

### Contributing Code
1. Pick an item from "Planned" or "v2.3+ opportunistic"
2. Open an issue or draft PR to discuss approach
3. Submit PR with tests; the 7-step merge gate (`make pr-check N=<num>`) runs as part of review

### Feedback
- Current experience with v2.1? File a feedback issue
- Missing a feature? Describe your use case — coverage decisions are driven by real asks, not speculation
- Want a hosted instance? Comment on the "Hosted deployment" item

---

**Last Updated**: 2026-05-17
**Maintained By**: meta-data-mcp team
**Current version**: `2.1.0` (commit `34f5946`); `feat/provenance-meta` branch (PR #90) staged for v2.2; v2.3 security & maturity track scoped (ADR 0002 + PROVENANCE_SPEC.md shipped, OAuth2 / rate-limit / sandbox / Streamable HTTP scaffolding pending)

> Note: `docs/development-roadmap.md` is the legacy OpenDataMCP-era roadmap and is
> superseded by this file. It should be removed in a follow-up cleanup.
