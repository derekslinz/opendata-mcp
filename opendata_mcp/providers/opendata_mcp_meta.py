"""
OpenData MCP Meta-Aggregator

This provider exposes discovery tools over the entire opendata-mcp provider
registry. An LLM that has only this one MCP server installed can:

- Search across all providers by free-text query
- Filter by domain (e.g. "health", "legal", "finance") or region (e.g. "us",
  "eu", "global")
- Get full metadata for a given provider, including the env vars it requires

This solves the discovery problem at scale: with 50+ providers, an LLM no
longer needs to memorize tool names — it asks `opendata-find-providers`
first, then sets up only the providers it needs.

Tools:
- opendata-find-providers   — query + optional domain/region filters
- opendata-list-domains     — enumerate the controlled domain vocabulary
- opendata-list-regions     — enumerate the controlled region vocabulary
- opendata-describe-provider — full registry entry for one provider id
- opendata-list-providers   — all providers (terse, paginated)
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import serialize_for_llm

from opendata_mcp.registry import (
    REGISTRY,
    find_providers,
    get_provider,
    list_domains,
    list_regions,
)

log = logging.getLogger(__name__)

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# find-providers
###################


class FindProvidersParams(BaseModel):
    """Filters for `opendata-find-providers`."""

    query: Optional[str] = Field(
        None,
        description="Free-text query. Matched against id, title, description, keywords, domains, regions. Tokens with exact keyword hits score higher.",
    )
    domain: Optional[str] = Field(
        None,
        description="Restrict to providers tagged with this domain (e.g. 'health', 'legal', 'finance'). Use opendata-list-domains to enumerate.",
    )
    region: Optional[str] = Field(
        None,
        description="Restrict to providers tagged with this region (e.g. 'us', 'eu', 'uk', 'global'). Use opendata-list-regions to enumerate.",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of providers to return (1-100, default 20).",
    )


async def handle_find_providers(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-find-providers tool call."""
    try:
        params = FindProvidersParams(**(arguments or {}))
        matches = find_providers(
            query=params.query,
            domain=params.domain,
            region=params.region,
            limit=params.limit,
        )
        payload = {
            "count": len(matches),
            "providers": [entry.to_dict() for entry in matches],
        }
        return [types.TextContent(type="text", text=serialize_for_llm(payload))]
    except Exception as e:
        log.error(f"Error in opendata-find-providers: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-find-providers",
        description="Search the opendata-mcp registry. Returns providers that match a free-text query and/or domain/region filters. Use this FIRST when you don't know which provider can answer a question.",
        inputSchema=FindProvidersParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-find-providers"] = handle_find_providers


###################
# list-domains
###################


class ListDomainsParams(BaseModel):
    """No parameters."""


async def handle_list_domains(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-list-domains tool call."""
    try:
        return [
            types.TextContent(
                type="text",
                text=serialize_for_llm({"domains": list_domains()}),
            )
        ]
    except Exception as e:
        log.error(f"Error in opendata-list-domains: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-list-domains",
        description="List the controlled domain vocabulary used by the provider registry (e.g. 'health', 'legal', 'finance', 'earth-science').",
        inputSchema=ListDomainsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-list-domains"] = handle_list_domains


###################
# list-regions
###################


class ListRegionsParams(BaseModel):
    """No parameters."""


async def handle_list_regions(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-list-regions tool call."""
    try:
        return [
            types.TextContent(
                type="text",
                text=serialize_for_llm({"regions": list_regions()}),
            )
        ]
    except Exception as e:
        log.error(f"Error in opendata-list-regions: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-list-regions",
        description="List the controlled region vocabulary used by the provider registry (e.g. 'us', 'eu', 'uk', 'global').",
        inputSchema=ListRegionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-list-regions"] = handle_list_regions


###################
# describe-provider
###################


class DescribeProviderParams(BaseModel):
    """Lookup a single registry entry by provider id."""

    provider_id: str = Field(
        ...,
        description="The provider id (e.g. 'us_nasa', 'global_world_bank', 'us_courtlistener').",
    )


async def handle_describe_provider(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-describe-provider tool call."""
    try:
        if not arguments or "provider_id" not in arguments:
            raise ValueError("provider_id is required")
        params = DescribeProviderParams(**arguments)
        entry = get_provider(params.provider_id)
        if entry is None:
            payload = {"error": f"Provider '{params.provider_id}' not found"}
        else:
            payload = entry.to_dict()
        return [types.TextContent(type="text", text=serialize_for_llm(payload))]
    except Exception as e:
        log.error(f"Error in opendata-describe-provider: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-describe-provider",
        description="Fetch the full registry entry for a single provider id — title, description, domains, regions, keywords, homepage, license note, required environment variables.",
        inputSchema=DescribeProviderParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-describe-provider"] = handle_describe_provider


###################
# list-providers
###################


class ListProvidersParams(BaseModel):
    """Pagination over the full registry."""

    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of entries to return (1-200, default 50).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of entries to skip (default 0).",
    )


async def handle_list_providers(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-list-providers tool call."""
    try:
        params = ListProvidersParams(**(arguments or {}))
        slice_ = REGISTRY[params.offset : params.offset + params.limit]
        payload = {
            "total": len(REGISTRY),
            "offset": params.offset,
            "limit": params.limit,
            "providers": [
                {
                    "id": entry.id,
                    "title": entry.title,
                    "domains": list(entry.domains),
                    "regions": list(entry.regions),
                    "requires_env": list(entry.requires_env),
                }
                for entry in slice_
            ],
        }
        return [types.TextContent(type="text", text=serialize_for_llm(payload))]
    except Exception as e:
        log.error(f"Error in opendata-list-providers: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-list-providers",
        description="Enumerate all providers in the opendata-mcp registry (paginated, terse). Returns id, title, domains, regions, and any required env vars per provider.",
        inputSchema=ListProvidersParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-list-providers"] = handle_list_providers


async def main():
    from mcp.server.stdio import stdio_server
    from opendata_mcp.utils import create_mcp_server

    server = create_mcp_server(
        "opendata-mcp-meta", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
