"""
European Central Bank Data Portal Provider

This module exposes the European Central Bank's SDMX 2.1 REST API (the
ECB Data Portal). Data is requested in SDMX-JSON (`format=jsondata`) so
responses are JSON-shaped, although consumers still need to understand
SDMX-style series keys (dotted dimension values like 'D.USD.EUR.SP00.A').

License / source:
    ECB statistical data is generally available for re-use under the
    European Central Bank's general terms of use. Always confirm the
    licence on individual dataflows.

Features:
- List all ECB dataflows (datasets)
- Get the metadata for a single dataflow
- Pull observations for a dataflow + key
- Inspect codelists (controlled value lists)
- Inspect concept schemes (definitions of dimensions/attributes)

Usage:
    The module can be run directly to start an MCP server handling these
    tools, or its components can be imported individually.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://data-api.ecb.europa.eu/service"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# List dataflows
###################


class ECBListDataflowsParams(BaseModel):
    """Parameters for listing all ECB dataflows (no inputs)."""


def fetch_ecb_list_dataflows(_: ECBListDataflowsParams) -> dict:
    """Fetch every ECB dataflow definition."""
    query_params: dict[str, Any] = {"format": "jsondata"}
    response = http_get(f"{BASE_URL}/dataflow/ECB/all/latest", params=query_params)
    return response.json()


async def handle_ecb_list_dataflows(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ecb-list-dataflows tool call."""
    try:
        params = ECBListDataflowsParams(**(arguments or {}))
        data = fetch_ecb_list_dataflows(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error listing ECB dataflows: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ecb-list-dataflows",
        description="List every ECB SDMX dataflow (dataset) available on the ECB Data Portal.",
        inputSchema=ECBListDataflowsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ecb-list-dataflows"] = handle_ecb_list_dataflows


###################
# Get dataflow
###################


class ECBGetDataflowParams(BaseModel):
    """Parameters for fetching a single dataflow's metadata."""

    id: str = Field(..., description="Dataflow ID (e.g. 'EXR' for exchange rates).")


def fetch_ecb_get_dataflow(params: ECBGetDataflowParams) -> dict:
    """Fetch metadata for a single ECB dataflow."""
    query_params: dict[str, Any] = {"format": "jsondata"}
    response = http_get(
        f"{BASE_URL}/dataflow/ECB/{params.id}/latest", params=query_params
    )
    return response.json()


async def handle_ecb_get_dataflow(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ecb-get-dataflow tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = ECBGetDataflowParams(**arguments)
        data = fetch_ecb_get_dataflow(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ECB dataflow {arguments}: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ecb-get-dataflow",
        description="Get metadata for a single ECB dataflow by ID (e.g. 'EXR').",
        inputSchema=ECBGetDataflowParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ecb-get-dataflow"] = handle_ecb_get_dataflow


###################
# Get data
###################


class ECBGetDataParams(BaseModel):
    """Parameters for pulling observations from a dataflow."""

    flow: str = Field(..., description="Dataflow ID (e.g. 'EXR').")
    key: str = Field(
        ...,
        description=(
            "Dotted SDMX series key (e.g. 'D.USD.EUR.SP00.A' for daily "
            "USD/EUR reference rates). Use 'all' to fetch the whole flow."
        ),
    )
    startPeriod: Optional[str] = Field(
        default=None,
        description="Inclusive start period (e.g. '2024-01-01' or '2024-Q1').",
    )
    endPeriod: Optional[str] = Field(
        default=None,
        description="Inclusive end period.",
    )
    lastNObservations: Optional[int] = Field(
        default=None,
        ge=1,
        description="If set, return only the last N observations (mutually exclusive with period filters).",
    )


def fetch_ecb_get_data(params: ECBGetDataParams) -> dict:
    """Fetch observations from an ECB dataflow."""
    query_params: dict[str, Any] = {"format": "jsondata"}
    if params.startPeriod:
        query_params["startPeriod"] = params.startPeriod
    if params.endPeriod:
        query_params["endPeriod"] = params.endPeriod
    if params.lastNObservations:
        query_params["lastNObservations"] = params.lastNObservations
    response = http_get(
        f"{BASE_URL}/data/{params.flow}/{params.key}", params=query_params
    )
    return response.json()


async def handle_ecb_get_data(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ecb-get-data tool call."""
    try:
        if not arguments or "flow" not in arguments or "key" not in arguments:
            raise ValueError("flow and key are required")
        params = ECBGetDataParams(**arguments)
        data = fetch_ecb_get_data(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ECB data: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ecb-get-data",
        description=(
            "Fetch observations from an ECB dataflow. Example: flow='EXR', "
            "key='D.USD.EUR.SP00.A' for daily USD/EUR reference rate."
        ),
        inputSchema=ECBGetDataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ecb-get-data"] = handle_ecb_get_data


###################
# Get codelist
###################


class ECBGetCodelistParams(BaseModel):
    """Parameters for fetching a codelist."""

    id: str = Field(..., description="Codelist ID (e.g. 'CL_CURRENCY').")


def fetch_ecb_get_codelist(params: ECBGetCodelistParams) -> dict:
    """Fetch an ECB codelist."""
    query_params: dict[str, Any] = {"format": "jsondata"}
    response = http_get(
        f"{BASE_URL}/codelist/ECB/{params.id}/latest", params=query_params
    )
    return response.json()


async def handle_ecb_get_codelist(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ecb-get-codelist tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = ECBGetCodelistParams(**arguments)
        data = fetch_ecb_get_codelist(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ECB codelist: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ecb-get-codelist",
        description="Get the values that make up an ECB SDMX codelist (e.g. 'CL_CURRENCY').",
        inputSchema=ECBGetCodelistParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ecb-get-codelist"] = handle_ecb_get_codelist


###################
# Get conceptscheme
###################


class ECBGetConceptSchemeParams(BaseModel):
    """Parameters for fetching a concept scheme."""

    id: str = Field(..., description="Concept scheme ID (e.g. 'ECB_CONCEPTS').")


def fetch_ecb_get_conceptscheme(params: ECBGetConceptSchemeParams) -> dict:
    """Fetch an ECB concept scheme."""
    query_params: dict[str, Any] = {"format": "jsondata"}
    response = http_get(
        f"{BASE_URL}/conceptscheme/ECB/{params.id}/latest", params=query_params
    )
    return response.json()


async def handle_ecb_get_conceptscheme(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the ecb-get-conceptscheme tool call."""
    try:
        if not arguments or "id" not in arguments:
            raise ValueError("id is required")
        params = ECBGetConceptSchemeParams(**arguments)
        data = fetch_ecb_get_conceptscheme(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching ECB concept scheme: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="ecb-get-conceptscheme",
        description="Get an ECB SDMX concept scheme (definitions of dimensions and attributes).",
        inputSchema=ECBGetConceptSchemeParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["ecb-get-conceptscheme"] = handle_ecb_get_conceptscheme


async def main():
    from mcp.server.stdio import stdio_server
    from opendata_mcp.utils import create_mcp_server

    # create the server
    server = create_mcp_server(
        "eu-ecb", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    # run the server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
