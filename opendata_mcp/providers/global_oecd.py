"""
OECD SDMX Provider

This module provides interfaces to the OECD public SDMX REST API, exposing
economic, social, and environmental statistics for OECD and partner countries.

License: Most OECD data is published under the OECD Terms and Conditions
(https://www.oecd.org/termsandconditions/). Many series are freely
redistributable; check the dataflow metadata for specific terms.

Features:
- Dataflow discovery (list/get)
- Data-structure (DSD) retrieval
- Time-series data retrieval (SDMX-JSON)
- Codelist and conceptscheme metadata
- No API key required

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://sdmx.oecd.org/public/rest"
SDMX_DATA_ACCEPT = "application/vnd.sdmx.data+json;version=1.0.0"
SDMX_STRUCT_ACCEPT = "application/vnd.sdmx.structure+json;version=1.0.0"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# List Dataflows
###################


class OECDListDataflowsParams(BaseModel):
    """Parameters for listing OECD dataflows."""

    pass


def fetch_list_dataflows(_params: OECDListDataflowsParams) -> dict:
    """Fetch the catalogue of OECD dataflows."""
    response = http_get(
        f"{BASE_URL}/dataflow/all/all/latest",
        params={"format": "jsonobject"},
        timeout=60.0,
        headers={"Accept": SDMX_STRUCT_ACCEPT},
    )
    return response.json()


async def handle_list_dataflows(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the oecd-list-dataflows tool call."""
    try:
        params = OECDListDataflowsParams(**(arguments or {}))
        data = fetch_list_dataflows(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error listing OECD dataflows: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="oecd-list-dataflows",
        description="List all available OECD SDMX dataflows.",
        inputSchema=OECDListDataflowsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["oecd-list-dataflows"] = handle_list_dataflows


###################
# Get Dataflow
###################


class OECDGetDataflowParams(BaseModel):
    """Parameters for fetching a single OECD dataflow."""

    agencyId: str = Field(..., description="Agency ID (e.g. 'OECD.SDD.NAD')")
    flowId: str = Field(
        ..., description="Dataflow ID (e.g. 'DSD_NAMAIN1@DF_QNA_EXPENDITURE')"
    )


def fetch_get_dataflow(params: OECDGetDataflowParams) -> dict:
    """Fetch a single OECD dataflow descriptor."""
    response = http_get(
        f"{BASE_URL}/dataflow/{params.agencyId}/{params.flowId}/latest",
        params={"format": "jsonobject"},
        timeout=60.0,
        headers={"Accept": SDMX_STRUCT_ACCEPT},
    )
    return response.json()


async def handle_get_dataflow(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the oecd-get-dataflow tool call."""
    try:
        if not arguments or "agencyId" not in arguments or "flowId" not in arguments:
            raise ValueError("agencyId and flowId are required")
        params = OECDGetDataflowParams(**arguments)
        data = fetch_get_dataflow(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OECD dataflow: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="oecd-get-dataflow",
        description="Get metadata for a single OECD dataflow.",
        inputSchema=OECDGetDataflowParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["oecd-get-dataflow"] = handle_get_dataflow


###################
# Get Data Structure
###################


class OECDGetDataStructureParams(BaseModel):
    """Parameters for fetching an OECD data-structure definition (DSD)."""

    agencyId: str = Field(..., description="Agency ID (e.g. 'OECD.SDD.NAD')")
    structureId: str = Field(..., description="Data-structure ID (e.g. 'DSD_NAMAIN1')")


def fetch_get_datastructure(params: OECDGetDataStructureParams) -> dict:
    """Fetch an OECD data-structure definition."""
    response = http_get(
        f"{BASE_URL}/datastructure/{params.agencyId}/{params.structureId}",
        params={"format": "jsonobject"},
        timeout=60.0,
        headers={"Accept": SDMX_STRUCT_ACCEPT},
    )
    return response.json()


async def handle_get_datastructure(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the oecd-get-datastructure tool call."""
    try:
        if (
            not arguments
            or "agencyId" not in arguments
            or "structureId" not in arguments
        ):
            raise ValueError("agencyId and structureId are required")
        params = OECDGetDataStructureParams(**arguments)
        data = fetch_get_datastructure(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OECD data-structure: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="oecd-get-datastructure",
        description="Get an OECD data-structure definition (DSD) describing dimensions and attributes.",
        inputSchema=OECDGetDataStructureParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["oecd-get-datastructure"] = handle_get_datastructure


###################
# Get Data
###################


class OECDGetDataParams(BaseModel):
    """Parameters for fetching OECD SDMX time-series data."""

    agencyId: str = Field(..., description="Agency ID (e.g. 'OECD.SDD.NAD')")
    flowId: str = Field(..., description="Dataflow ID")
    version: str = Field(default="1.0", description="Dataflow version (e.g. '1.0')")
    key: str = Field(
        default="all",
        description="SDMX series key with dimension values separated by dots, or 'all'",
    )
    startPeriod: Optional[str] = Field(
        None, description="Start period (e.g. '2010' or '2010-Q1')"
    )
    endPeriod: Optional[str] = Field(
        None, description="End period (e.g. '2020' or '2020-Q4')"
    )


def fetch_get_data(params: OECDGetDataParams) -> dict:
    """Fetch OECD SDMX time-series data."""
    query_params: dict[str, Any] = {"format": "jsondata"}
    if params.startPeriod is not None:
        query_params["startPeriod"] = params.startPeriod
    if params.endPeriod is not None:
        query_params["endPeriod"] = params.endPeriod

    url = (
        f"{BASE_URL}/data/"
        f"{params.agencyId},{params.flowId},{params.version}/{params.key}"
    )
    response = http_get(
        url,
        params=query_params,
        timeout=60.0,
        headers={"Accept": SDMX_DATA_ACCEPT},
    )
    return response.json()


async def handle_get_data(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the oecd-get-data tool call."""
    try:
        if not arguments or "agencyId" not in arguments or "flowId" not in arguments:
            raise ValueError("agencyId and flowId are required")
        params = OECDGetDataParams(**arguments)
        data = fetch_get_data(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OECD data: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="oecd-get-data",
        description="Fetch OECD SDMX time-series data for a dataflow and series key.",
        inputSchema=OECDGetDataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["oecd-get-data"] = handle_get_data


###################
# List Codelist
###################


class OECDListCodelistParams(BaseModel):
    """Parameters for fetching an OECD codelist."""

    agencyId: str = Field(..., description="Agency ID (e.g. 'OECD.SDD.NAD')")
    codelistId: str = Field(..., description="Codelist ID (e.g. 'CL_AREA')")
    version: str = Field(default="1.0", description="Codelist version")


def fetch_list_codelist(params: OECDListCodelistParams) -> dict:
    """Fetch a codelist from the OECD SDMX API."""
    response = http_get(
        f"{BASE_URL}/codelist/{params.agencyId}/{params.codelistId}/{params.version}",
        params={"format": "jsonobject"},
        timeout=60.0,
        headers={"Accept": SDMX_STRUCT_ACCEPT},
    )
    return response.json()


async def handle_list_codelist(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the oecd-list-codelist tool call."""
    try:
        if (
            not arguments
            or "agencyId" not in arguments
            or "codelistId" not in arguments
        ):
            raise ValueError("agencyId and codelistId are required")
        params = OECDListCodelistParams(**arguments)
        data = fetch_list_codelist(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OECD codelist: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="oecd-list-codelist",
        description="Fetch a codelist (controlled vocabulary) from the OECD SDMX API.",
        inputSchema=OECDListCodelistParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["oecd-list-codelist"] = handle_list_codelist


###################
# List Concept Scheme
###################


class OECDListConceptSchemeParams(BaseModel):
    """Parameters for fetching an OECD concept scheme."""

    agencyId: str = Field(..., description="Agency ID (e.g. 'OECD.SDD.NAD')")
    schemeId: str = Field(..., description="Concept scheme ID")
    version: str = Field(default="1.0", description="Concept scheme version")


def fetch_list_conceptscheme(params: OECDListConceptSchemeParams) -> dict:
    """Fetch a concept scheme from the OECD SDMX API."""
    response = http_get(
        f"{BASE_URL}/conceptscheme/{params.agencyId}/{params.schemeId}/{params.version}",
        params={"format": "jsonobject"},
        timeout=60.0,
        headers={"Accept": SDMX_STRUCT_ACCEPT},
    )
    return response.json()


async def handle_list_conceptscheme(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the oecd-list-conceptscheme tool call."""
    try:
        if not arguments or "agencyId" not in arguments or "schemeId" not in arguments:
            raise ValueError("agencyId and schemeId are required")
        params = OECDListConceptSchemeParams(**arguments)
        data = fetch_list_conceptscheme(params)
        return [types.TextContent(type="text", text=str(data)[:20000])]
    except Exception as e:
        log.error(f"Error fetching OECD concept scheme: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="oecd-list-conceptscheme",
        description="Fetch a concept scheme from the OECD SDMX API.",
        inputSchema=OECDListConceptSchemeParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["oecd-list-conceptscheme"] = handle_list_conceptscheme


async def main():
    from mcp.server.stdio import stdio_server

    from opendata_mcp.utils import create_mcp_server

    server = create_mcp_server(
        "global-oecd", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
