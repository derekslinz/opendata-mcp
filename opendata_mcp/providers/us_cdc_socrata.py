"""
US CDC Open Data Provider (Socrata)

This module provides interfaces to the US Centers for Disease Control and
Prevention open data catalog hosted on the Socrata Open Data API (SODA) at
data.cdc.gov.

License: Most CDC datasets are in the public domain. Individual dataset
licenses may apply; consult the dataset metadata for details.

Environment variables:
- None required for basic access. Authenticated/elevated rate limits may
  use a Socrata app token; this provider currently uses anonymous access.

Features:
- Catalog search across CDC datasets
- Dataset metadata retrieval by 4x4 dataset id
- Row-level SoQL queries against individual datasets
- Row-count helper using SoQL aggregate
- Bulk metadata view (`/api/views/metadata/v1`)

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://data.cdc.gov"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Search Datasets
###################


class CDCSearchDatasetsParams(BaseModel):
    """Parameters for searching the CDC Socrata catalog."""

    q: Optional[str] = Field(None, description="Free-text search query")
    limit: int = Field(default=20, description="Number of results per page")
    page: int = Field(default=1, description="Page number (1-indexed)")


def fetch_search_datasets(params: CDCSearchDatasetsParams) -> Any:
    """Search the CDC Socrata catalog."""
    query_params: dict[str, Any] = {"limit": params.limit, "page": params.page}
    if params.q:
        query_params["q"] = params.q

    response = http_get(f"{BASE_URL}/api/views", params=query_params)
    return response.json()


async def handle_search_datasets(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cdc-search-datasets tool call."""
    try:
        params = CDCSearchDatasetsParams(**(arguments or {}))
        data = fetch_search_datasets(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching CDC datasets: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cdc-search-datasets",
        description="Search the CDC Socrata data catalog for datasets.",
        inputSchema=CDCSearchDatasetsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cdc-search-datasets"] = handle_search_datasets


###################
# Get Dataset Metadata
###################


class CDCGetDatasetMetadataParams(BaseModel):
    """Parameters for fetching a CDC dataset's metadata."""

    dataset_id: str = Field(
        ..., description="The 4x4 Socrata dataset id (e.g. '9bhg-hcku')"
    )


def fetch_get_dataset_metadata(params: CDCGetDatasetMetadataParams) -> Any:
    """Fetch metadata for a CDC dataset."""
    response = http_get(f"{BASE_URL}/api/views/{params.dataset_id}")
    return response.json()


async def handle_get_dataset_metadata(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cdc-get-dataset-metadata tool call."""
    try:
        if not arguments or "dataset_id" not in arguments:
            raise ValueError("dataset_id is required")
        params = CDCGetDatasetMetadataParams(**arguments)
        data = fetch_get_dataset_metadata(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching CDC dataset metadata: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cdc-get-dataset-metadata",
        description="Fetch metadata for a specific CDC Socrata dataset by 4x4 id.",
        inputSchema=CDCGetDatasetMetadataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cdc-get-dataset-metadata"] = handle_get_dataset_metadata


###################
# Query Dataset
###################


class CDCQueryDatasetParams(BaseModel):
    """Parameters for SoQL queries against a CDC dataset."""

    dataset_id: str = Field(
        ..., description="The 4x4 Socrata dataset id (e.g. '9bhg-hcku')"
    )
    limit: int = Field(default=100, description="Maximum rows to return ($limit)")
    offset: int = Field(default=0, description="Row offset for pagination ($offset)")
    where: Optional[str] = Field(None, description="SoQL $where filter expression")


def fetch_query_dataset(params: CDCQueryDatasetParams) -> Any:
    """Run a SoQL query against a CDC dataset."""
    query_params: dict[str, Any] = {
        "$limit": params.limit,
        "$offset": params.offset,
    }
    if params.where:
        query_params["$where"] = params.where

    response = http_get(
        f"{BASE_URL}/resource/{params.dataset_id}.json", params=query_params
    )
    return response.json()


async def handle_query_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cdc-query-dataset tool call."""
    try:
        if not arguments or "dataset_id" not in arguments:
            raise ValueError("dataset_id is required")
        params = CDCQueryDatasetParams(**arguments)
        data = fetch_query_dataset(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error querying CDC dataset: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cdc-query-dataset",
        description="Query a CDC dataset using Socrata SoQL ($where/$limit/$offset).",
        inputSchema=CDCQueryDatasetParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cdc-query-dataset"] = handle_query_dataset


###################
# Count Dataset Rows
###################


class CDCCountDatasetRowsParams(BaseModel):
    """Parameters for counting rows in a CDC dataset."""

    dataset_id: str = Field(
        ..., description="The 4x4 Socrata dataset id (e.g. '9bhg-hcku')"
    )


def fetch_count_dataset_rows(params: CDCCountDatasetRowsParams) -> Any:
    """Count the rows in a CDC dataset via SoQL aggregate."""
    query_params = {"$select": "count(*)"}
    response = http_get(
        f"{BASE_URL}/resource/{params.dataset_id}.json", params=query_params
    )
    return response.json()


async def handle_count_dataset_rows(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cdc-count-dataset-rows tool call."""
    try:
        if not arguments or "dataset_id" not in arguments:
            raise ValueError("dataset_id is required")
        params = CDCCountDatasetRowsParams(**arguments)
        data = fetch_count_dataset_rows(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error counting CDC dataset rows: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cdc-count-dataset-rows",
        description="Count the rows in a CDC dataset via SoQL count(*) aggregate.",
        inputSchema=CDCCountDatasetRowsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cdc-count-dataset-rows"] = handle_count_dataset_rows


###################
# Get Metadata V1
###################


class CDCGetMetadataV1Params(BaseModel):
    """Parameters for the v1 metadata catalog view."""

    limit: int = Field(default=20, description="Number of metadata records to return")


def fetch_get_metadata_v1(params: CDCGetMetadataV1Params) -> Any:
    """Fetch CDC catalog metadata via the v1 metadata API."""
    query_params = {"limit": params.limit}
    response = http_get(f"{BASE_URL}/api/views/metadata/v1", params=query_params)
    return response.json()


async def handle_get_metadata_v1(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cdc-get-metadata-v1 tool call."""
    try:
        params = CDCGetMetadataV1Params(**(arguments or {}))
        data = fetch_get_metadata_v1(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching CDC v1 metadata: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cdc-get-metadata-v1",
        description="Fetch CDC catalog metadata via the Socrata v1 metadata view.",
        inputSchema=CDCGetMetadataV1Params.model_json_schema(),
    )
)
TOOLS_HANDLERS["cdc-get-metadata-v1"] = handle_get_metadata_v1


async def main(transport: str = "stdio", port: int = 8000):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "us-cdc-socrata", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
