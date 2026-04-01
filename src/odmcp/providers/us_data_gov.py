"""
US Data.gov (CKAN) API Client

This module provides interfaces to access the US Federal Government's open data catalog
via its CKAN-based API (catalog.data.gov).

Features:
- Dataset discovery through CKAN package_search
- Detailed dataset metadata retrieval through CKAN package_show

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
BASE_URL = "https://catalog.data.gov/api/3/action"
SEARCH_URL = f"{BASE_URL}/package_search"
SHOW_URL = f"{BASE_URL}/package_show"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# Data.gov Dataset Discovery
###################


class DataGovListDatasetsParams(BaseModel):
    """Parameters for searching or listing US Data.gov datasets."""

    search: Optional[str] = Field(
        None,
        description="Search term for dataset titles or descriptions (CKAN 'q' param)",
    )
    rows: int = Field(default=20, description="Number of results to return (max 1000)")
    start: int = Field(default=0, description="Offset for pagination")


def list_datagov_datasets(params: DataGovListDatasetsParams) -> dict:
    """Search for available US Data.gov datasets using CKAN package_search."""
    query_params = {
        "q": params.search if params.search else "*:*",
        "rows": params.rows,
        "start": params.start,
    }

    response = httpx.get(SEARCH_URL, params=query_params)
    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        raise ValueError(f"API Error: {data.get('error', 'Unknown Error')}")

    return data["result"]


async def handle_datagov_list_datasets(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the us-datagov-list-datasets tool call."""
    try:
        params = DataGovListDatasetsParams(**(arguments or {}))
        result = list_datagov_datasets(params)

        # We simplify the output to just key fields to keep it readable
        simplified_results = []
        for pkg in result.get("results", []):
            simplified_results.append(
                {
                    "id": pkg.get("id"),
                    "name": pkg.get("name"),
                    "title": pkg.get("title"),
                    "organization": pkg.get("organization", {}).get("title"),
                    "notes": pkg.get("notes", "")[:200] + "..."
                    if pkg.get("notes") and len(pkg.get("notes")) > 200
                    else pkg.get("notes"),
                }
            )

        output = {"count": result.get("count"), "datasets": simplified_results}

        return [types.TextContent(type="text", text=str(output)[:20000])]
    except Exception as e:
        log.error(f"Error listing Data.gov datasets: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="us-datagov-list-datasets",
        description="Search for datasets in the US Data.gov catalog.",
        inputSchema=DataGovListDatasetsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["us-datagov-list-datasets"] = handle_datagov_list_datasets

###################
# Data.gov Dataset Details
###################


class DataGovGetDatasetParams(BaseModel):
    """Parameters for fetching full metadata for a US Data.gov dataset."""

    dataset_id: str = Field(
        ...,
        description="The ID or name of the dataset (e.g., 'consumer-complaint-database')",
    )


def fetch_datagov_dataset(params: DataGovGetDatasetParams) -> dict:
    """Fetch full metadata for a specific US Data.gov dataset using CKAN package_show."""
    query_params = {"id": params.dataset_id}

    response = httpx.get(SHOW_URL, params=query_params)
    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        raise ValueError(f"API Error: {data.get('error', 'Unknown Error')}")

    return data["result"]


async def handle_datagov_get_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the us-datagov-get-dataset tool call."""
    try:
        if not arguments or "dataset_id" not in arguments:
            raise ValueError("dataset_id is required")

        params = DataGovGetDatasetParams(**arguments)
        result = fetch_datagov_dataset(params)
        return [types.TextContent(type="text", text=str(result))]
    except Exception as e:
        log.error(f"Error fetching Data.gov dataset: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="us-datagov-get-dataset",
        description="Fetch detailed metadata for a specific US Data.gov dataset.",
        inputSchema=DataGovGetDatasetParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["us-datagov-get-dataset"] = handle_datagov_get_dataset


async def main():
    from mcp.server.stdio import stdio_server

    from odmcp.utils import create_mcp_server

    # create the server
    server = create_mcp_server(
        "us-data-gov", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    # run the server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


# Server initialization
if __name__ == "__main__":
    import anyio

    anyio.run(main)
