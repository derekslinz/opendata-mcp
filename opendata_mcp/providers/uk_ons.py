"""
UK Office for National Statistics (ONS) Provider

This module provides interfaces to the UK Office for National Statistics
beta open API, exposing the catalogue of published datasets, their editions,
versions and observations along with code-list metadata.

License: ONS open data is published under the Open Government Licence v3.0
(https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

Features:
- Dataset, edition, and version discovery
- Observation retrieval with time/geography filters
- Code-list catalogues
- No API key required

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.beta.ons.gov.uk/v1"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# List Datasets
###################


class ONSListDatasetsParams(BaseModel):
    """Parameters for listing ONS datasets."""

    limit: int = Field(default=20, description="Maximum number of datasets to return")
    offset: int = Field(default=0, description="Pagination offset")


def fetch_list_datasets(params: ONSListDatasetsParams) -> dict:
    """Fetch the list of ONS datasets."""
    query_params = {"limit": params.limit, "offset": params.offset}
    response = http_get(f"{BASE_URL}/datasets", params=query_params, timeout=30.0)
    return response.json()


async def handle_list_datasets(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-ons-list-datasets tool call."""
    try:
        params = ONSListDatasetsParams(**(arguments or {}))
        data = fetch_list_datasets(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error listing ONS datasets: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-ons-list-datasets",
        description="List datasets published on the ONS open data API.",
        inputSchema=ONSListDatasetsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-ons-list-datasets"] = handle_list_datasets


###################
# Get Dataset
###################


class ONSGetDatasetParams(BaseModel):
    """Parameters for fetching a single ONS dataset."""

    id: str = Field(..., description="ONS dataset identifier (e.g. 'cpih01')")


def fetch_get_dataset(params: ONSGetDatasetParams) -> dict:
    """Fetch a single ONS dataset by ID."""
    response = http_get(f"{BASE_URL}/datasets/{params.id}", timeout=30.0)
    return response.json()


async def handle_get_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-ons-get-dataset tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = ONSGetDatasetParams(**arguments)
        data = fetch_get_dataset(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ONS dataset: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-ons-get-dataset",
        description="Get metadata for a single ONS dataset by ID.",
        inputSchema=ONSGetDatasetParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-ons-get-dataset"] = handle_get_dataset


###################
# List Editions
###################


class ONSListEditionsParams(BaseModel):
    """Parameters for listing the editions of an ONS dataset."""

    id: str = Field(..., description="ONS dataset identifier")


def fetch_list_editions(params: ONSListEditionsParams) -> dict:
    """Fetch the list of editions for an ONS dataset."""
    response = http_get(f"{BASE_URL}/datasets/{params.id}/editions", timeout=30.0)
    return response.json()


async def handle_list_editions(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-ons-list-editions tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = ONSListEditionsParams(**arguments)
        data = fetch_list_editions(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error listing ONS editions: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-ons-list-editions",
        description="List the editions of a given ONS dataset.",
        inputSchema=ONSListEditionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-ons-list-editions"] = handle_list_editions


###################
# Get Edition
###################


class ONSGetEditionParams(BaseModel):
    """Parameters for fetching a single ONS edition."""

    id: str = Field(..., description="ONS dataset identifier")
    edition: str = Field(..., description="Edition identifier (e.g. 'time-series')")


def fetch_get_edition(params: ONSGetEditionParams) -> dict:
    """Fetch a single ONS edition for a dataset."""
    response = http_get(
        f"{BASE_URL}/datasets/{params.id}/editions/{params.edition}", timeout=30.0
    )
    return response.json()


async def handle_get_edition(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-ons-get-edition tool call."""
    try:
        if not arguments or "id" not in arguments or "edition" not in arguments:
            raise ValueError("id and edition are required")
        params = ONSGetEditionParams(**arguments)
        data = fetch_get_edition(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ONS edition: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-ons-get-edition",
        description="Get metadata for a single edition of an ONS dataset.",
        inputSchema=ONSGetEditionParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-ons-get-edition"] = handle_get_edition


###################
# List Versions
###################


class ONSListVersionsParams(BaseModel):
    """Parameters for listing the versions of an ONS edition."""

    id: str = Field(..., description="ONS dataset identifier")
    edition: str = Field(..., description="Edition identifier")


def fetch_list_versions(params: ONSListVersionsParams) -> dict:
    """Fetch the list of versions for an ONS edition."""
    response = http_get(
        f"{BASE_URL}/datasets/{params.id}/editions/{params.edition}/versions",
        timeout=30.0,
    )
    return response.json()


async def handle_list_versions(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-ons-list-versions tool call."""
    try:
        if not arguments or "id" not in arguments or "edition" not in arguments:
            raise ValueError("id and edition are required")
        params = ONSListVersionsParams(**arguments)
        data = fetch_list_versions(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error listing ONS versions: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-ons-list-versions",
        description="List all versions of a given ONS edition.",
        inputSchema=ONSListVersionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-ons-list-versions"] = handle_list_versions


###################
# Get Observations
###################


class ONSGetObservationsParams(BaseModel):
    """Parameters for fetching observations from an ONS version."""

    id: str = Field(..., description="ONS dataset identifier")
    edition: str = Field(..., description="Edition identifier")
    version: str = Field(..., description="Version identifier (e.g. '1')")
    time: Optional[str] = Field(
        None, description="Time dimension filter (e.g. '2023', 'Jan-23', or '*')"
    )
    geography: Optional[str] = Field(
        None, description="Geography dimension filter (e.g. 'K02000001' or '*')"
    )


def fetch_get_observations(params: ONSGetObservationsParams) -> dict:
    """Fetch observations from a specific ONS dataset version."""
    query_params: dict[str, Any] = {}
    if params.time is not None:
        query_params["time"] = params.time
    if params.geography is not None:
        query_params["geography"] = params.geography

    url = (
        f"{BASE_URL}/datasets/{params.id}/editions/{params.edition}"
        f"/versions/{params.version}/observations"
    )
    response = http_get(url, params=query_params, timeout=30.0)
    return response.json()


async def handle_get_observations(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-ons-get-observations tool call."""
    try:
        if (
            not arguments
            or "id" not in arguments
            or "edition" not in arguments
            or "version" not in arguments
        ):
            raise ValueError("id, edition, and version are required")
        params = ONSGetObservationsParams(**arguments)
        data = fetch_get_observations(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ONS observations: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-ons-get-observations",
        description="Fetch observations from a specific ONS dataset version, filterable by time and geography.",
        inputSchema=ONSGetObservationsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-ons-get-observations"] = handle_get_observations


###################
# List Code Lists
###################


class ONSListCodeListsParams(BaseModel):
    """Parameters for listing ONS code-lists."""

    limit: int = Field(default=20, description="Maximum number of code-lists to return")
    offset: int = Field(default=0, description="Pagination offset")


def fetch_list_codelists(params: ONSListCodeListsParams) -> dict:
    """Fetch the list of ONS code-lists."""
    query_params = {"limit": params.limit, "offset": params.offset}
    response = http_get(f"{BASE_URL}/code-lists", params=query_params, timeout=30.0)
    return response.json()


async def handle_list_codelists(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-ons-list-codelists tool call."""
    try:
        params = ONSListCodeListsParams(**(arguments or {}))
        data = fetch_list_codelists(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error listing ONS code-lists: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-ons-list-codelists",
        description="List code-lists published on the ONS open data API.",
        inputSchema=ONSListCodeListsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-ons-list-codelists"] = handle_list_codelists


###################
# Get Code List
###################


class ONSGetCodeListParams(BaseModel):
    """Parameters for fetching a single ONS code-list."""

    id: str = Field(..., description="ONS code-list identifier")


def fetch_get_codelist(params: ONSGetCodeListParams) -> dict:
    """Fetch a single ONS code-list by ID."""
    response = http_get(f"{BASE_URL}/code-lists/{params.id}", timeout=30.0)
    return response.json()


async def handle_get_codelist(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-ons-get-codelist tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = ONSGetCodeListParams(**arguments)
        data = fetch_get_codelist(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ONS code-list: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-ons-get-codelist",
        description="Get metadata for a single ONS code-list by ID.",
        inputSchema=ONSGetCodeListParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-ons-get-codelist"] = handle_get_codelist


async def main():
    from mcp.server.stdio import stdio_server

    from opendata_mcp.utils import create_mcp_server

    server = create_mcp_server(
        "uk-ons", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
