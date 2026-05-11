"""
Wikidata Provider

This module exposes Wikidata's public MediaWiki Action API and the Wikidata
Query Service (SPARQL) endpoint. Wikidata is a free, collaboratively edited
multilingual knowledge graph hosted by the Wikimedia Foundation.

License note:
    Wikidata structured data is released under the Creative Commons CC0
    public domain dedication. Some text snippets in entity labels/descriptions
    may carry CC BY-SA. Wikimedia request that callers respect the
    User-Agent and rate-limit policies; this module relies on the project's
    default User-Agent set in opendata_mcp.utils.http_get.

Features:
- Fetch entity records by Q/P id (wbgetentities)
- Free-text entity search (wbsearchentities)
- Fetch claims/statements on a single entity (wbgetclaims)
- Run arbitrary SPARQL against the Wikidata Query Service
- Search property entities (P-ids) by name
- Resolve an entity from its Wikipedia article title

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
BASE_URL = "https://www.wikidata.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# wbgetentities (by ids)
###################


class WikidataGetEntitiesParams(BaseModel):
    """Parameters for fetching Wikidata entities by id."""

    ids: str = Field(
        ...,
        description="Comma-separated list of entity ids, e.g. 'Q42,Q5' or 'P31'.",
    )
    languages: Optional[str] = Field(
        None,
        description="Optional comma-separated language codes to restrict labels/descriptions, e.g. 'en,fr'.",
    )


def fetch_wikidata_entities(params: WikidataGetEntitiesParams) -> dict:
    """Call action=wbgetentities on the Wikidata Action API."""
    query_params: dict[str, Any] = {
        "action": "wbgetentities",
        "ids": params.ids,
        "format": "json",
    }
    if params.languages:
        query_params["languages"] = params.languages
    response = http_get(BASE_URL, params=query_params)
    return response.json()


async def handle_wikidata_get_entities(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the wikidata-get-entities tool call."""
    try:
        if not arguments or "ids" not in arguments:
            raise ValueError("ids is required")
        params = WikidataGetEntitiesParams(**arguments)
        data = fetch_wikidata_entities(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Wikidata entities: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="wikidata-get-entities",
        description="Fetch one or more Wikidata entities by Q/P id (action=wbgetentities).",
        inputSchema=WikidataGetEntitiesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["wikidata-get-entities"] = handle_wikidata_get_entities


###################
# wbsearchentities (items)
###################


class WikidataSearchEntitiesParams(BaseModel):
    """Parameters for free-text entity search on Wikidata."""

    search: str = Field(..., description="Free-text query string.")
    language: str = Field(default="en", description="Search language code.")
    limit: int = Field(default=10, description="Maximum number of results.")


def fetch_wikidata_search_entities(params: WikidataSearchEntitiesParams) -> dict:
    """Call action=wbsearchentities (type=item) on the Wikidata Action API."""
    query_params: dict[str, Any] = {
        "action": "wbsearchentities",
        "search": params.search,
        "language": params.language,
        "type": "item",
        "limit": params.limit,
        "format": "json",
    }
    response = http_get(BASE_URL, params=query_params)
    return response.json()


async def handle_wikidata_search_entities(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the wikidata-search-entities tool call."""
    try:
        if not arguments or "search" not in arguments:
            raise ValueError("search is required")
        params = WikidataSearchEntitiesParams(**arguments)
        data = fetch_wikidata_search_entities(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Wikidata entities: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="wikidata-search-entities",
        description="Free-text search for Wikidata item entities (Q-ids).",
        inputSchema=WikidataSearchEntitiesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["wikidata-search-entities"] = handle_wikidata_search_entities


###################
# wbgetclaims
###################


class WikidataGetClaimsParams(BaseModel):
    """Parameters for fetching claims on a Wikidata entity."""

    entity: str = Field(..., description="Entity id, e.g. 'Q42'.")
    property: Optional[str] = Field(
        None,
        description="Optional property id to filter to a single property, e.g. 'P31'.",
    )


def fetch_wikidata_claims(params: WikidataGetClaimsParams) -> dict:
    """Call action=wbgetclaims on the Wikidata Action API."""
    query_params: dict[str, Any] = {
        "action": "wbgetclaims",
        "entity": params.entity,
        "format": "json",
    }
    if params.property:
        query_params["property"] = params.property
    response = http_get(BASE_URL, params=query_params)
    return response.json()


async def handle_wikidata_get_claims(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the wikidata-get-claims tool call."""
    try:
        if not arguments or "entity" not in arguments:
            raise ValueError("entity is required")
        params = WikidataGetClaimsParams(**arguments)
        data = fetch_wikidata_claims(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Wikidata claims: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="wikidata-get-claims",
        description="Fetch claims (statements) for a Wikidata entity, optionally filtered by property.",
        inputSchema=WikidataGetClaimsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["wikidata-get-claims"] = handle_wikidata_get_claims


###################
# SPARQL
###################


class WikidataSPARQLParams(BaseModel):
    """Parameters for running a SPARQL query against the Wikidata Query Service."""

    query: str = Field(..., description="SPARQL query to execute.")


def fetch_wikidata_sparql(params: WikidataSPARQLParams) -> dict:
    """Run a SPARQL query against https://query.wikidata.org/sparql."""
    response = http_get(
        SPARQL_URL,
        params={"query": params.query},
        headers={"Accept": "application/sparql-results+json"},
    )
    return response.json()


async def handle_wikidata_sparql(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the wikidata-sparql tool call."""
    try:
        if not arguments or "query" not in arguments:
            raise ValueError("query is required")
        params = WikidataSPARQLParams(**arguments)
        data = fetch_wikidata_sparql(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error running Wikidata SPARQL: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="wikidata-sparql",
        description="Run a SPARQL query against the Wikidata Query Service.",
        inputSchema=WikidataSPARQLParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["wikidata-sparql"] = handle_wikidata_sparql


###################
# wbsearchentities (properties)
###################


class WikidataListPropertiesParams(BaseModel):
    """Parameters for searching Wikidata property entities (P-ids)."""

    search: str = Field(..., description="Free-text query for the property name.")
    language: str = Field(default="en", description="Search language code.")
    limit: int = Field(default=10, description="Maximum number of results.")


def fetch_wikidata_list_properties(params: WikidataListPropertiesParams) -> dict:
    """Call action=wbsearchentities (type=property) on the Wikidata Action API."""
    query_params: dict[str, Any] = {
        "action": "wbsearchentities",
        "search": params.search,
        "language": params.language,
        "type": "property",
        "limit": params.limit,
        "format": "json",
    }
    response = http_get(BASE_URL, params=query_params)
    return response.json()


async def handle_wikidata_list_properties(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the wikidata-list-properties tool call."""
    try:
        if not arguments or "search" not in arguments:
            raise ValueError("search is required")
        params = WikidataListPropertiesParams(**arguments)
        data = fetch_wikidata_list_properties(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching Wikidata properties: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="wikidata-list-properties",
        description="Search Wikidata property entities (P-ids) by name.",
        inputSchema=WikidataListPropertiesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["wikidata-list-properties"] = handle_wikidata_list_properties


###################
# wbgetentities by Wikipedia title
###################


class WikidataGetByTitleParams(BaseModel):
    """Parameters for resolving a Wikidata entity from a Wikipedia article title."""

    titles: str = Field(
        ...,
        description="Pipe-separated Wikipedia article titles, e.g. 'Albert Einstein|Marie Curie'.",
    )
    sites: str = Field(
        default="enwiki",
        description="Wikipedia site id, e.g. 'enwiki', 'frwiki'.",
    )


def fetch_wikidata_get_by_title(params: WikidataGetByTitleParams) -> dict:
    """Call action=wbgetentities with sites+titles on the Wikidata Action API."""
    query_params: dict[str, Any] = {
        "action": "wbgetentities",
        "sites": params.sites,
        "titles": params.titles,
        "format": "json",
    }
    response = http_get(BASE_URL, params=query_params)
    return response.json()


async def handle_wikidata_get_by_title(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the wikidata-get-entity-by-title tool call."""
    try:
        if not arguments or "titles" not in arguments:
            raise ValueError("titles is required")
        params = WikidataGetByTitleParams(**arguments)
        data = fetch_wikidata_get_by_title(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Wikidata entity by Wikipedia title: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="wikidata-get-entity-by-title",
        description="Resolve Wikidata entities from Wikipedia article titles (sites+titles).",
        inputSchema=WikidataGetByTitleParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["wikidata-get-entity-by-title"] = handle_wikidata_get_by_title


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-wikidata", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
