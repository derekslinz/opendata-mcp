"""
Singapore Government Open Data (data.gov.sg) Provider

This module exposes the public v2 REST API hosted at api-production.data.gov.sg,
the Singapore Government's open data portal. The catalog publishes datasets and
collections owned by Singapore ministries, statutory boards, and partner
agencies.

License note:
    Catalog metadata is made available under the Singapore Open Data Licence.
    Individual datasets may carry their own terms; consult the dataset metadata
    before redistribution. This provider only inspects metadata and download
    status — it does NOT fetch raw payload data.

Features:
- Dataset listing (paged) and per-dataset metadata
- Collection listing (paged) and per-collection metadata
- Asynchronous download status polling (status only — no data fetch)

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.
"""

import logging
from typing import Any, List, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
PROVIDER_ID = "sg-data-gov"
BASE_URL = "https://api-production.data.gov.sg/v2/public/api"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Dataset Listing
###################


class SGDataGovListDatasetsParams(BaseModel):
    """Parameters for paged listing of datasets on data.gov.sg."""

    page: int = Field(
        default=1,
        description="1-indexed page number for pagination.",
    )
    per_page: int = Field(
        default=20,
        description="Number of datasets to return per page.",
    )


def fetch_sg_datagov_list_datasets(params: SGDataGovListDatasetsParams) -> dict:
    """Call /datasets on data.gov.sg v2."""
    query_params: dict[str, Any] = {
        "page": params.page,
        "per_page": params.per_page,
    }
    response = http_get(
        f"{BASE_URL}/datasets", params=query_params, provider=PROVIDER_ID
    )
    return response.json()


async def handle_sg_datagov_list_datasets(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the sg-data-gov-list-datasets tool call."""
    try:
        params = SGDataGovListDatasetsParams(**(arguments or {}))
        data = fetch_sg_datagov_list_datasets(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing data.gov.sg datasets: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="sg-data-gov-list-datasets",
        description="List datasets in the Singapore data.gov.sg catalog (paged).",
        inputSchema=SGDataGovListDatasetsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["sg-data-gov-list-datasets"] = handle_sg_datagov_list_datasets


###################
# Dataset Details
###################


class SGDataGovGetDatasetParams(BaseModel):
    """Parameters for fetching a single dataset's metadata."""

    datasetId: str = Field(
        ...,
        description="The dataset id (path segment in /datasets/{id}/metadata).",
    )


def fetch_sg_datagov_get_dataset(params: SGDataGovGetDatasetParams) -> dict:
    """Call /datasets/{datasetId}/metadata on data.gov.sg v2."""
    response = http_get(
        f"{BASE_URL}/datasets/{params.datasetId}/metadata", provider=PROVIDER_ID
    )
    return response.json()


async def handle_sg_datagov_get_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the sg-data-gov-get-dataset tool call."""
    try:
        if not arguments or "datasetId" not in arguments:
            raise ValueError("datasetId is required")
        params = SGDataGovGetDatasetParams(**arguments)
        data = fetch_sg_datagov_get_dataset(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching data.gov.sg dataset metadata: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="sg-data-gov-get-dataset",
        description="Fetch metadata for a single data.gov.sg dataset by id.",
        inputSchema=SGDataGovGetDatasetParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["sg-data-gov-get-dataset"] = handle_sg_datagov_get_dataset


###################
# Collections Listing
###################


class SGDataGovListCollectionsParams(BaseModel):
    """Parameters for paged listing of collections on data.gov.sg."""

    page: int = Field(
        default=1,
        description="1-indexed page number for pagination.",
    )


def fetch_sg_datagov_list_collections(params: SGDataGovListCollectionsParams) -> dict:
    """Call /collections on data.gov.sg v2."""
    query_params: dict[str, Any] = {"page": params.page}
    response = http_get(
        f"{BASE_URL}/collections", params=query_params, provider=PROVIDER_ID
    )
    return response.json()


async def handle_sg_datagov_list_collections(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the sg-data-gov-list-collections tool call."""
    try:
        params = SGDataGovListCollectionsParams(**(arguments or {}))
        data = fetch_sg_datagov_list_collections(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing data.gov.sg collections: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="sg-data-gov-list-collections",
        description="List collections in the Singapore data.gov.sg catalog (paged).",
        inputSchema=SGDataGovListCollectionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["sg-data-gov-list-collections"] = handle_sg_datagov_list_collections


###################
# Collection Details
###################


class SGDataGovGetCollectionParams(BaseModel):
    """Parameters for fetching a single collection's metadata."""

    collectionId: str = Field(
        ...,
        description="The collection id (path segment in /collections/{id}/metadata).",
    )


def fetch_sg_datagov_get_collection(params: SGDataGovGetCollectionParams) -> dict:
    """Call /collections/{collectionId}/metadata on data.gov.sg v2."""
    response = http_get(
        f"{BASE_URL}/collections/{params.collectionId}/metadata", provider=PROVIDER_ID
    )
    return response.json()


async def handle_sg_datagov_get_collection(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the sg-data-gov-get-collection tool call."""
    try:
        if not arguments or "collectionId" not in arguments:
            raise ValueError("collectionId is required")
        params = SGDataGovGetCollectionParams(**arguments)
        data = fetch_sg_datagov_get_collection(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching data.gov.sg collection metadata: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="sg-data-gov-get-collection",
        description="Fetch metadata for a single data.gov.sg collection by id.",
        inputSchema=SGDataGovGetCollectionParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["sg-data-gov-get-collection"] = handle_sg_datagov_get_collection


###################
# Poll Download Status
###################


class SGDataGovPollDownloadParams(BaseModel):
    """Parameters for polling the async download-prep status for a dataset.

    Important: this endpoint only reports preparation status (e.g. PENDING,
    READY, FAILED) and returns a signed URL handle for the caller. This
    provider intentionally does NOT follow the URL or fetch payload bytes.
    """

    datasetId: str = Field(
        ...,
        description="The dataset id whose download-prep status should be polled.",
    )


def fetch_sg_datagov_poll_download(params: SGDataGovPollDownloadParams) -> dict:
    """Call /datasets/{datasetId}/poll-download on data.gov.sg v2."""
    response = http_get(
        f"{BASE_URL}/datasets/{params.datasetId}/poll-download", provider=PROVIDER_ID
    )
    return response.json()


async def handle_sg_datagov_poll_download(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the sg-data-gov-poll-download tool call."""
    try:
        if not arguments or "datasetId" not in arguments:
            raise ValueError("datasetId is required")
        params = SGDataGovPollDownloadParams(**arguments)
        data = fetch_sg_datagov_poll_download(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error polling data.gov.sg download status: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="sg-data-gov-poll-download",
        description=(
            "Poll the async download-preparation status for a data.gov.sg "
            "dataset (status only; does NOT download payload data)."
        ),
        inputSchema=SGDataGovPollDownloadParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["sg-data-gov-poll-download"] = handle_sg_datagov_poll_download


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "sg-data-gov", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
