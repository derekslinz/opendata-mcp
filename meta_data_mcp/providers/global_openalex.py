"""
OpenAlex Provider

This module exposes the OpenAlex API, a fully open index of the global
scholarly research graph: works, authors, institutions, sources
(journals/repositories), concepts, and publishers.

License note:
    OpenAlex metadata is released under the CC0 public-domain
    dedication (see https://docs.openalex.org/ for details).

Polite pool:
    OpenAlex routes traffic from clients that identify themselves via
    the ``mailto`` query parameter onto a faster, more reliable pool.
    This module injects ``mailto`` automatically from the
    ``OPENDATA_MCP_CONTACT`` environment variable (falling back to a
    safe default).

Features:
- Works search (by query, with filters, sort, paging)
- Single-work lookup by id (OpenAlex W-id, DOI, or full URL)
- Authors / institutions / sources / concepts / publishers search
- Single-author lookup

Usage:
    The module can be run directly to start an MCP server, or its
    components can be imported individually.
"""

import logging
import os
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
PROVIDER_ID = "global-openalex"
BASE_URL = "https://api.openalex.org"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _polite_params() -> dict[str, str]:
    """Return polite-pool query params (``mailto``) for every OpenAlex call."""
    return {"mailto": os.getenv("OPENDATA_MCP_CONTACT", "opendata-mcp@example.org")}


def _merge_params(extra: dict[str, Any]) -> dict[str, Any]:
    """Merge polite-pool params with caller-supplied query params."""
    merged: dict[str, Any] = {}
    merged.update(_polite_params())
    merged.update(extra)
    return merged


###################
# Search Works
###################


class OpenAlexSearchWorksParams(BaseModel):
    """Parameters for searching OpenAlex works."""

    search: Optional[str] = Field(
        None, description="Free-text search query across work fields."
    )
    per_page: int = Field(default=25, description="Results per page (max 200).")
    page: int = Field(default=1, description="Results page (1-indexed).")
    filter: Optional[str] = Field(
        None,
        description=(
            "Comma-separated OpenAlex filter expression "
            "(e.g. 'from_publication_date:2024-01-01,type:journal-article')."
        ),
    )
    sort: Optional[str] = Field(
        None,
        description=(
            "Sort expression, e.g. 'cited_by_count:desc', 'publication_date:desc'."
        ),
    )


def fetch_openalex_search_works(params: OpenAlexSearchWorksParams) -> dict:
    """Call /works."""
    query_params: dict[str, Any] = {
        "per_page": params.per_page,
        "page": params.page,
    }
    if params.search:
        query_params["search"] = params.search
    if params.filter:
        query_params["filter"] = params.filter
    if params.sort:
        query_params["sort"] = params.sort
    response = http_get(
        f"{BASE_URL}/works", params=_merge_params(query_params), provider=PROVIDER_ID
    )
    return response.json()


async def handle_openalex_search_works(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openalex-search-works tool call."""
    try:
        params = OpenAlexSearchWorksParams(**(arguments or {}))
        data = fetch_openalex_search_works(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching OpenAlex works: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openalex-search-works",
        description="Search OpenAlex works with free text, filters, sort, and paging.",
        inputSchema=OpenAlexSearchWorksParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openalex-search-works"] = handle_openalex_search_works


###################
# Get Work
###################


class OpenAlexGetWorkParams(BaseModel):
    """Parameters for fetching a single OpenAlex work."""

    id: str = Field(
        ...,
        description=(
            "OpenAlex work id ('W12345'), a DOI ('doi:10.1038/...'), or full "
            "OpenAlex URL."
        ),
    )


def fetch_openalex_get_work(params: OpenAlexGetWorkParams) -> dict:
    """Call /works/{id}."""
    response = http_get(
        f"{BASE_URL}/works/{params.id}", params=_merge_params({}), provider=PROVIDER_ID
    )
    return response.json()


async def handle_openalex_get_work(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openalex-get-work tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = OpenAlexGetWorkParams(**arguments)
        data = fetch_openalex_get_work(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching OpenAlex work: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openalex-get-work",
        description=(
            "Fetch a single OpenAlex work by id (OpenAlex W-id, DOI "
            "prefix, or full URL)."
        ),
        inputSchema=OpenAlexGetWorkParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openalex-get-work"] = handle_openalex_get_work


###################
# Search Authors
###################


class OpenAlexSearchAuthorsParams(BaseModel):
    """Parameters for searching OpenAlex authors."""

    search: Optional[str] = Field(None, description="Free-text search query.")
    per_page: int = Field(default=25, description="Results per page (max 200).")
    page: int = Field(default=1, description="Results page (1-indexed).")
    filter: Optional[str] = Field(
        None,
        description="Comma-separated OpenAlex filter expression.",
    )


def fetch_openalex_search_authors(params: OpenAlexSearchAuthorsParams) -> dict:
    """Call /authors."""
    query_params: dict[str, Any] = {
        "per_page": params.per_page,
        "page": params.page,
    }
    if params.search:
        query_params["search"] = params.search
    if params.filter:
        query_params["filter"] = params.filter
    response = http_get(
        f"{BASE_URL}/authors", params=_merge_params(query_params), provider=PROVIDER_ID
    )
    return response.json()


async def handle_openalex_search_authors(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openalex-search-authors tool call."""
    try:
        params = OpenAlexSearchAuthorsParams(**(arguments or {}))
        data = fetch_openalex_search_authors(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching OpenAlex authors: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openalex-search-authors",
        description="Search OpenAlex authors by free-text query and optional filters.",
        inputSchema=OpenAlexSearchAuthorsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openalex-search-authors"] = handle_openalex_search_authors


###################
# Get Author
###################


class OpenAlexGetAuthorParams(BaseModel):
    """Parameters for fetching a single OpenAlex author."""

    id: str = Field(
        ...,
        description=(
            "OpenAlex author id ('A12345'), an ORCID ('orcid:0000-...'), or "
            "full OpenAlex URL."
        ),
    )


def fetch_openalex_get_author(params: OpenAlexGetAuthorParams) -> dict:
    """Call /authors/{id}."""
    response = http_get(
        f"{BASE_URL}/authors/{params.id}",
        params=_merge_params({}),
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_openalex_get_author(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openalex-get-author tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = OpenAlexGetAuthorParams(**arguments)
        data = fetch_openalex_get_author(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching OpenAlex author: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openalex-get-author",
        description="Fetch a single OpenAlex author by id (A-id, ORCID, or full URL).",
        inputSchema=OpenAlexGetAuthorParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openalex-get-author"] = handle_openalex_get_author


###################
# Search Institutions
###################


class OpenAlexSearchInstitutionsParams(BaseModel):
    """Parameters for searching OpenAlex institutions."""

    search: Optional[str] = Field(None, description="Free-text search query.")
    per_page: int = Field(default=25, description="Results per page (max 200).")
    filter: Optional[str] = Field(
        None,
        description="Comma-separated OpenAlex filter expression.",
    )


def fetch_openalex_search_institutions(
    params: OpenAlexSearchInstitutionsParams,
) -> dict:
    """Call /institutions."""
    query_params: dict[str, Any] = {"per_page": params.per_page}
    if params.search:
        query_params["search"] = params.search
    if params.filter:
        query_params["filter"] = params.filter
    response = http_get(
        f"{BASE_URL}/institutions",
        params=_merge_params(query_params),
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_openalex_search_institutions(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openalex-search-institutions tool call."""
    try:
        params = OpenAlexSearchInstitutionsParams(**(arguments or {}))
        data = fetch_openalex_search_institutions(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching OpenAlex institutions: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openalex-search-institutions",
        description="Search OpenAlex institutions (universities, labs, etc.) by free-text query.",
        inputSchema=OpenAlexSearchInstitutionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openalex-search-institutions"] = handle_openalex_search_institutions


###################
# Search Sources
###################


class OpenAlexSearchSourcesParams(BaseModel):
    """Parameters for searching OpenAlex sources (journals/repositories)."""

    search: Optional[str] = Field(None, description="Free-text search query.")
    per_page: int = Field(default=25, description="Results per page (max 200).")
    filter: Optional[str] = Field(
        None,
        description="Comma-separated OpenAlex filter expression.",
    )


def fetch_openalex_search_sources(params: OpenAlexSearchSourcesParams) -> dict:
    """Call /sources."""
    query_params: dict[str, Any] = {"per_page": params.per_page}
    if params.search:
        query_params["search"] = params.search
    if params.filter:
        query_params["filter"] = params.filter
    response = http_get(
        f"{BASE_URL}/sources", params=_merge_params(query_params), provider=PROVIDER_ID
    )
    return response.json()


async def handle_openalex_search_sources(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openalex-search-sources tool call."""
    try:
        params = OpenAlexSearchSourcesParams(**(arguments or {}))
        data = fetch_openalex_search_sources(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching OpenAlex sources: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openalex-search-sources",
        description="Search OpenAlex sources (journals, repositories, conferences) by free-text query.",
        inputSchema=OpenAlexSearchSourcesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openalex-search-sources"] = handle_openalex_search_sources


###################
# Search Concepts
###################


class OpenAlexSearchConceptsParams(BaseModel):
    """Parameters for searching OpenAlex concepts."""

    search: Optional[str] = Field(None, description="Free-text search query.")
    per_page: int = Field(default=25, description="Results per page (max 200).")


def fetch_openalex_search_concepts(params: OpenAlexSearchConceptsParams) -> dict:
    """Call /concepts."""
    query_params: dict[str, Any] = {"per_page": params.per_page}
    if params.search:
        query_params["search"] = params.search
    response = http_get(
        f"{BASE_URL}/concepts", params=_merge_params(query_params), provider=PROVIDER_ID
    )
    return response.json()


async def handle_openalex_search_concepts(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openalex-search-concepts tool call."""
    try:
        params = OpenAlexSearchConceptsParams(**(arguments or {}))
        data = fetch_openalex_search_concepts(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching OpenAlex concepts: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openalex-search-concepts",
        description="Search OpenAlex concepts (topical taxonomy) by free-text query.",
        inputSchema=OpenAlexSearchConceptsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openalex-search-concepts"] = handle_openalex_search_concepts


###################
# Search Publishers
###################


class OpenAlexSearchPublishersParams(BaseModel):
    """Parameters for searching OpenAlex publishers."""

    search: Optional[str] = Field(None, description="Free-text search query.")
    per_page: int = Field(default=25, description="Results per page (max 200).")


def fetch_openalex_search_publishers(params: OpenAlexSearchPublishersParams) -> dict:
    """Call /publishers."""
    query_params: dict[str, Any] = {"per_page": params.per_page}
    if params.search:
        query_params["search"] = params.search
    response = http_get(
        f"{BASE_URL}/publishers",
        params=_merge_params(query_params),
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_openalex_search_publishers(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openalex-search-publishers tool call."""
    try:
        params = OpenAlexSearchPublishersParams(**(arguments or {}))
        data = fetch_openalex_search_publishers(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching OpenAlex publishers: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openalex-search-publishers",
        description="Search OpenAlex publishers by free-text query.",
        inputSchema=OpenAlexSearchPublishersParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openalex-search-publishers"] = handle_openalex_search_publishers


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-openalex", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
