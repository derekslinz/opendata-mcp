"""
UNESCO Institute for Statistics (UIS) Provider

This module exposes the UNESCO UIS SDMX API, which provides access to global
statistics on education, science, technology, culture, and communication.

License / source:
    Data is provided by UNESCO under the CC BY-SA 3.0 IGO license.
    Consult https://uis.unesco.org/en/licensing for attribution requirements.

Authentication:
    A subscription key is required for the SDMX API.
    Register for a free key at https://api.uis.unesco.org/ and set the
    ``UNESCO_UIS_SUBSCRIPTION_KEY`` environment variable.  When present it is
    sent as the ``Ocp-Apim-Subscription-Key`` header.

Features:
- List available dataflows (datasets) from the UIS SDMX API
- Fetch data for a specific dataflow and dimension key
- Get codelist values for a dimension (e.g. country codes, indicators)

Usage:
    The module can be run directly to start an MCP server, or its components
    can be imported individually.
"""

import logging
import os
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

log = logging.getLogger(__name__)

BASE_URL = "https://api.uis.unesco.org/sdmx"

RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _auth_headers() -> dict[str, str]:
    """Return the Ocp-Apim-Subscription-Key header if the env var is set."""
    key = os.getenv("UNESCO_UIS_SUBSCRIPTION_KEY")
    if key:
        return {"Ocp-Apim-Subscription-Key": key}
    return {}


###################
# List Dataflows
###################


class UNESCOUISListDataflowsParams(BaseModel):
    """Parameters for listing UIS SDMX dataflows."""

    agencyID: str = Field(
        default="UNESCO",
        description="Agency identifier (default 'UNESCO').",
    )


def fetch_unesco_uis_list_dataflows(params: UNESCOUISListDataflowsParams) -> dict:
    """Fetch the list of SDMX dataflows from UNESCO UIS."""
    response = http_get(
        f"{BASE_URL}/dataflow/{params.agencyID}",
        headers={**_auth_headers(), "Accept": "application/json"},
    )
    return response.json()


async def handle_unesco_uis_list_dataflows(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the unesco-uis-list-dataflows tool call."""
    try:
        params = UNESCOUISListDataflowsParams(**(arguments or {}))
        data = fetch_unesco_uis_list_dataflows(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error listing UNESCO UIS dataflows: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="unesco-uis-list-dataflows",
        description=(
            "List all available UNESCO UIS SDMX dataflows (datasets) covering education, "
            "science, culture, and communication statistics."
        ),
        inputSchema=UNESCOUISListDataflowsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["unesco-uis-list-dataflows"] = handle_unesco_uis_list_dataflows


###################
# Get Data
###################


class UNESCOUISGetDataParams(BaseModel):
    """Parameters for fetching data from a UNESCO UIS SDMX dataflow."""

    dataflow_id: str = Field(
        ...,
        description=(
            "The SDMX dataflow ID (e.g. 'UNESCO,SDG4,1.0'). "
            "Use unesco-uis-list-dataflows to discover available dataflows."
        ),
    )
    key: str = Field(
        default="all",
        description=(
            "SDMX key selecting specific dimension values. Use 'all' to retrieve all data, "
            "or specify values like 'AFG.TRTENRL._T._T._T.INST_T' to narrow results."
        ),
    )
    startPeriod: Optional[str] = Field(
        None,
        description="Start of the time range (e.g. '2015' or '2015-Q1').",
    )
    endPeriod: Optional[str] = Field(
        None,
        description="End of the time range (e.g. '2023' or '2023-Q4').",
    )


def fetch_unesco_uis_data(params: UNESCOUISGetDataParams) -> dict:
    """Fetch SDMX data from UNESCO UIS."""
    query_params: dict[str, Any] = {"format": "jsondata"}
    if params.startPeriod:
        query_params["startPeriod"] = params.startPeriod
    if params.endPeriod:
        query_params["endPeriod"] = params.endPeriod
    response = http_get(
        f"{BASE_URL}/data/{params.dataflow_id}/{params.key}",
        params=query_params,
        headers={**_auth_headers(), "Accept": "application/json"},
        timeout=30.0,
    )
    return response.json()


async def handle_unesco_uis_get_data(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the unesco-uis-get-data tool call."""
    try:
        if not arguments or "dataflow_id" not in arguments:
            raise ValueError("dataflow_id is required")
        params = UNESCOUISGetDataParams(**arguments)
        data = fetch_unesco_uis_data(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching UNESCO UIS data: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="unesco-uis-get-data",
        description=(
            "Fetch statistical data from a UNESCO UIS SDMX dataflow. "
            "Returns observations for education, science, and culture indicators by country and year."
        ),
        inputSchema=UNESCOUISGetDataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["unesco-uis-get-data"] = handle_unesco_uis_get_data


###################
# Get Codelist
###################


class UNESCOUISGetCodelistParams(BaseModel):
    """Parameters for fetching a UNESCO UIS SDMX codelist."""

    agencyID: str = Field(
        default="UNESCO",
        description="Agency identifier (default 'UNESCO').",
    )
    resourceID: str = Field(
        ...,
        description=(
            "Codelist resource ID (e.g. 'CL_AREA' for country/region codes, "
            "'CL_INDICATOR' for indicator codes)."
        ),
    )
    version: str = Field(
        default="latest",
        description="Codelist version (default 'latest').",
    )


def fetch_unesco_uis_codelist(params: UNESCOUISGetCodelistParams) -> dict:
    """Fetch a codelist from UNESCO UIS SDMX."""
    response = http_get(
        f"{BASE_URL}/codelist/{params.agencyID}/{params.resourceID}/{params.version}",
        headers={**_auth_headers(), "Accept": "application/json"},
    )
    return response.json()


async def handle_unesco_uis_get_codelist(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the unesco-uis-get-codelist tool call."""
    try:
        if not arguments or "resourceID" not in arguments:
            raise ValueError("resourceID is required")
        params = UNESCOUISGetCodelistParams(**arguments)
        data = fetch_unesco_uis_codelist(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching UNESCO UIS codelist: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="unesco-uis-get-codelist",
        description=(
            "Fetch a UNESCO UIS SDMX codelist — dimension values such as country codes "
            "('CL_AREA') or indicator codes ('CL_INDICATOR')."
        ),
        inputSchema=UNESCOUISGetCodelistParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["unesco-uis-get-codelist"] = handle_unesco_uis_get_codelist


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-unesco-uis", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
