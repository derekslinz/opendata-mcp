"""
ClinicalTrials.gov v2 API Provider

This module provides interfaces to access the U.S. National Library of
Medicine (NLM) / NIH ClinicalTrials.gov v2 REST API, which exposes the
public registry of clinical studies conducted around the world.

Source: https://clinicaltrials.gov/data-api/api
License: The information in ClinicalTrials.gov is provided by sponsors and
investigators and is in the public domain. See the ClinicalTrials.gov terms
and conditions for fair-use guidance:
https://clinicaltrials.gov/about-site/terms-conditions

Fair-use notes:
- The API does not require an API key.
- Use reasonable request rates; the registry recommends modest pageSize
  values and pagination via pageToken for large result sets.

Features:
- Free-text search across studies
- Detail retrieval by NCT identifier
- Search by condition, intervention, or location
- Overall registry size statistics

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://clinicaltrials.gov/api/v2"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Search Studies
###################


class CtgovSearchStudiesParams(BaseModel):
    """Parameters for searching ClinicalTrials.gov studies by free-text term."""

    query_term: Optional[str] = Field(
        None,
        description="Free-text search term (mapped to query.term)",
    )
    pageSize: int = Field(default=20, description="Number of studies per page")
    pageToken: Optional[str] = Field(
        None,
        description="Pagination token returned by a previous response (nextPageToken)",
    )
    fields: Optional[str] = Field(
        None,
        description="Comma-separated list of field paths to include (e.g. 'NCTId,BriefTitle')",
    )


def fetch_search_studies(params: CtgovSearchStudiesParams) -> dict:
    """Search ClinicalTrials.gov studies via /studies endpoint."""
    query_params: dict[str, Any] = {
        "pageSize": params.pageSize,
        "format": "json",
    }
    if params.query_term:
        query_params["query.term"] = params.query_term
    if params.pageToken:
        query_params["pageToken"] = params.pageToken
    if params.fields:
        query_params["fields"] = params.fields

    response = http_get(f"{BASE_URL}/studies", params=query_params, timeout=30.0)
    return response.json()


async def handle_search_studies(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ctgov-search-studies tool call."""
    try:
        params = CtgovSearchStudiesParams(**(arguments or {}))
        data = fetch_search_studies(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error searching ClinicalTrials.gov studies: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ctgov-search-studies",
        description=(
            "Search ClinicalTrials.gov studies by free-text term. Supports "
            "pagination via pageToken and optional fields filtering."
        ),
        inputSchema=CtgovSearchStudiesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ctgov-search-studies"] = handle_search_studies


###################
# Get Study
###################


class CtgovGetStudyParams(BaseModel):
    """Parameters for fetching a single ClinicalTrials.gov study by NCT ID."""

    nctId: str = Field(
        ..., description="NCT identifier of the study (e.g. 'NCT00000001')"
    )
    fields: Optional[str] = Field(
        None,
        description="Comma-separated list of field paths to include",
    )


def fetch_get_study(params: CtgovGetStudyParams) -> dict:
    """Fetch a single study by NCT identifier."""
    query_params: dict[str, Any] = {"format": "json"}
    if params.fields:
        query_params["fields"] = params.fields

    response = http_get(
        f"{BASE_URL}/studies/{params.nctId}",
        params=query_params,
        timeout=30.0,
    )
    return response.json()


async def handle_get_study(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ctgov-get-study tool call."""
    try:
        if not arguments or "nctId" not in arguments:
            raise ValueError("nctId is required")
        params = CtgovGetStudyParams(**arguments)
        data = fetch_get_study(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ClinicalTrials.gov study: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ctgov-get-study",
        description="Fetch the full record for a ClinicalTrials.gov study by NCT identifier (e.g. NCT00000001).",
        inputSchema=CtgovGetStudyParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ctgov-get-study"] = handle_get_study


###################
# Search by Condition
###################


class CtgovSearchByConditionParams(BaseModel):
    """Parameters for searching studies by condition / disease."""

    condition: str = Field(
        ..., description="Condition or disease name (e.g. 'diabetes')"
    )
    pageSize: int = Field(default=20, description="Number of studies per page")


def fetch_search_by_condition(params: CtgovSearchByConditionParams) -> dict:
    """Search studies by condition via query.cond."""
    query_params = {
        "query.cond": params.condition,
        "pageSize": params.pageSize,
        "format": "json",
    }
    response = http_get(f"{BASE_URL}/studies", params=query_params, timeout=30.0)
    return response.json()


async def handle_search_by_condition(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ctgov-search-by-condition tool call."""
    try:
        if not arguments or "condition" not in arguments:
            raise ValueError("condition is required")
        params = CtgovSearchByConditionParams(**arguments)
        data = fetch_search_by_condition(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error searching ClinicalTrials.gov by condition: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ctgov-search-by-condition",
        description="Search ClinicalTrials.gov studies by condition / disease name.",
        inputSchema=CtgovSearchByConditionParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ctgov-search-by-condition"] = handle_search_by_condition


###################
# Search by Intervention
###################


class CtgovSearchByInterventionParams(BaseModel):
    """Parameters for searching studies by intervention / treatment."""

    intervention: str = Field(
        ..., description="Intervention or treatment name (e.g. 'metformin')"
    )
    pageSize: int = Field(default=20, description="Number of studies per page")


def fetch_search_by_intervention(
    params: CtgovSearchByInterventionParams,
) -> dict:
    """Search studies by intervention via query.intr."""
    query_params = {
        "query.intr": params.intervention,
        "pageSize": params.pageSize,
        "format": "json",
    }
    response = http_get(f"{BASE_URL}/studies", params=query_params, timeout=30.0)
    return response.json()


async def handle_search_by_intervention(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ctgov-search-by-intervention tool call."""
    try:
        if not arguments or "intervention" not in arguments:
            raise ValueError("intervention is required")
        params = CtgovSearchByInterventionParams(**arguments)
        data = fetch_search_by_intervention(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error searching ClinicalTrials.gov by intervention: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ctgov-search-by-intervention",
        description="Search ClinicalTrials.gov studies by intervention / treatment.",
        inputSchema=CtgovSearchByInterventionParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ctgov-search-by-intervention"] = handle_search_by_intervention


###################
# Search by Location
###################


class CtgovSearchByLocationParams(BaseModel):
    """Parameters for searching studies by location."""

    location: str = Field(
        ...,
        description="Location term (city / state / country / facility); mapped to query.locn",
    )
    pageSize: int = Field(default=20, description="Number of studies per page")


def fetch_search_by_location(params: CtgovSearchByLocationParams) -> dict:
    """Search studies by location via query.locn."""
    query_params = {
        "query.locn": params.location,
        "pageSize": params.pageSize,
        "format": "json",
    }
    response = http_get(f"{BASE_URL}/studies", params=query_params, timeout=30.0)
    return response.json()


async def handle_search_by_location(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ctgov-search-by-location tool call."""
    try:
        if not arguments or "location" not in arguments:
            raise ValueError("location is required")
        params = CtgovSearchByLocationParams(**arguments)
        data = fetch_search_by_location(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error searching ClinicalTrials.gov by location: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ctgov-search-by-location",
        description="Search ClinicalTrials.gov studies by location (city, state, country or facility).",
        inputSchema=CtgovSearchByLocationParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ctgov-search-by-location"] = handle_search_by_location


###################
# List Stats (Overall Size)
###################


class CtgovListStatsParams(BaseModel):
    """Parameters for fetching overall ClinicalTrials.gov registry statistics."""

    pass


def fetch_list_stats(_params: CtgovListStatsParams) -> dict:
    """Fetch overall registry size statistics via /stats/size."""
    response = http_get(f"{BASE_URL}/stats/size", timeout=30.0)
    return response.json()


async def handle_list_stats(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ctgov-list-stats tool call."""
    try:
        params = CtgovListStatsParams(**(arguments or {}))
        data = fetch_list_stats(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ClinicalTrials.gov stats: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ctgov-list-stats",
        description="Get overall ClinicalTrials.gov registry size statistics (/stats/size).",
        inputSchema=CtgovListStatsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ctgov-list-stats"] = handle_list_stats


async def main():
    from mcp.server.stdio import stdio_server

    from opendata_mcp.utils import create_mcp_server

    server = create_mcp_server(
        "us-clinicaltrials", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
