# Meta-Data-MCP Roadmap

## Overview

Meta-data-mcp is evolving from a simple provider registry into an intelligent discovery and routing platform. This roadmap outlines the vision for the next 3 versions.

## Version History

### v1.0
- ✅ Basic provider registry
- ✅ find-providers (token-based matching)
- ✅ list-domains, list-regions, describe-provider tools
- ✅ CLI integration

### v0.99.3 (Current - Merged)
- ✅ Sophisticated multi-criteria routing (RoutingEngine)
- ✅ 4 scoring strategies (Token, Fuzzy, Metadata, Semantic)
- ✅ LRU caching with TTL
- ✅ Explanation tool (show ranking breakdown)
- ✅ Backward compatibility maintained
- ✅ Provider rename: opendata_mcp_meta → meta_data_mcp

## v1.2: Hierarchical Discovery (Planned)

### Goal
Enable structured browsing of providers by domain → subcategory → provider for users who don't know what they need.

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

### Timeline
- Design: 1 week
- Implementation: 2 weeks
- Testing & docs: 1 week
- **Estimated ship date**: 2026-06-03

---

## v1.3: Agent-Driven Provider Generation (Planned)

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

### Timeline
- Design & validation: 2 weeks
- Implementation: 4 weeks
- Testing & stabilization: 2 weeks
- **Estimated ship date**: 2026-07-15

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

| Metric | v0.99.3 | v1.2 | v1.3 |
|--------|---------|------|------|
| Query latency (p99) | <100ms | <150ms | <500ms |
| Cache hit rate | >90% | >85% | >80% |
| Provider coverage | 50 | 50 | Dynamic |
| User satisfaction | TBD | >4/5 | >4.5/5 |

---

## How to Contribute

### Filing Issues
- **Feature requests**: Use template `[ROADMAP]` prefix
- **Bugs**: Include version (v0.99.3, v1.2, etc.)
- **Enhancement**: Link to relevant roadmap section

### Contributing Code
- Pick an item from the roadmap
- Open an issue to discuss approach
- Submit PR with comprehensive tests

### Feedback
- Current experience with v0.99.3? File feedback issue
- Prioritization for v1.2? Comment on roadmap
- Missing a feature? Describe your use case

---

**Last Updated**: 2026-05-13  
**Maintained By**: meta-data-mcp team  
**Status**: v0.99.3 merged, v1.2 in design phase
