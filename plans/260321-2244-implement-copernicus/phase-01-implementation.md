# Phase 01: Implementation of `eu_copernicus.py`

## Overview
Create the main provider module for Copernicus.

## Proposed Tools
1. `list_collections`: List available satellite data collections.
2. `search_products`: Search for satellite imagery by bbox, date, and collection.
3. `get_product_metadata`: Get detailed OData metadata for a specific product ID.

## Implementation Steps
1. Create `src/odmcp/providers/eu_copernicus.py`.
2. Define Pydantic models for STAC and OData responses.
3. Implement `CopernicusProvider` class inheriting from `BaseProvider` (check `ch_sbb.py` for exact base class if any, or follow template).
4. Implement tool handlers with `httpx`.

## Success Criteria
- CLI can list the provider.
- `odmcp info eu_copernicus` works.
- Tools return valid data from CDSE.
