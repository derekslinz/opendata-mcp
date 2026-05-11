"""
Crossref Scholarly Metadata Provider

This module exposes the Crossref REST API, the canonical source of DOI
metadata for journal articles, books, datasets, conference proceedings,
and more.

License note:
    Crossref metadata is generally available under CC0 (works metadata) or
    CC-BY (member metadata). Polite-pool usage requires identifying the
    client via User-Agent, which ``http_get`` already provides; the
    contact email can be customised via the ``OPENDATA_MCP_CONTACT``
    environment variable.

Features:
- Works search (full-text, author, title) with filters and field selection
- Single-work lookup by DOI
- Journals search and single-journal lookup by ISSN
- Funders search

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.
"""

import logging
from typing import Any, List, Optional, Sequence
from urllib.parse import quote

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.crossref.org"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Works Search
###################


class CrossrefWorksSearchParams(BaseModel):
    """Parameters for searching Crossref /works."""

    query: Optional[str] = Field(
        None, description="Free-text search query across all fields."
    )
    rows: int = Field(default=20, description="Number of results per page (max 1000).")
    offset: int = Field(default=0, description="Offset into the result set.")
    filter: Optional[str] = Field(
        None,
        description="Comma-separated Crossref filter expression (e.g. 'from-pub-date:2020,type:journal-article').",
    )
    select: Optional[str] = Field(
        None,
        description="Comma-separated list of fields to return (e.g. 'DOI,title,author').",
    )
    sort: Optional[str] = Field(
        None,
        description="Sort field (e.g. 'score', 'published', 'is-referenced-by-count').",
    )
    order: Optional[str] = Field(None, description="Sort order ('asc' or 'desc').")


def fetch_crossref_works_search(params: CrossrefWorksSearchParams) -> dict:
    """Call Crossref /works for a general search."""
    query_params: dict[str, Any] = {
        "rows": params.rows,
        "offset": params.offset,
    }
    if params.query:
        query_params["query"] = params.query
    if params.filter:
        query_params["filter"] = params.filter
    if params.select:
        query_params["select"] = params.select
    if params.sort:
        query_params["sort"] = params.sort
    if params.order:
        query_params["order"] = params.order
    response = http_get(f"{BASE_URL}/works", params=query_params)
    return response.json()


async def handle_crossref_works_search(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the crossref-works-search tool call."""
    try:
        params = CrossrefWorksSearchParams(**(arguments or {}))
        data = fetch_crossref_works_search(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Crossref works: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="crossref-works-search",
        description="Search Crossref scholarly works with full-text query, filters, sort, and field selection.",
        inputSchema=CrossrefWorksSearchParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["crossref-works-search"] = handle_crossref_works_search


###################
# Get Work
###################


class CrossrefGetWorkParams(BaseModel):
    """Parameters for fetching a single Crossref work by DOI."""

    doi: str = Field(..., description="DOI of the work (e.g. '10.1038/nature12373').")


def fetch_crossref_get_work(params: CrossrefGetWorkParams) -> dict:
    """Call Crossref /works/{doi}."""
    # safe="" forces full URL-encoding (including the '/').
    encoded = quote(params.doi, safe="")
    response = http_get(f"{BASE_URL}/works/{encoded}")
    return response.json()


async def handle_crossref_get_work(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the crossref-get-work tool call."""
    try:
        if not arguments or "doi" not in arguments:
            raise ValueError("doi is required")
        params = CrossrefGetWorkParams(**arguments)
        data = fetch_crossref_get_work(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Crossref work: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="crossref-get-work",
        description="Fetch the full Crossref metadata record for a single DOI.",
        inputSchema=CrossrefGetWorkParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["crossref-get-work"] = handle_crossref_get_work


###################
# Works by Author
###################


class CrossrefWorksByAuthorParams(BaseModel):
    """Parameters for searching Crossref works by author."""

    author: str = Field(..., description="Author name to search for.")
    rows: int = Field(default=20, description="Number of results per page.")
    select: Optional[str] = Field(
        None,
        description="Comma-separated list of fields to return (e.g. 'DOI,title,author').",
    )


def fetch_crossref_works_by_author(params: CrossrefWorksByAuthorParams) -> dict:
    """Call Crossref /works with query.author."""
    query_params: dict[str, Any] = {
        "query.author": params.author,
        "rows": params.rows,
    }
    if params.select:
        query_params["select"] = params.select
    response = http_get(f"{BASE_URL}/works", params=query_params)
    return response.json()


async def handle_crossref_works_by_author(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the crossref-works-by-author tool call."""
    try:
        if not arguments or "author" not in arguments:
            raise ValueError("author is required")
        params = CrossrefWorksByAuthorParams(**arguments)
        data = fetch_crossref_works_by_author(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Crossref works by author: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="crossref-works-by-author",
        description="Search Crossref works whose author field matches the given name.",
        inputSchema=CrossrefWorksByAuthorParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["crossref-works-by-author"] = handle_crossref_works_by_author


###################
# Works by Title
###################


class CrossrefWorksByTitleParams(BaseModel):
    """Parameters for searching Crossref works by title."""

    title: str = Field(..., description="Title (or fragment) to search for.")
    rows: int = Field(default=20, description="Number of results per page.")


def fetch_crossref_works_by_title(params: CrossrefWorksByTitleParams) -> dict:
    """Call Crossref /works with query.title."""
    query_params: dict[str, Any] = {
        "query.title": params.title,
        "rows": params.rows,
    }
    response = http_get(f"{BASE_URL}/works", params=query_params)
    return response.json()


async def handle_crossref_works_by_title(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the crossref-works-by-title tool call."""
    try:
        if not arguments or "title" not in arguments:
            raise ValueError("title is required")
        params = CrossrefWorksByTitleParams(**arguments)
        data = fetch_crossref_works_by_title(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Crossref works by title: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="crossref-works-by-title",
        description="Search Crossref works whose title field matches the given query.",
        inputSchema=CrossrefWorksByTitleParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["crossref-works-by-title"] = handle_crossref_works_by_title


###################
# Journals Search
###################


class CrossrefJournalsSearchParams(BaseModel):
    """Parameters for searching Crossref /journals."""

    query: str = Field(..., description="Free-text query over journal metadata.")
    rows: int = Field(default=20, description="Number of results per page.")


def fetch_crossref_journals_search(params: CrossrefJournalsSearchParams) -> dict:
    """Call Crossref /journals."""
    query_params: dict[str, Any] = {
        "query": params.query,
        "rows": params.rows,
    }
    response = http_get(f"{BASE_URL}/journals", params=query_params)
    return response.json()


async def handle_crossref_journals_search(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the crossref-journals-search tool call."""
    try:
        if not arguments or "query" not in arguments:
            raise ValueError("query is required")
        params = CrossrefJournalsSearchParams(**arguments)
        data = fetch_crossref_journals_search(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Crossref journals: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="crossref-journals-search",
        description="Search Crossref journals by free-text query.",
        inputSchema=CrossrefJournalsSearchParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["crossref-journals-search"] = handle_crossref_journals_search


###################
# Get Journal
###################


class CrossrefGetJournalParams(BaseModel):
    """Parameters for fetching a single Crossref journal by ISSN."""

    issn: str = Field(..., description="ISSN of the journal (e.g. '1476-4687').")


def fetch_crossref_get_journal(params: CrossrefGetJournalParams) -> dict:
    """Call Crossref /journals/{issn}."""
    response = http_get(f"{BASE_URL}/journals/{params.issn}")
    return response.json()


async def handle_crossref_get_journal(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the crossref-get-journal tool call."""
    try:
        if not arguments or "issn" not in arguments:
            raise ValueError("issn is required")
        params = CrossrefGetJournalParams(**arguments)
        data = fetch_crossref_get_journal(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Crossref journal: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="crossref-get-journal",
        description="Fetch the full Crossref metadata record for a single journal by ISSN.",
        inputSchema=CrossrefGetJournalParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["crossref-get-journal"] = handle_crossref_get_journal


###################
# Funders Search
###################


class CrossrefFundersSearchParams(BaseModel):
    """Parameters for searching Crossref /funders."""

    query: str = Field(..., description="Free-text query over funder metadata.")
    rows: int = Field(default=20, description="Number of results per page.")


def fetch_crossref_funders_search(params: CrossrefFundersSearchParams) -> dict:
    """Call Crossref /funders."""
    query_params: dict[str, Any] = {
        "query": params.query,
        "rows": params.rows,
    }
    response = http_get(f"{BASE_URL}/funders", params=query_params)
    return response.json()


async def handle_crossref_funders_search(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the crossref-funders-search tool call."""
    try:
        if not arguments or "query" not in arguments:
            raise ValueError("query is required")
        params = CrossrefFundersSearchParams(**arguments)
        data = fetch_crossref_funders_search(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Crossref funders: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="crossref-funders-search",
        description="Search Crossref funders by free-text query.",
        inputSchema=CrossrefFundersSearchParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["crossref-funders-search"] = handle_crossref_funders_search


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-crossref", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
