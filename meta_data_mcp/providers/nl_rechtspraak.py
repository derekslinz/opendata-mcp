"""
Dutch Rechtspraak (Case Law) Provider

This module provides interfaces to the Dutch Rechtspraak Open Data API,
the official source for Dutch court rulings and case law.

License: Rechtspraak data is in the public domain.
See https://www.rechtspraak.nl/Paginas/Open-Data.aspx for details.

API Documentation: https://www.rechtspraak.nl/Paginas/Open-Data.aspx
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://data.rechtspraak.nl/uitspraken"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# Rechtspraak Search
###################


class RechtspraakSearchParams(BaseModel):
    """Parameters for searching Dutch court rulings."""

    query: str = Field(..., description="Search query (e.g. 'arbeidsrecht')")
    max_results: int = Field(
        default=10, description="Maximum number of results to return (max 1000)"
    )
    date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")


def search_rechtspraak(params: RechtspraakSearchParams) -> List[dict]:
    """Search for rulings via the Rechtspraak OpenSearch API."""
    query_params = {
        "q": params.query,
        "max": params.max_results,
    }
    if params.date_from:
        query_params["date"] = params.date_from
    # Note: The API support for date ranges is specific, but simple 'date' filter is common.

    response = http_get(f"{BASE_URL}/zoeken", params=query_params)
    root = ET.fromstring(response.content)

    results = []
    for entry in root.findall("atom:entry", ATOM_NS):
        results.append(
            {
                "ecli": entry.findtext("atom:id", "", ATOM_NS),
                "title": entry.findtext("atom:title", "", ATOM_NS),
                "summary": entry.findtext("atom:summary", "", ATOM_NS),
                "updated": entry.findtext("atom:updated", "", ATOM_NS),
                "link": entry.find("atom:link", ATOM_NS).get("href")
                if entry.find("atom:link", ATOM_NS) is not None
                else "",
            }
        )
    return results


async def handle_rechtspraak_search(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the rechtspraak-search tool call."""
    try:
        params = RechtspraakSearchParams(**(arguments or {}))
        data = search_rechtspraak(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Rechtspraak: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="rechtspraak-search",
        description="Search for Dutch court rulings (uitspraken) via ECLI and text search.",
        inputSchema=RechtspraakSearchParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["rechtspraak-search"] = handle_rechtspraak_search

###################
# Rechtspraak Content
###################


class RechtspraakContentParams(BaseModel):
    """Parameters for fetching a specific Dutch ruling."""

    ecli: str = Field(
        ..., description="The ECLI identifier (e.g. 'ECLI:NL:HR:2020:1234')"
    )


def fetch_rechtspraak_content(params: RechtspraakContentParams) -> str:
    """Fetch the full content of a ruling from Rechtspraak."""
    query_params = {"id": params.ecli}
    response = http_get(f"{BASE_URL}/content", params=query_params)
    # Return raw XML as it contains structured legal data
    return response.text


async def handle_rechtspraak_content(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the rechtspraak-get-content tool call."""
    try:
        params = RechtspraakContentParams(**(arguments or {}))
        data = fetch_rechtspraak_content(params)
        return [types.TextContent(type="text", text=data)]
    except Exception as e:
        log.error(f"Error fetching Rechtspraak content: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="rechtspraak-get-content",
        description="Fetch the full text and metadata of a specific Dutch court ruling by ECLI.",
        inputSchema=RechtspraakContentParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["rechtspraak-get-content"] = handle_rechtspraak_content


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "nl-rechtspraak", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
