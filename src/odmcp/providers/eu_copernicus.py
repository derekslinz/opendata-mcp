"""
Copernicus Earth Observation Data API Client

This module provides interfaces to access the Copernicus Data Space Ecosystem (CDSE).
It allows discovery of satellite data (Sentinel, Landsat, etc.) through STAC and OData APIs.

Features:
- Collection discovery through STAC Collections API
- Product search via STAC Search API (bbox, datetime, collection)
- Detailed product metadata retrieval via OData API

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

# Initialize logging
log = logging.getLogger(__name__)

# Constants
STAC_BASE_URL = "https://stac.dataspace.copernicus.eu/v1"
ODATA_BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# Copernicus Collections
###################


class ListCollectionsParams(BaseModel):
    """Parameters for listing Copernicus satellite collections."""

    limit: int = Field(
        default=20, description="Maximum number of collections to return"
    )


class CollectionInfo(BaseModel):
    """Basic information about a Copernicus collection."""

    id: str = Field(..., description="The unique ID of the collection")
    title: Optional[str] = Field(None, description="The title of the collection")
    description: Optional[str] = Field(
        None, description="Description of the collection"
    )


def list_copernicus_collections(params: ListCollectionsParams) -> List[CollectionInfo]:
    """Fetch available satellite data collections from STAC API."""
    endpoint = f"{STAC_BASE_URL}/collections"
    response = httpx.get(endpoint, timeout=10.0)
    response.raise_for_status()

    data = response.json()
    collections = []
    for col in data.get("collections", []):
        collections.append(
            CollectionInfo(
                id=col.get("id"),
                title=col.get("title"),
                description=col.get("description"),
            )
        )
        if len(collections) >= params.limit:
            break
    return collections


async def handle_list_collections(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the copernicus-list-collections tool call."""
    try:
        params = ListCollectionsParams(**(arguments or {}))
        collections = list_copernicus_collections(params)
        text = str([c.model_dump() for c in collections])
        return [
            types.TextContent(type="text", text=text[:10000])
        ]  # Truncate if too long
    except httpx.HTTPError as e:
        log.error(f"HTTP error listing Copernicus collections: {e}")
        return [
            types.TextContent(
                type="text", text=f"Error: Unable to reach Copernicus STAC API. {e}"
            )
        ]
    except Exception as e:
        log.error(f"Error listing Copernicus collections: {e}")
        return [
            types.TextContent(type="text", text=f"An unexpected error occurred: {e}")
        ]


TOOLS.append(
    types.Tool(
        name="copernicus-list-collections",
        description="List available Copernicus satellite data collections (e.g., sentinel-2a-l2a).",
        inputSchema=ListCollectionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["copernicus-list-collections"] = handle_list_collections

###################
# Copernicus Product Search (STAC)
###################


class SearchProductsParams(BaseModel):
    """Parameters for searching products via STAC."""

    collection: str = Field(
        ..., description="The collection ID to search (e.g., 'sentinel-2a-l2a')"
    )
    bbox: Optional[List[float]] = Field(
        None, description="Bounding box [min_lon, min_lat, max_lon, max_lat]"
    )
    datetime: Optional[str] = Field(
        None,
        description="Time range (e.g., '2023-01-01T00:00:00Z/2023-01-02T23:59:59Z')",
    )
    limit: int = Field(default=10, description="Maximum number of results (max 100)")


def search_copernicus_products(params: SearchProductsParams) -> dict:
    """Search for products using STAC Search endpoint."""
    endpoint = f"{STAC_BASE_URL}/search"
    query_params = {"collections": [params.collection], "limit": min(params.limit, 100)}
    if params.bbox:
        query_params["bbox"] = params.bbox
    if params.datetime:
        query_params["datetime"] = params.datetime

    response = httpx.post(endpoint, json=query_params, timeout=15.0)
    response.raise_for_status()
    return response.json()


async def handle_search_products(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the copernicus-search-products tool call."""
    try:
        params = SearchProductsParams(**(arguments or {}))
        data = search_copernicus_products(params)
        # Summarize results to keep it concise for LLM
        features = data.get("features", [])
        summary = []
        for feat in features:
            props = feat.get("properties", {})
            summary.append(
                {
                    "id": feat.get("id"),
                    "datetime": props.get("datetime"),
                    "cloud_cover": props.get("eo:cloud_cover"),
                    "bbox": feat.get("bbox"),
                }
            )
        return [types.TextContent(type="text", text=str(summary)[:10000])]
    except httpx.HTTPError as e:
        log.error(f"HTTP error searching Copernicus products: {e}")
        return [
            types.TextContent(
                type="text", text=f"Error searching Copernicus products: {e}"
            )
        ]
    except Exception as e:
        log.error(f"Error searching Copernicus products: {e}")
        return [
            types.TextContent(type="text", text=f"An unexpected error occurred: {e}")
        ]


TOOLS.append(
    types.Tool(
        name="copernicus-search-products",
        description="Search for satellite imagery products based on spatial and temporal criteria.",
        inputSchema=SearchProductsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["copernicus-search-products"] = handle_search_products

###################
# Copernicus Product Metadata (OData)
###################


class ProductMetadataParams(BaseModel):
    """Parameters for getting detailed product metadata."""

    product_id: str = Field(..., description="The unique Product ID (UUID)")


def fetch_product_metadata(params: ProductMetadataParams) -> dict:
    """Fetch detailed metadata for a specific product ID via OData."""
    endpoint = f"{ODATA_BASE_URL}/Products({params.product_id})"
    response = httpx.get(endpoint, timeout=10.0)
    response.raise_for_status()
    return response.json()


async def handle_get_product_metadata(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the copernicus-get-product-metadata tool call."""
    try:
        params = ProductMetadataParams(**(arguments or {}))
        data = fetch_product_metadata(params)
        return [types.TextContent(type="text", text=str(data)[:15000])]
    except httpx.HTTPError as e:
        log.error(f"HTTP error fetching Copernicus product metadata: {e}")
        return [
            types.TextContent(type="text", text=f"Error fetching product metadata: {e}")
        ]
    except Exception as e:
        log.error(f"Error fetching Copernicus product metadata: {e}")
        return [
            types.TextContent(type="text", text=f"An unexpected error occurred: {e}")
        ]


TOOLS.append(
    types.Tool(
        name="copernicus-get-product-metadata",
        description="Get detailed technical metadata for a specific Copernicus product ID via OData.",
        inputSchema=ProductMetadataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["copernicus-get-product-metadata"] = handle_get_product_metadata


async def main():
    from mcp.server.stdio import stdio_server
    from odmcp.utils import create_mcp_server

    # create the server
    server = create_mcp_server(
        "eu-copernicus", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    # run the server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
