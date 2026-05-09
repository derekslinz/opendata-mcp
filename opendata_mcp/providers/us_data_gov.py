"""
US Data.gov Catalog API Client

This module provides interfaces to access the US Federal Government's open data catalog
via the current catalog.data.gov API.

Features:
- Dataset discovery through the catalog search endpoint
- Detailed dataset metadata retrieval from exact search matches

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import to_json_text

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://catalog.data.gov"
SEARCH_URL = f"{BASE_URL}/search"

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
        description="Search term for dataset titles or descriptions",
    )
    rows: int = Field(default=20, description="Number of results to return")
    after: Optional[str] = Field(
        None,
        description="Pagination cursor returned by a previous Data.gov search",
    )
    org_slug: Optional[str] = Field(
        None,
        description="Optional organization slug filter, e.g. 'nasa'",
    )


def list_datagov_datasets(params: DataGovListDatasetsParams) -> dict:
    """Search for available US Data.gov datasets using the catalog API."""
    query_params = {
        "q": params.search or "",
        "per_page": params.rows,
    }
    if params.after:
        query_params["after"] = params.after
    if params.org_slug:
        query_params["org_slug"] = params.org_slug

    response = httpx.get(SEARCH_URL, params=query_params, timeout=10.0)
    response.raise_for_status()
    return response.json()


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
                    "identifier": pkg.get("identifier"),
                    "slug": pkg.get("slug"),
                    "title": pkg.get("title"),
                    "publisher": pkg.get("publisher"),
                    "organization": pkg.get("organization", {}).get("name"),
                    "description": pkg.get("description", "")[:200] + "..."
                    if pkg.get("description") and len(pkg.get("description")) > 200
                    else pkg.get("description"),
                    "harvest_record": pkg.get("harvest_record"),
                }
            )

        output = {
            "count": len(simplified_results),
            "after": result.get("after"),
            "datasets": simplified_results,
        }

        return [types.TextContent(type="text", text=to_json_text(output, max_chars=20000))]
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
        description="The slug, identifier, or title of the dataset",
    )


def _normalize_dataset_key(value: str | None) -> str:
    return (value or "").strip().casefold()


def fetch_datagov_dataset(params: DataGovGetDatasetParams) -> dict:
    """Fetch full metadata for a specific US Data.gov dataset using catalog search."""
    dataset_id = params.dataset_id.strip()
    query_params = {"q": dataset_id, "per_page": 25}

    response = httpx.get(SEARCH_URL, params=query_params, timeout=10.0)
    response.raise_for_status()
    data = response.json()

    target = _normalize_dataset_key(dataset_id)
    results = data.get("results", [])
    for result in results:
        candidates = [
            result.get("slug"),
            result.get("identifier"),
            result.get("title"),
            result.get("dcat", {}).get("identifier"),
            result.get("dcat", {}).get("title"),
        ]
        if any(_normalize_dataset_key(candidate) == target for candidate in candidates):
            return result

    if results:
        return results[0]

    raise ValueError(f"API Error: dataset not found: {dataset_id}")


async def handle_datagov_get_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the us-datagov-get-dataset tool call."""
    try:
        if not arguments or "dataset_id" not in arguments:
            raise ValueError("dataset_id is required")

        params = DataGovGetDatasetParams(**arguments)
        result = fetch_datagov_dataset(params)
        return [types.TextContent(type="text", text=to_json_text(result))]
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

    from opendata_mcp.utils import create_mcp_server

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
