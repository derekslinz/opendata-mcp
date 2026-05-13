"""
CERN Open Data Portal Provider

This module provides interfaces to the CERN Open Data Portal API, which
publishes particle physics datasets, software, and documentation from LHC
experiments (CMS, ATLAS, LHCb, ALICE, OPERA).

License: Datasets are published under CC0 1.0 and software under various
open-source licenses. See https://opendata.cern.ch/about/terms-of-use for
full terms.

Environment variables:
- None required. All endpoints are public.

Features:
- Record search with full-text query, sort, and pagination
- Full record metadata retrieval by record id
- Dataset collection listing
- Experiment-scoped search (CMS, ATLAS, LHCb, ALICE)
- Software record search

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://opendata.cern.ch/api"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Search Records
###################


class CERNSearchRecordsParams(BaseModel):
    """Parameters for searching CERN Open Data records."""

    q: Optional[str] = Field(None, description="Full-text search query string")
    size: int = Field(default=20, description="Number of results per page")
    page: int = Field(default=1, description="Page number (1-indexed)")


def fetch_search_records(params: CERNSearchRecordsParams) -> dict:
    """Search the CERN Open Data record index."""
    query_params: dict[str, Any] = {
        "size": params.size,
        "page": params.page,
        "sort": "mostrecent",
    }
    if params.q:
        query_params["q"] = params.q

    response = http_get(f"{BASE_URL}/records/", params=query_params)
    return response.json()


async def handle_search_records(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cern-search-records tool call."""
    try:
        params = CERNSearchRecordsParams(**(arguments or {}))
        data = fetch_search_records(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching CERN Open Data records: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cern-search-records",
        description="Search the CERN Open Data Portal for datasets, software, and documentation.",
        inputSchema=CERNSearchRecordsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cern-search-records"] = handle_search_records


###################
# Get Record
###################


class CERNGetRecordParams(BaseModel):
    """Parameters for fetching a single CERN Open Data record."""

    record_id: int = Field(..., description="The CERN Open Data numeric record id")


def fetch_get_record(params: CERNGetRecordParams) -> dict:
    """Fetch full metadata for a CERN Open Data record."""
    response = http_get(f"{BASE_URL}/records/{params.record_id}")
    return response.json()


async def handle_get_record(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cern-get-record tool call."""
    try:
        if not arguments or "record_id" not in arguments:
            raise ValueError("record_id is required")
        params = CERNGetRecordParams(**arguments)
        data = fetch_get_record(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching CERN Open Data record: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cern-get-record",
        description="Fetch full metadata for a specific CERN Open Data record by record_id.",
        inputSchema=CERNGetRecordParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cern-get-record"] = handle_get_record


###################
# List Collections (Datasets)
###################


class CERNListCollectionsParams(BaseModel):
    """Parameters for listing CERN Open Data dataset collections."""

    size: int = Field(default=50, description="Number of dataset records to return")


def fetch_list_collections(params: CERNListCollectionsParams) -> dict:
    """List CERN Open Data Dataset records."""
    query_params = {"type": "Dataset", "size": params.size}
    response = http_get(f"{BASE_URL}/records/", params=query_params)
    return response.json()


async def handle_list_collections(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cern-list-collections tool call."""
    try:
        params = CERNListCollectionsParams(**(arguments or {}))
        data = fetch_list_collections(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing CERN Open Data collections: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cern-list-collections",
        description="List CERN Open Data dataset collections.",
        inputSchema=CERNListCollectionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cern-list-collections"] = handle_list_collections


###################
# Search By Experiment
###################


class CERNSearchByExperimentParams(BaseModel):
    """Parameters for searching CERN Open Data within a single experiment."""

    experiment: str = Field(
        ..., description="Experiment name (e.g. 'CMS', 'ATLAS', 'LHCb', 'ALICE')"
    )
    q: Optional[str] = Field(None, description="Optional full-text search query")
    size: int = Field(default=20, description="Number of results to return")


def fetch_search_by_experiment(params: CERNSearchByExperimentParams) -> dict:
    """Search CERN Open Data records filtered by experiment."""
    query_params: dict[str, Any] = {
        "experiment": params.experiment,
        "size": params.size,
    }
    if params.q:
        query_params["q"] = params.q

    response = http_get(f"{BASE_URL}/records/", params=query_params)
    return response.json()


async def handle_search_by_experiment(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cern-search-by-experiment tool call."""
    try:
        if not arguments or "experiment" not in arguments:
            raise ValueError("experiment is required")
        params = CERNSearchByExperimentParams(**arguments)
        data = fetch_search_by_experiment(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching CERN Open Data by experiment: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cern-search-by-experiment",
        description="Search CERN Open Data records scoped to a specific experiment (CMS, ATLAS, LHCb, ALICE).",
        inputSchema=CERNSearchByExperimentParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cern-search-by-experiment"] = handle_search_by_experiment


###################
# Search Software
###################


class CERNSearchSoftwareParams(BaseModel):
    """Parameters for searching CERN Open Data software releases."""

    q: Optional[str] = Field(None, description="Optional full-text search query")
    size: int = Field(default=20, description="Number of results to return")


def fetch_search_software(params: CERNSearchSoftwareParams) -> dict:
    """Search CERN Open Data Software-typed records."""
    query_params: dict[str, Any] = {"type": "Software", "size": params.size}
    if params.q:
        query_params["q"] = params.q

    response = http_get(f"{BASE_URL}/records/", params=query_params)
    return response.json()


async def handle_search_software(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the cern-search-software tool call."""
    try:
        params = CERNSearchSoftwareParams(**(arguments or {}))
        data = fetch_search_software(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching CERN Open Data software: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="cern-search-software",
        description="Search CERN Open Data software releases (analysis frameworks, VMs).",
        inputSchema=CERNSearchSoftwareParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["cern-search-software"] = handle_search_software


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "cern-opendata", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
