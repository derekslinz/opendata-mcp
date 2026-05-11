"""
France Open Data Portal (data.gouv.fr) Provider

This module exposes the public uData REST API hosted at www.data.gouv.fr, the
French Government's open data portal. The catalog aggregates datasets, reuses,
organisations, and thematic topics published by central and local government,
public agencies, and partner institutions.

License note:
    Catalog metadata is typically published under the Licence Ouverte / Open
    Licence v2.0 (compatible with CC-BY 2.0). Individual datasets carry their
    own licences; consult the license fields before redistribution.

Features:
- Dataset search and listing (uData /datasets/)
- Dataset metadata retrieval (/datasets/{id_or_slug}/)
- Organisation discovery and detail (/organizations/)
- Reuse discovery (/reuses/) — community-built apps using the data
- Topic catalog (/topics/)
- Tag suggestions (/tags/suggest/)

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.

Note:
    Unlike CKAN portals, data.gouv.fr uses uData REST conventions: pagination
    uses `page` + `page_size`, and single-resource lookups are RESTful path
    segments (`/datasets/{slug}/`) rather than CKAN's `package_show?id=`.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.data.gouv.fr/api/1"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Dataset Search
###################


class FRDataGouvSearchDatasetsParams(BaseModel):
    """Parameters for searching datasets on data.gouv.fr."""

    q: Optional[str] = Field(
        None,
        description="Free-text search query. Leave blank to list all datasets.",
    )
    page: int = Field(
        default=1,
        description="1-indexed page number for pagination.",
    )
    page_size: int = Field(
        default=20,
        description="Number of datasets to return per page.",
    )


def fetch_fr_datagouv_search_datasets(params: FRDataGouvSearchDatasetsParams) -> dict:
    """Call /datasets/ on data.gouv.fr."""
    query_params: dict[str, Any] = {
        "page": params.page,
        "page_size": params.page_size,
    }
    if params.q:
        query_params["q"] = params.q
    response = http_get(f"{BASE_URL}/datasets/", params=query_params)
    return response.json()


async def handle_fr_datagouv_search_datasets(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fr-data-gouv-search-datasets tool call."""
    try:
        params = FRDataGouvSearchDatasetsParams(**(arguments or {}))
        data = fetch_fr_datagouv_search_datasets(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching data.gouv.fr datasets: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fr-data-gouv-search-datasets",
        description="Search the France data.gouv.fr catalog (uData /datasets/).",
        inputSchema=FRDataGouvSearchDatasetsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fr-data-gouv-search-datasets"] = handle_fr_datagouv_search_datasets


###################
# Dataset Details
###################


class FRDataGouvGetDatasetParams(BaseModel):
    """Parameters for fetching a single dataset's full metadata."""

    id: str = Field(
        ...,
        description="The dataset slug or id (used as a RESTful path segment).",
    )


def fetch_fr_datagouv_get_dataset(params: FRDataGouvGetDatasetParams) -> dict:
    """Call /datasets/{id}/ on data.gouv.fr."""
    response = http_get(f"{BASE_URL}/datasets/{params.id}/")
    return response.json()


async def handle_fr_datagouv_get_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fr-data-gouv-get-dataset tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = FRDataGouvGetDatasetParams(**arguments)
        data = fetch_fr_datagouv_get_dataset(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching data.gouv.fr dataset: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fr-data-gouv-get-dataset",
        description="Fetch full metadata for a data.gouv.fr dataset by slug or id.",
        inputSchema=FRDataGouvGetDatasetParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fr-data-gouv-get-dataset"] = handle_fr_datagouv_get_dataset


###################
# Organizations List
###################


class FRDataGouvListOrganizationsParams(BaseModel):
    """Parameters for listing publishing organisations."""

    page: int = Field(default=1, description="1-indexed page number.")
    page_size: int = Field(
        default=20, description="Number of organisations to return per page."
    )


def fetch_fr_datagouv_list_organizations(
    params: FRDataGouvListOrganizationsParams,
) -> dict:
    """Call /organizations/ on data.gouv.fr."""
    query_params: dict[str, Any] = {
        "page": params.page,
        "page_size": params.page_size,
    }
    response = http_get(f"{BASE_URL}/organizations/", params=query_params)
    return response.json()


async def handle_fr_datagouv_list_organizations(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fr-data-gouv-list-organizations tool call."""
    try:
        params = FRDataGouvListOrganizationsParams(**(arguments or {}))
        data = fetch_fr_datagouv_list_organizations(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing data.gouv.fr organisations: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fr-data-gouv-list-organizations",
        description="List publishing organisations on data.gouv.fr.",
        inputSchema=FRDataGouvListOrganizationsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fr-data-gouv-list-organizations"] = (
    handle_fr_datagouv_list_organizations
)


###################
# Organization Details
###################


class FRDataGouvGetOrganizationParams(BaseModel):
    """Parameters for fetching a single organisation's full record."""

    id: str = Field(
        ...,
        description="The organisation slug or id (used as a RESTful path segment).",
    )


def fetch_fr_datagouv_get_organization(
    params: FRDataGouvGetOrganizationParams,
) -> dict:
    """Call /organizations/{slug}/ on data.gouv.fr."""
    response = http_get(f"{BASE_URL}/organizations/{params.id}/")
    return response.json()


async def handle_fr_datagouv_get_organization(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fr-data-gouv-get-organization tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = FRDataGouvGetOrganizationParams(**arguments)
        data = fetch_fr_datagouv_get_organization(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching data.gouv.fr organisation: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fr-data-gouv-get-organization",
        description="Fetch full details for a data.gouv.fr publishing organisation.",
        inputSchema=FRDataGouvGetOrganizationParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fr-data-gouv-get-organization"] = handle_fr_datagouv_get_organization


###################
# Reuses Search
###################


class FRDataGouvSearchReusesParams(BaseModel):
    """Parameters for searching reuses (apps/sites built on the data)."""

    q: Optional[str] = Field(
        None,
        description="Free-text search query for reuse titles/descriptions.",
    )
    page_size: int = Field(
        default=20, description="Number of reuses to return per page."
    )


def fetch_fr_datagouv_search_reuses(params: FRDataGouvSearchReusesParams) -> dict:
    """Call /reuses/ on data.gouv.fr."""
    query_params: dict[str, Any] = {"page_size": params.page_size}
    if params.q:
        query_params["q"] = params.q
    response = http_get(f"{BASE_URL}/reuses/", params=query_params)
    return response.json()


async def handle_fr_datagouv_search_reuses(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fr-data-gouv-search-reuses tool call."""
    try:
        params = FRDataGouvSearchReusesParams(**(arguments or {}))
        data = fetch_fr_datagouv_search_reuses(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching data.gouv.fr reuses: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fr-data-gouv-search-reuses",
        description="Search community-built reuses on data.gouv.fr.",
        inputSchema=FRDataGouvSearchReusesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fr-data-gouv-search-reuses"] = handle_fr_datagouv_search_reuses


###################
# Topics
###################


class FRDataGouvListTopicsParams(BaseModel):
    """Parameters for listing thematic topics."""

    page_size: int = Field(
        default=20, description="Number of topics to return per page."
    )


def fetch_fr_datagouv_list_topics(params: FRDataGouvListTopicsParams) -> dict:
    """Call /topics/ on data.gouv.fr."""
    query_params: dict[str, Any] = {"page_size": params.page_size}
    response = http_get(f"{BASE_URL}/topics/", params=query_params)
    return response.json()


async def handle_fr_datagouv_list_topics(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fr-data-gouv-list-topics tool call."""
    try:
        params = FRDataGouvListTopicsParams(**(arguments or {}))
        data = fetch_fr_datagouv_list_topics(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing data.gouv.fr topics: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fr-data-gouv-list-topics",
        description="List thematic topics defined on data.gouv.fr.",
        inputSchema=FRDataGouvListTopicsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fr-data-gouv-list-topics"] = handle_fr_datagouv_list_topics


###################
# Tag Suggestions
###################


class FRDataGouvListTagsParams(BaseModel):
    """Parameters for tag-name autosuggestion."""

    q: Optional[str] = Field(
        None,
        description="Substring to suggest tags for (uData /tags/suggest/?q=).",
    )


def fetch_fr_datagouv_list_tags(params: FRDataGouvListTagsParams) -> dict | list:
    """Call /tags/suggest/ on data.gouv.fr."""
    query_params: dict[str, Any] = {}
    if params.q:
        query_params["q"] = params.q
    response = http_get(f"{BASE_URL}/tags/suggest/", params=query_params)
    return response.json()


async def handle_fr_datagouv_list_tags(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the fr-data-gouv-list-tags tool call."""
    try:
        params = FRDataGouvListTagsParams(**(arguments or {}))
        data = fetch_fr_datagouv_list_tags(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error suggesting data.gouv.fr tags: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="fr-data-gouv-list-tags",
        description="Autosuggest tag names on data.gouv.fr.",
        inputSchema=FRDataGouvListTagsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["fr-data-gouv-list-tags"] = handle_fr_datagouv_list_tags


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "fr-data-gouv", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
