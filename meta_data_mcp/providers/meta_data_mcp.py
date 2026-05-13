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
from pydantic import AnyUrl, BaseModel, Field

from meta_data_mcp.utils import serialize_for_llm

from meta_data_mcp.registry import (
    REGISTRY,
    get_provider,
    list_domains,
    list_regions,
)
from meta_data_mcp.routing import RoutingEngine

log = logging.getLogger(__name__)

# Module-level singleton — cache survives across tool calls within the same server process.
_engine = RoutingEngine()

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
    """Handle the opendata-find-providers tool call.

    Uses sophisticated multi-criteria routing for intelligent provider ranking.
    Falls back to original token-based search if needed.
    """
    try:
        params = FindProvidersParams(**(arguments or {}))

        scored_results = await _engine.route(
            query=params.query,
            domain=params.domain,
            region=params.region,
            limit=params.limit,
            explain=False,
        )

        # Extract entries for compatibility
        matches = [result.entry for result in scored_results]

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
# explain-choice
###################


class ExplainChoiceParams(BaseModel):
    """Parameters for explain-choice tool."""

    query: Optional[str] = Field(
        None,
        description="The original search query to explain scoring for.",
    )
    domain: Optional[str] = Field(
        None,
        description="Domain filter used in search.",
    )
    region: Optional[str] = Field(
        None,
        description="Region filter used in search.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top providers to explain (1-20, default 5).",
    )


async def handle_explain_choice(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Explain the scoring breakdown for a provider search query.

    Shows how each provider was ranked, including the contribution of
    token matching, fuzzy matching, semantic similarity, and metadata filters.
    """
    try:
        params = ExplainChoiceParams(**(arguments or {}))

        scored_results = await _engine.route(
            query=params.query,
            domain=params.domain,
            region=params.region,
            limit=params.limit,
            explain=True,
        )

        # Format explanation
        explanations = []
        for i, result in enumerate(scored_results, 1):
            explanation = {
                "rank": i,
                "provider_id": result.entry.id,
                "provider_title": result.entry.title,
                "overall_score": round(result.score, 3),
                "scoring_breakdown": result.breakdown,
            }
            explanations.append(explanation)

        payload = {
            "query": params.query,
            "domain_filter": params.domain,
            "region_filter": params.region,
            "results": explanations,
        }

        return [types.TextContent(type="text", text=serialize_for_llm(payload))]
    except Exception as e:
        log.error(f"Error in opendata-explain-choice: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-explain-choice",
        description="Explain the scoring breakdown for a provider search. Shows how each provider was ranked using token matching, fuzzy matching, semantic similarity, and metadata filters.",
        inputSchema=ExplainChoiceParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-explain-choice"] = handle_explain_choice


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


###################
# Resources
###################

RESOURCES.append(
    types.Resource(
        uri="registry://all-providers",
        name="All OpenData Providers",
        description="A complete list of all currently registered OpenData MCP providers and their metadata.",
        mimeType="application/json",
    )
)


def handle_read_all_providers(uri: AnyUrl) -> str:
    payload = [entry.to_dict() for entry in REGISTRY]
    return serialize_for_llm(payload)


RESOURCES_HANDLERS["registry://all-providers"] = handle_read_all_providers

###################
# Prompts
###################

# Create a module-level variable for prompts
PROMPTS: List[types.Prompt] = []
PROMPTS_HANDLERS: dict[str, Any] = {}

PROMPTS.append(
    types.Prompt(
        name="discover-providers",
        description="Ask the LLM to analyze your needs and suggest the best OpenData MCP providers.",
        arguments=[
            types.PromptArgument(
                name="use_case",
                description="What are you trying to build? (e.g., 'a dashboard for weather and flights')",
                required=True,
            )
        ],
    )
)


async def handle_discover_providers(
    arguments: dict[str, str] | None,
) -> types.GetPromptResult:
    use_case = (arguments or {}).get("use_case", "General exploration")

    return types.GetPromptResult(
        description=f"Suggest providers for: {use_case}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"I want to build the following: {use_case}\n\nPlease use your `opendata-find-providers` tool to search the registry and recommend the 3 most relevant providers for my project. Explain why each one is a good fit and how I can use them together.",
                ),
            )
        ],
    )


PROMPTS_HANDLERS["discover-providers"] = handle_discover_providers

# Predefined Use Cases
USE_CASES = {
    "usecase-financial-research": {
        "title": "Financial & Economic Research",
        "description": "Analyze economic indicators, exchange rates, and financial markets.",
        "text": "I am building a financial research tool. Please suggest 3-5 providers from the registry that deal with economics, finance, exchange rates, or central banks (e.g., FRED, ECB, World Bank, DBnomics). Explain what data each provides and how they can be correlated.",
    },
    "usecase-climate-dashboard": {
        "title": "Climate & Environment Dashboard",
        "description": "Build tools to track weather, climate change, and environmental data.",
        "text": "I am building a climate and environment dashboard. Please suggest 3-5 providers from the registry that deal with weather, climate, emissions, or earth science (e.g., NOAA, Copernicus, OpenMeteo). Explain what data each provides and how to combine them for a comprehensive view.",
    },
    "usecase-healthcare-analytics": {
        "title": "Healthcare & Epidemiology Analytics",
        "description": "Track diseases, clinical trials, and public health data.",
        "text": "I am building a healthcare analytics platform. Please suggest 3-5 providers from the registry that deal with public health, epidemiology, or clinical trials (e.g., CDC, FDA, WHO, Disease.sh). Explain what datasets they offer and how they might be used together.",
    },
    "usecase-academic-literature": {
        "title": "Academic Literature Review",
        "description": "Search for scholarly articles, preprints, and citations.",
        "text": "I am conducting an academic literature review. Please suggest 3-5 providers from the registry that offer access to scholarly publications, metadata, and citations (e.g., ArXiv, CrossRef, EuropePMC, OpenAlex). Explain how to use them together for a comprehensive literature search.",
    },
}

for prompt_id, case_info in USE_CASES.items():
    PROMPTS.append(
        types.Prompt(name=prompt_id, description=case_info["description"], arguments=[])
    )

    # Need a factory function to capture the correct text in the closure
    def make_handler(text: str, title: str):
        async def handler(arguments: dict[str, str] | None) -> types.GetPromptResult:
            return types.GetPromptResult(
                description=f"Recommendations for: {title}",
                messages=[
                    types.PromptMessage(
                        role="user", content=types.TextContent(type="text", text=text)
                    )
                ],
            )

        return handler

    PROMPTS_HANDLERS[prompt_id] = make_handler(case_info["text"], case_info["title"])


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "opendata-mcp-meta",
        resources=RESOURCES,
        resources_handlers=RESOURCES_HANDLERS,
        tools=TOOLS,
        tools_handlers=TOOLS_HANDLERS,
        prompts=PROMPTS,
        prompts_handlers=PROMPTS_HANDLERS,
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
