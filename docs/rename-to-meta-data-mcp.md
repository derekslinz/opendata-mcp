# Rename: opendata_mcp_meta → meta_data_mcp

## Why This Change?

The original name `opendata_mcp_meta` was inherited from the project's genesis but became increasingly inaccurate as the provider evolved. The new name **`meta_data_mcp`** better reflects what the provider actually does and carries rich semantic meaning.

## Dual Meaning of "Meta-Data-MCP"

### 1. Literal: Metadata Aggregator
The provider maintains and exposes **metadata** about all opendata-mcp providers:
- Domain taxonomy (health, finance, earth-science, etc.)
- Region coverage (US, EU, global, etc.)
- Keywords and descriptions
- Required environment variables
- Provider capabilities and tool inventory

### 2. Figurative: Meta-Level Router
The provider operates at a **meta-level** above individual data providers:
- Intelligent routing: "Which provider best answers this question?"
- Decision-making: Ranks providers by relevance, freshness, user intent
- Discovery: Guides LLMs toward the right provider without overloading them
- Transparency: Explains *why* each provider was chosen

## What Changed

### File Rename
```
opendata_mcp/providers/opendata_mcp_meta.py  →  meta_data_mcp.py
tests/providers/test_opendata_mcp_meta.py    →  test_meta_data_mcp.py
```

### CLI Integration
```bash
# Old (multi-server model, separate per-provider CLI)
uv run opendata-mcp setup opendata_mcp_meta

# New (single unified server)
uv run meta-data-mcp setup
uv run meta-data-mcp run --transport stdio
```

### Python Imports
```python
# Old
from opendata_mcp.providers.opendata_mcp_meta import TOOLS

# New
from meta_data_mcp.providers.meta_data_mcp import TOOLS
```

### Documentation Updates
- README.md
- system_prompt.md
- Docstrings and comments
- CLI help text

## Version Numbering

- **Current**: v1.1 (rename + routing engine)
- **Previous**: v1.0 (original opendata_mcp_meta)

## Testing & Verification

All existing tests pass with the new name:
- 15/15 tests in test_meta_data_mcp.py ✅
- All imports resolve correctly ✅
- CLI default provider updated ✅
- Documentation consistent ✅

## Why This Matters

### For Users
- **Clarity**: The name now reflects what the provider does (routing + metadata)
- **Semantics**: "meta-data" suggests both metadata AND meta-level intelligence
- **Branding**: Clearer positioning as the gateway/discovery layer

### For Contributors
- **Naming Consistency**: Matches the provider's evolved role
- **Self-Documenting**: New developers understand purpose from the name
- **Future-Proof**: Scales conceptually as the provider gains more meta capabilities

### For the Project
- **Professionalism**: Shows thoughtful evolution, not just accumulation
- **Marketing**: Easier to explain: "meta-data-mcp is your intelligent discovery layer"
- **Architecture Clarity**: Separates concerns: individual providers vs. routing layer

## FAQs

**Q: How does this affect provider generation?**  
A: Provider generation tools should reference `meta_data_mcp` as the meta provider going forward.

---

**Status**: Merged to main via PR #19  
**Effective Date**: 2026-05-13  
**Previous Name**: opendata_mcp_meta
