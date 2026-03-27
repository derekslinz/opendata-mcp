# Research Report: Copernicus CDSE API Integration

**Type**: researcher
**Date**: 260321
**Topic**: Copernicus CDSE (STAC/OData)

## Overview
Copernicus Data Space Ecosystem (CDSE) provides access to Sentinel satellite data. It offers two primary APIs for discovery:
1. **STAC API**: Standardized SpatioTemporal Asset Catalog.
   - Endpoint: `https://stac.dataspace.copernicus.eu/v1/`
   - Good for: Searching by bbox, time, and collections.
2. **OData API**: Advanced querying protocol.
   - Endpoint: `https://catalogue.dataspace.copernicus.eu/odata/v1/`
   - Good for: Detailed product metadata and specific filtering.

## Findings
- **Collections**: There are ~185 collections (Sentinel-1, 2, 3, 5P, Landsat, etc.).
- **STAC**: Standard `collections` and `search` endpoints are available.
- **OData**: Supports `$filter`, `$select`, `$top`.
- **Authentication**: Mostly OIDC for data download, but metadata is often public.

## Recommended Approach
- Implement `eu_copernicus.py`.
- Provide a `list_collections` tool using STAC.
- Provide a `search_products` tool using STAC (easier bbox/temporal filtering).
- Provide a `get_product_details` tool using OData by ID.

## Standard Compliance
- Use `httpx` for requests.
- Pydantic models for validation.
- Consistent with `src/odmcp/providers/__template__.py`.
