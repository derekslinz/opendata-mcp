"""global-opensanctions provider.

OpenSanctions — a database of persons and companies of political, criminal,
or economic interest, compiled from over 200 official sources: OFAC SDN,
UN consolidated sanctions, EU consolidated list, UK HMT, national PEP
lists, debarment registers, ICIJ disclosures, and more.

Homepage: https://www.opensanctions.org
API docs: https://www.opensanctions.org/docs/api/
License: Most data is CC-BY 4.0; the API is free for non-commercial
research use (cite "OpenSanctions"). Commercial use requires a license.
Auth: Anonymous public-API tier works; set ``OPENSANCTIONS_API_KEY`` env
var (sent as ``Authorization: ApiKey ...``) for higher rate limits and
the commercial-tier datasets.
"""

import logging
import os
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, ConfigDict, Field

from meta_data_mcp.utils import (
    create_mcp_server,
    http_get,
    run_server,
    serialize_for_llm,
)

log = logging.getLogger(__name__)

PROVIDER_ID = "global-opensanctions"
BASE_URL = "https://api.opensanctions.org"

RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _auth_headers() -> dict[str, str]:
    """Send Authorization when OPENSANCTIONS_API_KEY is set."""
    token = os.getenv("OPENSANCTIONS_API_KEY")
    if token:
        return {"Authorization": f"ApiKey {token}"}
    return {}


###################
# opensanctions-search
###################


class OpenSanctionsSearchParams(BaseModel):
    """Parameters for opensanctions-search."""

    query: str = Field(
        ...,
        min_length=1,
        description=(
            "Free-text query — a name, alias, organization, or vessel. "
            "OpenSanctions performs fuzzy matching including transliteration."
        ),
    )
    schema_: Optional[str] = Field(
        None,
        alias="schema",
        description=(
            "Entity schema filter — 'Person', 'Organization', 'Company', "
            "'Vessel', 'Aircraft', 'CryptoWallet', 'Address', 'Security'. "
            "Defaults to all schemas."
        ),
    )
    countries: Optional[str] = Field(
        None,
        description=(
            "ISO 3166-1 alpha-2 country code(s), comma-separated (e.g. "
            "'ru,by'). Filters to entities tagged with these countries."
        ),
    )
    topics: Optional[str] = Field(
        None,
        description=(
            "Topic filter — 'sanction', 'sanction.linked', 'role.pep', "
            "'crime.fin', 'corp.disqual', etc. Comma-separated to combine."
        ),
    )
    dataset: str = Field(
        default="default",
        description=(
            "Dataset slug — 'default' (recommended sanctions+PEP collection), "
            "'sanctions', 'peps', or a specific source slug like 'us_ofac_sdn'."
        ),
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return (1-100).",
    )

    model_config = ConfigDict(populate_by_name=True)


def fetch_opensanctions_search(params: OpenSanctionsSearchParams) -> Any:
    """Search OpenSanctions for matching entities."""
    query: dict[str, Any] = {"q": params.query, "limit": params.limit}
    if params.schema_ is not None:
        query["schema"] = params.schema_
    if params.countries is not None:
        query["countries"] = params.countries
    if params.topics is not None:
        query["topics"] = params.topics
    response = http_get(
        f"{BASE_URL}/search/{params.dataset}",
        params=query,
        headers=_auth_headers() or None,
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_opensanctions_search(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opensanctions-search tool call."""
    params = OpenSanctionsSearchParams(**(arguments or {}))
    data = fetch_opensanctions_search(params)
    return [types.TextContent(type="text", text=serialize_for_llm(data))]


TOOLS.append(
    types.Tool(
        name="opensanctions-search",
        description=(
            "Search OpenSanctions for persons, companies, vessels, or other "
            "entities that appear on official sanctions lists, PEP registers, "
            "or related risk databases. Supports fuzzy / transliterated name "
            "matching. Returns the entity's schema, topics, countries, and "
            "source references."
        ),
        inputSchema=OpenSanctionsSearchParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opensanctions-search"] = handle_opensanctions_search


###################
# opensanctions-get-entity
###################


class OpenSanctionsGetEntityParams(BaseModel):
    """Parameters for opensanctions-get-entity."""

    entity_id: str = Field(
        ...,
        min_length=1,
        description=(
            "OpenSanctions entity id (e.g. 'NK-aBcD123' or a 'Q-' Wikidata "
            "id). Returned in the 'id' field of a search result."
        ),
    )


def fetch_opensanctions_get_entity(params: OpenSanctionsGetEntityParams) -> Any:
    """Fetch full structured data for a single OpenSanctions entity."""
    response = http_get(
        f"{BASE_URL}/entities/{params.entity_id}",
        headers=_auth_headers() or None,
        provider=PROVIDER_ID,
    )
    return response.json()


async def handle_opensanctions_get_entity(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opensanctions-get-entity tool call."""
    params = OpenSanctionsGetEntityParams(**(arguments or {}))
    data = fetch_opensanctions_get_entity(params)
    return [types.TextContent(type="text", text=serialize_for_llm(data))]


TOOLS.append(
    types.Tool(
        name="opensanctions-get-entity",
        description=(
            "Fetch the full structured profile for a single OpenSanctions "
            "entity — properties, sources, related entities, and provenance."
        ),
        inputSchema=OpenSanctionsGetEntityParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opensanctions-get-entity"] = handle_opensanctions_get_entity


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    server = create_mcp_server(
        "global-opensanctions",
        RESOURCES,
        RESOURCES_HANDLERS,
        TOOLS,
        TOOLS_HANDLERS,
    )
    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
