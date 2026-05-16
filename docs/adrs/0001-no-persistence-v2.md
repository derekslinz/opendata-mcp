# ADR 0001 — No persistent state in v2.x

- **Status:** Accepted
- **Date:** 2026-05-16
- **Deciders:** Derek Linz
- **Architecture review:** §M2 (post-v2.0 hygiene sweep)

## Context

Three pieces of in-process state currently live only in memory:

1. **HTTP response cache** (`transport._response_cache`) — TTL-bounded LRU,
   default ~5 min, capped at 256 entries.
2. **Provider health state** (`health._state`) — per-provider failure /
   success event masses, decayed over time. Fed by `http_get` / `http_post`
   on every call that passes `provider=`.
3. **Activation state** (`providers/meta_data_mcp.py` `ActivationState`) —
   which plugins the user has activated this session.

A single-tenant local MCP server restarts when the user restarts their
host (Claude Desktop, Inspector, etc.). On every restart all three
caches reset to empty:

- The response cache cold-start adds one upstream request per resource
  on first call, then warms naturally.
- The health registry cold-start gives every provider a 1.0 baseline
  ("fully healthy / no recorded failures"). With routing weight at
  0.05 (normalized: ~0.048 of the combined score), this is
  indistinguishable from the steady-state score for a healthy provider.
  Cold-start cost is therefore *zero accuracy loss*, only loss of
  cross-session memory of *bad* providers.
- The activation state cold-start returns the user to the 11-tool
  default surface, which is the documented intent of lazy activation
  (kernel contract from v1.0).

## Decision

**v2.x will not persist any of the three pieces of state to disk.**

Specifically, we will not introduce:

- A SQLite / file-backed response cache.
- A health-state journal written to `~/.meta-data-mcp/`.
- A `activation.json` that restores plugin selection on startup.

The decision applies to all v2.x releases (v2.0 through v2.x). It will
be revisited when one of the triggers below fires.

## Consequences

### Positive

- **Zero on-disk state.** The server has no install-time directory to
  create, no migration story, no schema versioning. Uninstall = delete
  the binary.
- **No multi-process coordination.** A second running instance can't
  corrupt cache or health for the first. We don't need file locking,
  WAL, or a daemon.
- **No PII surface.** Cached responses (some containing API keys via
  query parameters in upstream URLs) live only in memory. No "delete
  my history" feature to build.
- **Tests stay simple.** `utils._response_cache.clear()` and
  `health.clear_health_state()` are enough; no fixture for tmp dirs,
  no teardown for sqlite files.

### Negative (accepted)

- **Repeat cold-start cost.** Every host restart re-fetches everything.
  In practice the upstream APIs we target (data.gov, World Bank, ECB,
  …) handle this trivially. Mitigated by the in-memory cache once warm.
- **Health attribution doesn't survive restart.** A provider that 500s
  for an hour loses its "demoted" status when the host restarts. With
  the current routing weight (0.05 normalized to ~0.048 of combined
  score), the demotion is small to begin with; the user will re-observe
  the failure quickly.
- **Activation memory is per-session.** Users who want a custom default
  set the `META_DATA_MCP_PRELOAD` env var. This is the documented path.

### Neutral

- **`HealthScorer.weight = 0.05` stays.** L3 in the architecture review
  asked whether to raise this further. Decision: no — the 0.05 setting
  is intentionally small so unrecorded providers (1.0 baseline) don't
  get systematically out-ranked by recorded-but-mostly-healthy ones,
  and the Phase 3 routing-test calibration depends on it. Pinned by
  `tests/test_health.py::test_default_engine_health_weight_is_nonzero`.

## When to revisit

Reopen this ADR when **any** of the following becomes true:

1. **Multi-tenant deployment.** If we ship a hosted MCP server where
   one process handles many users, the response cache becomes a
   shared resource and warrants a backing store.
2. **High-availability requirement.** If the server runs behind a
   load balancer with rolling restarts, health and activation state
   need to survive process churn.
3. **Cold-start latency complaints.** Concrete user reports of
   "every restart is slow" for the warm path. Today the warm path
   is sub-100ms once cached; the cold path is bounded by the
   slowest upstream.
4. **Health weight materially > 0.05.** If routing tuning pushes
   the health weight to >0.15 (where it starts dominating the rank
   for borderline matches), the no-persistence cold-start hides
   useful demotion signal across restarts.

When any of those fire, the natural choice is SQLite (single-file,
durable, well-understood concurrency story) over a JSON sidecar or
a real database. Until then, in-memory is the right call.

## References

- Architecture review §M2 (no-persistence decision)
- Architecture review §L3 (HealthScorer weight)
- `meta_data_mcp/transport.py` — `_TTLCache`
- `meta_data_mcp/health.py` — in-memory health registry
- `meta_data_mcp/routing.py:231-240` — health weight wiring
- `tests/test_health.py::test_default_engine_health_weight_is_nonzero`
