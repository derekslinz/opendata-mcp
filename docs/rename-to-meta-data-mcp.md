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
# Old
uv run opendata-mcp setup opendata_mcp_meta

# New
uv run meta-data-mcp setup

# Server key conversion (automatic)
meta_data_mcp  →  meta-data-mcp  (in Claude Desktop config)
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

## Backward Compatibility

✅ **No breaking changes**
- All existing APIs unchanged
- Existing configurations can be migrated with `opendata-mcp cleanup`
- CLI auto-migration support for legacy double-prefixed keys

## Migration Path for Users

### For Claude Desktop Users

**Automatic via CLI:**
```bash
uv run meta-data-mcp setup-all       # Installs meta-data-mcp + companion
```

**Manual Update:**
1. Open `~/Library/Application\ Support/Claude/claude_desktop_config.json`
2. Rename the server key:
   ```json
   {
     "mcpServers": {
       "meta-data-mcp": {
         "command": "uvx",
         "args": ["meta-data-mcp", "run"]
       }
     }
   }
   ```
3. Restart Claude Desktop

### For Developers

**If you import the provider directly:**
```python
# Update imports
from meta_data_mcp.providers.meta_data_mcp import TOOLS, TOOLS_HANDLERS
```

**If you use registry.find_providers():**
- No change needed (registry is unaffected)
- But consider using the new RoutingEngine for better results

## Version Numbering

- **Current**: v0.99.3 (rename + routing engine)
- **Previous**: v0.99.2 (original opendata_mcp_meta)
- **Upgrade path**: v0.99.2 → v0.99.3 is seamless (auto-migration)

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

**Q: Will my existing setup break?**  
A: No. The CLI handles migration automatically. Your config will continue working.

**Q: Do I need to manually update anything?**  
A: For most users, no. Run `uv run opendata-mcp setup-all` to refresh. Manual update of config file is optional.

**Q: What about the PyPI package?**  
A: The PyPI package is now `meta-data-mcp`. Install it with `pip install meta-data-mcp` or `uvx meta-data-mcp`.

**Q: Can I use both the old and new names?**  
A: The old name is no longer recognized. Use `meta_data_mcp` everywhere.

**Q: How does this affect provider generation?**  
A: Provider generation tools should reference `meta_data_mcp` as the meta provider going forward.

---

**Status**: Merged to main via PR #46  
**Effective Date**: 2026-05-13  
**Previous Name**: opendata_mcp_meta  
**Migration Tool**: `uv run meta-data-mcp cleanup`
