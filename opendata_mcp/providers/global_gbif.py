"""
Global Biodiversity Information Facility (GBIF) Provider

This module exposes the public GBIF v1 REST API, which aggregates species
occurrence records, taxonomic backbone data, and dataset metadata from
contributors worldwide.

License note:
    GBIF metadata is released under the GBIF Terms of Use; underlying
    occurrence records carry licences supplied by the publishing dataset
    (commonly CC0, CC BY, or CC BY-NC). Always honour the licence reported
    on the individual record before redistribution.

Features:
- Occurrence search and detail
- Species search, detail, and name suggestion
- Dataset listing and detail
- Country-level occurrence counts

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
BASE_URL = "https://api.gbif.org/v1"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Search Occurrences
###################


class GBIFSearchOccurrencesParams(BaseModel):
    """Parameters for searching GBIF occurrence records."""

    scientificName: Optional[str] = Field(
        None, description="Scientific name to match (e.g. 'Puma concolor')."
    )
    country: Optional[str] = Field(
        None, description="ISO 3166-1 alpha-2 country code (e.g. 'US')."
    )
    year: Optional[int] = Field(None, description="Filter by collection year.")
    hasCoordinate: Optional[bool] = Field(
        None, description="If true, only records with lat/lon."
    )
    limit: int = Field(default=20, ge=1, le=300, description="Page size.")
    offset: int = Field(default=0, ge=0, description="Offset into the result set.")


def fetch_gbif_search_occurrences(params: GBIFSearchOccurrencesParams) -> dict:
    """Call /occurrence/search."""
    query_params: dict[str, Any] = {"limit": params.limit, "offset": params.offset}
    if params.scientificName:
        query_params["scientificName"] = params.scientificName
    if params.country:
        query_params["country"] = params.country
    if params.year is not None:
        query_params["year"] = params.year
    if params.hasCoordinate is not None:
        query_params["hasCoordinate"] = str(params.hasCoordinate).lower()
    response = http_get(f"{BASE_URL}/occurrence/search", params=query_params)
    return response.json()


async def handle_gbif_search_occurrences(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the gbif-search-occurrences tool call."""
    try:
        params = GBIFSearchOccurrencesParams(**(arguments or {}))
        data = fetch_gbif_search_occurrences(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching GBIF occurrences: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="gbif-search-occurrences",
        description="Search GBIF occurrence records by scientific name, country, year, and coordinate flag.",
        inputSchema=GBIFSearchOccurrencesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["gbif-search-occurrences"] = handle_gbif_search_occurrences


###################
# Get Occurrence
###################


class GBIFGetOccurrenceParams(BaseModel):
    """Parameters for retrieving a single occurrence record."""

    key: int = Field(..., description="GBIF occurrence integer key.")


def fetch_gbif_get_occurrence(params: GBIFGetOccurrenceParams) -> dict:
    """Call /occurrence/{key}."""
    response = http_get(f"{BASE_URL}/occurrence/{params.key}")
    return response.json()


async def handle_gbif_get_occurrence(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the gbif-get-occurrence tool call."""
    try:
        if not arguments or "key" not in arguments:
            raise ValueError("key is required")
        params = GBIFGetOccurrenceParams(**arguments)
        data = fetch_gbif_get_occurrence(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching GBIF occurrence: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="gbif-get-occurrence",
        description="Fetch a single GBIF occurrence record by integer key.",
        inputSchema=GBIFGetOccurrenceParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["gbif-get-occurrence"] = handle_gbif_get_occurrence


###################
# Search Species
###################


class GBIFSearchSpeciesParams(BaseModel):
    """Parameters for searching the GBIF species backbone."""

    q: str = Field(..., description="Free-text query (e.g. 'Quercus').")
    rank: Optional[str] = Field(
        None,
        description="Restrict to a taxonomic rank (kingdom, phylum, class, order, family, genus, species).",
    )
    limit: int = Field(default=20, ge=1, le=100, description="Page size.")


def fetch_gbif_search_species(params: GBIFSearchSpeciesParams) -> dict:
    """Call /species/search."""
    query_params: dict[str, Any] = {"q": params.q, "limit": params.limit}
    if params.rank:
        query_params["rank"] = params.rank
    response = http_get(f"{BASE_URL}/species/search", params=query_params)
    return response.json()


async def handle_gbif_search_species(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the gbif-search-species tool call."""
    try:
        if not arguments or "q" not in arguments:
            raise ValueError("q is required")
        params = GBIFSearchSpeciesParams(**arguments)
        data = fetch_gbif_search_species(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error searching GBIF species: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="gbif-search-species",
        description="Search the GBIF species backbone by free-text query and optional rank.",
        inputSchema=GBIFSearchSpeciesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["gbif-search-species"] = handle_gbif_search_species


###################
# Get Species
###################


class GBIFGetSpeciesParams(BaseModel):
    """Parameters for retrieving a single species record."""

    key: int = Field(..., description="GBIF taxon key.")


def fetch_gbif_get_species(params: GBIFGetSpeciesParams) -> dict:
    """Call /species/{key}."""
    response = http_get(f"{BASE_URL}/species/{params.key}")
    return response.json()


async def handle_gbif_get_species(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the gbif-get-species tool call."""
    try:
        if not arguments or "key" not in arguments:
            raise ValueError("key is required")
        params = GBIFGetSpeciesParams(**arguments)
        data = fetch_gbif_get_species(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching GBIF species: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="gbif-get-species",
        description="Fetch a single GBIF species/taxon record by taxon key.",
        inputSchema=GBIFGetSpeciesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["gbif-get-species"] = handle_gbif_get_species


###################
# Species Name Suggest
###################


class GBIFSpeciesSuggestParams(BaseModel):
    """Parameters for the species name autocomplete endpoint."""

    q: str = Field(..., description="Partial scientific name to autocomplete.")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum suggestions.")


def fetch_gbif_species_suggest(params: GBIFSpeciesSuggestParams) -> Any:
    """Call /species/suggest."""
    query_params: dict[str, Any] = {"q": params.q, "limit": params.limit}
    response = http_get(f"{BASE_URL}/species/suggest", params=query_params)
    return response.json()


async def handle_gbif_get_species_name_suggest(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the gbif-get-species-name-suggest tool call."""
    try:
        if not arguments or "q" not in arguments:
            raise ValueError("q is required")
        params = GBIFSpeciesSuggestParams(**arguments)
        data = fetch_gbif_species_suggest(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error suggesting GBIF species names: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="gbif-get-species-name-suggest",
        description="Autocomplete scientific names against the GBIF species backbone.",
        inputSchema=GBIFSpeciesSuggestParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["gbif-get-species-name-suggest"] = handle_gbif_get_species_name_suggest


###################
# List Datasets
###################


class GBIFListDatasetsParams(BaseModel):
    """Parameters for listing GBIF datasets."""

    type: Optional[str] = Field(
        None,
        description="Dataset type (OCCURRENCE, CHECKLIST, METADATA, SAMPLING_EVENT).",
    )
    country: Optional[str] = Field(
        None, description="ISO 3166-1 alpha-2 country code filter."
    )
    limit: int = Field(default=20, ge=1, le=1000, description="Page size.")
    offset: int = Field(default=0, ge=0, description="Offset into the result set.")


def fetch_gbif_list_datasets(params: GBIFListDatasetsParams) -> dict:
    """Call /dataset."""
    query_params: dict[str, Any] = {"limit": params.limit, "offset": params.offset}
    if params.type:
        query_params["type"] = params.type
    if params.country:
        query_params["country"] = params.country
    response = http_get(f"{BASE_URL}/dataset", params=query_params)
    return response.json()


async def handle_gbif_list_datasets(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the gbif-list-datasets tool call."""
    try:
        params = GBIFListDatasetsParams(**(arguments or {}))
        data = fetch_gbif_list_datasets(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing GBIF datasets: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="gbif-list-datasets",
        description="List GBIF datasets with optional type and country filters.",
        inputSchema=GBIFListDatasetsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["gbif-list-datasets"] = handle_gbif_list_datasets


###################
# Get Dataset
###################


class GBIFGetDatasetParams(BaseModel):
    """Parameters for fetching a single dataset record."""

    key: str = Field(..., description="GBIF dataset UUID key.")


def fetch_gbif_get_dataset(params: GBIFGetDatasetParams) -> dict:
    """Call /dataset/{key}."""
    response = http_get(f"{BASE_URL}/dataset/{params.key}")
    return response.json()


async def handle_gbif_get_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the gbif-get-dataset tool call."""
    try:
        if not arguments or "key" not in arguments:
            raise ValueError("key is required")
        params = GBIFGetDatasetParams(**arguments)
        data = fetch_gbif_get_dataset(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching GBIF dataset: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="gbif-get-dataset",
        description="Fetch a single GBIF dataset record by UUID key.",
        inputSchema=GBIFGetDatasetParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["gbif-get-dataset"] = handle_gbif_get_dataset


###################
# Occurrence Counts
###################


class GBIFOccurrenceCountsParams(BaseModel):
    """Parameters for the country occurrence-counts endpoint."""

    country: Optional[str] = Field(
        None, description="ISO 3166-1 alpha-2 country code filter."
    )


def fetch_gbif_occurrence_counts(params: GBIFOccurrenceCountsParams) -> Any:
    """Call /occurrence/counts."""
    query_params: dict[str, Any] = {}
    if params.country:
        query_params["country"] = params.country
    response = http_get(f"{BASE_URL}/occurrence/counts", params=query_params)
    return response.json()


async def handle_gbif_get_occurrence_counts(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the gbif-get-occurrence-counts tool call."""
    try:
        params = GBIFOccurrenceCountsParams(**(arguments or {}))
        data = fetch_gbif_occurrence_counts(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching GBIF occurrence counts: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="gbif-get-occurrence-counts",
        description="Get aggregate GBIF occurrence counts, optionally filtered by country.",
        inputSchema=GBIFOccurrenceCountsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["gbif-get-occurrence-counts"] = handle_gbif_get_occurrence_counts


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-gbif", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
