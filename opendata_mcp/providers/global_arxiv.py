"""
arXiv Preprint Provider

This module exposes the arXiv export API, which returns Atom XML feeds of
preprint metadata across physics, mathematics, computer science, biology,
quantitative finance, statistics, and more.

License note:
    arXiv metadata is provided for personal and scholarly use. The full text
    of each paper carries the license selected by its authors (often arXiv's
    non-exclusive license to distribute, sometimes CC-BY / CC0). Consult
    each paper's listing before redistribution.

Output format:
    Endpoints return Atom XML, not JSON. Each handler returns the raw text
    truncated to 20,000 characters so consumers can parse the feed
    themselves (e.g. with feedparser or xml.etree.ElementTree).

Features:
- Free-text and field-targeted query (title, author, abstract, category)
- Title and author shortcuts
- Category-scoped feed (e.g. cs.AI, math.NT)
- Direct paper lookup by arXiv id

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.
"""

import logging
from typing import Any, List, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://export.arxiv.org/api"

# arXiv responds with Atom XML; ask for it explicitly.
_ATOM_HEADERS = {"Accept": "application/atom+xml"}

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Query
###################


class ArxivQueryParams(BaseModel):
    """Parameters for a generic arXiv search query."""

    search_query: str = Field(
        ...,
        description=(
            "arXiv search expression, e.g. 'all:transformer', 'ti:attention', "
            "'au:hinton AND cat:cs.LG'."
        ),
    )
    start: int = Field(default=0, description="Offset into the result set.")
    max_results: int = Field(
        default=10, description="Maximum results to return (max 2000)."
    )
    sortBy: str = Field(
        default="relevance",
        description="Sort field ('relevance', 'lastUpdatedDate', 'submittedDate').",
    )
    sortOrder: str = Field(
        default="descending",
        description="Sort order ('ascending' or 'descending').",
    )


def fetch_arxiv_query(params: ArxivQueryParams) -> str:
    """Call arXiv /query and return the raw Atom XML text."""
    query_params: dict[str, Any] = {
        "search_query": params.search_query,
        "start": params.start,
        "max_results": params.max_results,
        "sortBy": params.sortBy,
        "sortOrder": params.sortOrder,
    }
    response = http_get(f"{BASE_URL}/query", params=query_params, headers=_ATOM_HEADERS)
    return response.text


async def handle_arxiv_query(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the arxiv-query tool call."""
    try:
        if not arguments or "search_query" not in arguments:
            raise ValueError("search_query is required")
        params = ArxivQueryParams(**arguments)
        data = fetch_arxiv_query(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error querying arXiv: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="arxiv-query",
        description="Run an arXiv search query and return raw Atom XML. Use field prefixes like 'ti:', 'au:', 'cat:'.",
        inputSchema=ArxivQueryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["arxiv-query"] = handle_arxiv_query


###################
# Search by Title
###################


class ArxivSearchByTitleParams(BaseModel):
    """Parameters for an arXiv title-only search."""

    title: str = Field(..., description="Title (or fragment) to search for.")
    max_results: int = Field(default=10, description="Maximum results to return.")


def fetch_arxiv_search_by_title(params: ArxivSearchByTitleParams) -> str:
    """Search arXiv by exact title phrase."""
    query_params: dict[str, Any] = {
        "search_query": f'ti:"{params.title}"',
        "max_results": params.max_results,
    }
    response = http_get(f"{BASE_URL}/query", params=query_params, headers=_ATOM_HEADERS)
    return response.text


async def handle_arxiv_search_by_title(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the arxiv-search-by-title tool call."""
    try:
        if not arguments or "title" not in arguments:
            raise ValueError("title is required")
        params = ArxivSearchByTitleParams(**arguments)
        data = fetch_arxiv_search_by_title(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching arXiv by title: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="arxiv-search-by-title",
        description="Search arXiv preprints by title (Atom XML response).",
        inputSchema=ArxivSearchByTitleParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["arxiv-search-by-title"] = handle_arxiv_search_by_title


###################
# Search by Author
###################


class ArxivSearchByAuthorParams(BaseModel):
    """Parameters for an arXiv author search."""

    author: str = Field(..., description="Author name to search for.")
    max_results: int = Field(default=10, description="Maximum results to return.")


def fetch_arxiv_search_by_author(params: ArxivSearchByAuthorParams) -> str:
    """Search arXiv by author, sorted by submission date."""
    query_params: dict[str, Any] = {
        "search_query": f'au:"{params.author}"',
        "max_results": params.max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = http_get(f"{BASE_URL}/query", params=query_params, headers=_ATOM_HEADERS)
    return response.text


async def handle_arxiv_search_by_author(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the arxiv-search-by-author tool call."""
    try:
        if not arguments or "author" not in arguments:
            raise ValueError("author is required")
        params = ArxivSearchByAuthorParams(**arguments)
        data = fetch_arxiv_search_by_author(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching arXiv by author: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="arxiv-search-by-author",
        description="Search arXiv preprints by author, newest first (Atom XML response).",
        inputSchema=ArxivSearchByAuthorParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["arxiv-search-by-author"] = handle_arxiv_search_by_author


###################
# Search by Category
###################


class ArxivSearchByCategoryParams(BaseModel):
    """Parameters for an arXiv category feed."""

    category: str = Field(
        ..., description="arXiv category slug (e.g. 'cs.AI', 'math.NT', 'q-bio.PE')."
    )
    max_results: int = Field(default=10, description="Maximum results to return.")


def fetch_arxiv_search_by_category(params: ArxivSearchByCategoryParams) -> str:
    """Fetch the most recent papers in an arXiv category."""
    query_params: dict[str, Any] = {
        "search_query": f"cat:{params.category}",
        "max_results": params.max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = http_get(f"{BASE_URL}/query", params=query_params, headers=_ATOM_HEADERS)
    return response.text


async def handle_arxiv_search_by_category(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the arxiv-search-by-category tool call."""
    try:
        if not arguments or "category" not in arguments:
            raise ValueError("category is required")
        params = ArxivSearchByCategoryParams(**arguments)
        data = fetch_arxiv_search_by_category(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching arXiv by category: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="arxiv-search-by-category",
        description="Fetch the latest arXiv preprints for a category like 'cs.AI' or 'math.NT'.",
        inputSchema=ArxivSearchByCategoryParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["arxiv-search-by-category"] = handle_arxiv_search_by_category


###################
# Get Paper
###################


class ArxivGetPaperParams(BaseModel):
    """Parameters for fetching a single arXiv paper by id."""

    arxiv_id: str = Field(
        ..., description="arXiv identifier (e.g. '2104.08653' or 'cs.AI/0606009')."
    )


def fetch_arxiv_get_paper(params: ArxivGetPaperParams) -> str:
    """Look up a single arXiv paper by id_list."""
    query_params: dict[str, Any] = {"id_list": params.arxiv_id}
    response = http_get(f"{BASE_URL}/query", params=query_params, headers=_ATOM_HEADERS)
    return response.text


async def handle_arxiv_get_paper(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the arxiv-get-paper tool call."""
    try:
        if not arguments or "arxiv_id" not in arguments:
            raise ValueError("arxiv_id is required")
        params = ArxivGetPaperParams(**arguments)
        data = fetch_arxiv_get_paper(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching arXiv paper: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="arxiv-get-paper",
        description="Fetch metadata for a single arXiv paper by its identifier (Atom XML response).",
        inputSchema=ArxivGetPaperParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["arxiv-get-paper"] = handle_arxiv_get_paper


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-arxiv", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
