"""
Open Library Provider

This module exposes the public Open Library API (hosted by the Internet
Archive). It covers book search, work / edition / author records, ISBN
lookup, and subject feeds.

License / source:
    Open Library data is available under Creative Commons CC0 (public
    domain dedication). Some downstream sources (e.g. cover images) may
    carry their own terms; consult openlibrary.org for details.

Features:
- Book search (`/search.json`)
- Author search (`/search/authors.json`)
- Work record (`/works/{work_id}.json`)
- Edition record (`/books/{edition_id}.json`)
- Author record (`/authors/{author_id}.json`)
- ISBN lookup (`/isbn/{isbn}.json`)
- Subject feed (`/subjects/{subject}.json`)

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://openlibrary.org"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Search books
###################


class OpenLibrarySearchBooksParams(BaseModel):
    """Parameters for searching Open Library books."""

    title: Optional[str] = Field(
        default=None, description="Title fragment to search for."
    )
    author: Optional[str] = Field(default=None, description="Author name fragment.")
    q: Optional[str] = Field(
        default=None, description="Free-text search across all fields."
    )
    limit: int = Field(
        default=10, ge=1, le=100, description="Results per page (1-100)."
    )
    page: int = Field(default=1, ge=1, description="Page number (1-indexed).")


def fetch_open_library_search_books(params: OpenLibrarySearchBooksParams) -> dict:
    """Search Open Library books."""
    query_params: dict[str, Any] = {"limit": params.limit, "page": params.page}
    if params.title:
        query_params["title"] = params.title
    if params.author:
        query_params["author"] = params.author
    if params.q:
        query_params["q"] = params.q
    response = http_get(f"{BASE_URL}/search.json", params=query_params)
    return response.json()


async def handle_openlibrary_search_books(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openlibrary-search-books tool call."""
    try:
        params = OpenLibrarySearchBooksParams(**(arguments or {}))
        data = fetch_open_library_search_books(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Open Library books: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openlibrary-search-books",
        description="Search Open Library books by title, author, or free-text query.",
        inputSchema=OpenLibrarySearchBooksParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openlibrary-search-books"] = handle_openlibrary_search_books


###################
# Search authors
###################


class OpenLibrarySearchAuthorsParams(BaseModel):
    """Parameters for searching Open Library authors."""

    q: str = Field(..., description="Free-text author search.")
    limit: int = Field(
        default=10, ge=1, le=100, description="Results per page (1-100)."
    )


def fetch_open_library_search_authors(
    params: OpenLibrarySearchAuthorsParams,
) -> dict:
    """Search Open Library authors."""
    query_params: dict[str, Any] = {"q": params.q, "limit": params.limit}
    response = http_get(f"{BASE_URL}/search/authors.json", params=query_params)
    return response.json()


async def handle_openlibrary_search_authors(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openlibrary-search-authors tool call."""
    try:
        if not arguments or "q" not in arguments:
            raise ValueError("q is required")
        params = OpenLibrarySearchAuthorsParams(**arguments)
        data = fetch_open_library_search_authors(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Open Library authors: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openlibrary-search-authors",
        description="Search Open Library authors by free-text query.",
        inputSchema=OpenLibrarySearchAuthorsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openlibrary-search-authors"] = handle_openlibrary_search_authors


###################
# Get work
###################


class OpenLibraryGetWorkParams(BaseModel):
    """Parameters for fetching a work record."""

    work_id: str = Field(..., description="Open Library work ID (e.g. 'OL45804W').")


def fetch_open_library_get_work(params: OpenLibraryGetWorkParams) -> dict:
    """Fetch an Open Library work record."""
    response = http_get(f"{BASE_URL}/works/{params.work_id}.json")
    return response.json()


async def handle_openlibrary_get_work(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openlibrary-get-work tool call."""
    try:
        if not arguments or "work_id" not in arguments:
            raise ValueError("work_id is required")
        params = OpenLibraryGetWorkParams(**arguments)
        data = fetch_open_library_get_work(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Open Library work: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openlibrary-get-work",
        description="Get an Open Library work record by ID (e.g. 'OL45804W').",
        inputSchema=OpenLibraryGetWorkParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openlibrary-get-work"] = handle_openlibrary_get_work


###################
# Get edition
###################


class OpenLibraryGetEditionParams(BaseModel):
    """Parameters for fetching an edition record."""

    edition_id: str = Field(
        ..., description="Open Library edition ID (e.g. 'OL7353617M')."
    )


def fetch_open_library_get_edition(params: OpenLibraryGetEditionParams) -> dict:
    """Fetch an Open Library edition record."""
    response = http_get(f"{BASE_URL}/books/{params.edition_id}.json")
    return response.json()


async def handle_openlibrary_get_edition(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openlibrary-get-edition tool call."""
    try:
        if not arguments or "edition_id" not in arguments:
            raise ValueError("edition_id is required")
        params = OpenLibraryGetEditionParams(**arguments)
        data = fetch_open_library_get_edition(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Open Library edition: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openlibrary-get-edition",
        description="Get an Open Library edition (book) record by ID (e.g. 'OL7353617M').",
        inputSchema=OpenLibraryGetEditionParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openlibrary-get-edition"] = handle_openlibrary_get_edition


###################
# Get author
###################


class OpenLibraryGetAuthorParams(BaseModel):
    """Parameters for fetching an author record."""

    author_id: str = Field(..., description="Open Library author ID (e.g. 'OL23919A').")


def fetch_open_library_get_author(params: OpenLibraryGetAuthorParams) -> dict:
    """Fetch an Open Library author record."""
    response = http_get(f"{BASE_URL}/authors/{params.author_id}.json")
    return response.json()


async def handle_openlibrary_get_author(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openlibrary-get-author tool call."""
    try:
        if not arguments or "author_id" not in arguments:
            raise ValueError("author_id is required")
        params = OpenLibraryGetAuthorParams(**arguments)
        data = fetch_open_library_get_author(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Open Library author: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openlibrary-get-author",
        description="Get an Open Library author record by ID (e.g. 'OL23919A').",
        inputSchema=OpenLibraryGetAuthorParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openlibrary-get-author"] = handle_openlibrary_get_author


###################
# ISBN lookup
###################


class OpenLibraryISBNLookupParams(BaseModel):
    """Parameters for ISBN lookup."""

    isbn: str = Field(
        ..., description="ISBN-10 or ISBN-13 (without hyphens or with them)."
    )


def fetch_open_library_isbn_lookup(params: OpenLibraryISBNLookupParams) -> dict:
    """Look up a book by ISBN."""
    response = http_get(f"{BASE_URL}/isbn/{params.isbn}.json")
    return response.json()


async def handle_openlibrary_isbn_lookup(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openlibrary-isbn-lookup tool call."""
    try:
        if not arguments or "isbn" not in arguments:
            raise ValueError("isbn is required")
        params = OpenLibraryISBNLookupParams(**arguments)
        data = fetch_open_library_isbn_lookup(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error performing ISBN lookup: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openlibrary-isbn-lookup",
        description="Look up an Open Library edition by ISBN.",
        inputSchema=OpenLibraryISBNLookupParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openlibrary-isbn-lookup"] = handle_openlibrary_isbn_lookup


###################
# Subject
###################


class OpenLibrarySubjectParams(BaseModel):
    """Parameters for fetching a subject feed."""

    subject: str = Field(
        ..., description="Subject slug (e.g. 'love', 'science_fiction')."
    )
    limit: int = Field(
        default=10, ge=1, le=1000, description="Maximum works to return."
    )


def fetch_open_library_subject(params: OpenLibrarySubjectParams) -> dict:
    """Fetch the subject feed for a subject slug."""
    query_params: dict[str, Any] = {"limit": params.limit}
    response = http_get(
        f"{BASE_URL}/subjects/{params.subject}.json", params=query_params
    )
    return response.json()


async def handle_openlibrary_subject(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openlibrary-subject tool call."""
    try:
        if not arguments or "subject" not in arguments:
            raise ValueError("subject is required")
        params = OpenLibrarySubjectParams(**arguments)
        data = fetch_open_library_subject(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Open Library subject: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openlibrary-subject",
        description="Get the Open Library subject feed for a slug (e.g. 'science_fiction').",
        inputSchema=OpenLibrarySubjectParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openlibrary-subject"] = handle_openlibrary_subject


async def main():
    from mcp.server.stdio import stdio_server
    from opendata_mcp.utils import create_mcp_server

    # create the server
    server = create_mcp_server(
        "global-open-library", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    # run the server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
