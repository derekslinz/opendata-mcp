"""
UK Government Open Data Catalog (data.gov.uk) Provider

This module exposes the public CKAN v3 API hosted at data.gov.uk, the UK
Government's open data portal. The catalog aggregates datasets published by
central government, devolved administrations, local authorities, and other
public-sector organisations.

License note:
    Catalog metadata is made available under the UK Open Government Licence
    (OGL v3.0). Individual datasets may carry their own licences; consult the
    license fields returned by the API before redistributing payload data.

Features:
- Dataset search via CKAN package_search
- Dataset metadata retrieval via package_show
- Organisation discovery and detail (organization_list / organization_show)
- Group (theme) discovery (group_list)
- Tag suggestions (tag_list)
- Recently changed packages feed for monitoring catalog churn

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
PROVIDER_ID = "uk-gov"
BASE_URL = "https://data.gov.uk/api/3/action"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Dataset Search
###################


class UKGovSearchDatasetsParams(BaseModel):
    """Parameters for searching datasets in the data.gov.uk CKAN catalog."""

    q: Optional[str] = Field(
        None,
        description="Free-text search query (CKAN 'q' parameter). Leave blank to list all.",
    )
    rows: int = Field(
        default=20,
        description="Maximum number of datasets to return per page (CKAN 'rows').",
    )
    start: int = Field(
        default=0,
        description="Offset into the result set for pagination (CKAN 'start').",
    )


def fetch_uk_gov_search_datasets(params: UKGovSearchDatasetsParams) -> dict:
    """Call CKAN package_search on data.gov.uk."""
    query_params: dict[str, Any] = {
        "q": params.q or "",
        "rows": params.rows,
        "start": params.start,
    }
    response = http_get(
        f"{BASE_URL}/package_search", params=query_params, provider=PROVIDER_ID
    )
    return response.json()


async def handle_uk_gov_search_datasets(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-gov-search-datasets tool call."""
    try:
        params = UKGovSearchDatasetsParams(**(arguments or {}))
        data = fetch_uk_gov_search_datasets(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching data.gov.uk datasets: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-gov-search-datasets",
        description="Search the UK Government data.gov.uk catalog (CKAN package_search).",
        inputSchema=UKGovSearchDatasetsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-gov-search-datasets"] = handle_uk_gov_search_datasets


###################
# Dataset Details
###################


class UKGovGetDatasetParams(BaseModel):
    """Parameters for fetching a single dataset's metadata."""

    id: str = Field(..., description="The CKAN dataset id or slug (name) to retrieve.")


def fetch_uk_gov_get_dataset(params: UKGovGetDatasetParams) -> dict:
    """Call CKAN package_show on data.gov.uk."""
    response = http_get(
        f"{BASE_URL}/package_show", params={"id": params.id}, provider=PROVIDER_ID
    )
    return response.json()


async def handle_uk_gov_get_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-gov-get-dataset tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = UKGovGetDatasetParams(**arguments)
        data = fetch_uk_gov_get_dataset(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching data.gov.uk dataset: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-gov-get-dataset",
        description="Fetch full metadata for a single data.gov.uk dataset by id or slug.",
        inputSchema=UKGovGetDatasetParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-gov-get-dataset"] = handle_uk_gov_get_dataset


###################
# Organizations List
###################


class UKGovListOrganizationsParams(BaseModel):
    """Parameters for listing publishing organisations."""

    limit: int = Field(
        default=50,
        description="Maximum number of organisations to return.",
    )


def fetch_uk_gov_list_organizations(params: UKGovListOrganizationsParams) -> dict:
    """Call CKAN organization_list on data.gov.uk."""
    query_params: dict[str, Any] = {
        "all_fields": "true",
        "limit": params.limit,
    }
    response = http_get(
        f"{BASE_URL}/organization_list", params=query_params, provider=PROVIDER_ID
    )
    return response.json()


async def handle_uk_gov_list_organizations(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-gov-list-organizations tool call."""
    try:
        params = UKGovListOrganizationsParams(**(arguments or {}))
        data = fetch_uk_gov_list_organizations(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing data.gov.uk organisations: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-gov-list-organizations",
        description="List publishing organisations on data.gov.uk with full fields.",
        inputSchema=UKGovListOrganizationsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-gov-list-organizations"] = handle_uk_gov_list_organizations


###################
# Organization Details
###################


class UKGovGetOrganizationParams(BaseModel):
    """Parameters for retrieving a single organisation."""

    id: str = Field(..., description="The CKAN organisation id or slug (name).")


def fetch_uk_gov_get_organization(params: UKGovGetOrganizationParams) -> dict:
    """Call CKAN organization_show on data.gov.uk."""
    response = http_get(
        f"{BASE_URL}/organization_show", params={"id": params.id}, provider=PROVIDER_ID
    )
    return response.json()


async def handle_uk_gov_get_organization(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-gov-get-organization tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = UKGovGetOrganizationParams(**arguments)
        data = fetch_uk_gov_get_organization(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching data.gov.uk organisation: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-gov-get-organization",
        description="Fetch full details for a data.gov.uk publishing organisation.",
        inputSchema=UKGovGetOrganizationParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-gov-get-organization"] = handle_uk_gov_get_organization


###################
# Groups List
###################


class UKGovListGroupsParams(BaseModel):
    """Parameters for listing groups (thematic collections)."""

    all_fields: bool = Field(
        default=True,
        description="Whether to return full group records (true) or just names (false).",
    )


def fetch_uk_gov_list_groups(params: UKGovListGroupsParams) -> dict:
    """Call CKAN group_list on data.gov.uk."""
    query_params: dict[str, Any] = {
        "all_fields": "true" if params.all_fields else "false",
    }
    response = http_get(
        f"{BASE_URL}/group_list", params=query_params, provider=PROVIDER_ID
    )
    return response.json()


async def handle_uk_gov_list_groups(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-gov-list-groups tool call."""
    try:
        params = UKGovListGroupsParams(**(arguments or {}))
        data = fetch_uk_gov_list_groups(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing data.gov.uk groups: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-gov-list-groups",
        description="List groups (themes) defined on data.gov.uk.",
        inputSchema=UKGovListGroupsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-gov-list-groups"] = handle_uk_gov_list_groups


###################
# Tag Suggestions
###################


class UKGovListTagsParams(BaseModel):
    """Parameters for listing or searching tags."""

    query: Optional[str] = Field(
        None,
        description="Optional substring to filter tag names (CKAN 'query').",
    )


def fetch_uk_gov_list_tags(params: UKGovListTagsParams) -> dict:
    """Call CKAN tag_list on data.gov.uk."""
    query_params: dict[str, Any] = {}
    if params.query:
        query_params["query"] = params.query
    response = http_get(
        f"{BASE_URL}/tag_list", params=query_params, provider=PROVIDER_ID
    )
    return response.json()


async def handle_uk_gov_list_tags(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-gov-list-tags tool call."""
    try:
        params = UKGovListTagsParams(**(arguments or {}))
        data = fetch_uk_gov_list_tags(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing data.gov.uk tags: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-gov-list-tags",
        description="List or search tag names on data.gov.uk.",
        inputSchema=UKGovListTagsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-gov-list-tags"] = handle_uk_gov_list_tags


###################
# Recently Changed Packages
###################


class UKGovListRecentlyChangedParams(BaseModel):
    """Parameters for fetching the recently-changed packages activity feed."""

    limit: int = Field(
        default=20,
        description="Maximum number of recent activity items to return.",
    )


def fetch_uk_gov_list_recently_changed(
    params: UKGovListRecentlyChangedParams,
) -> dict:
    """Call CKAN recently_changed_packages_activity_list on data.gov.uk."""
    query_params: dict[str, Any] = {"limit": params.limit}
    response = http_get(
        f"{BASE_URL}/recently_changed_packages_activity_list",
        params=query_params,
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_uk_gov_list_recently_changed(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the uk-gov-list-recently-changed tool call."""
    try:
        params = UKGovListRecentlyChangedParams(**(arguments or {}))
        data = fetch_uk_gov_list_recently_changed(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing recently changed data.gov.uk packages: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="uk-gov-list-recently-changed",
        description="List recently changed packages on data.gov.uk (activity feed).",
        inputSchema=UKGovListRecentlyChangedParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["uk-gov-list-recently-changed"] = handle_uk_gov_list_recently_changed


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "uk-gov", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
