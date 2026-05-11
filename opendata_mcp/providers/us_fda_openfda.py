"""
US openFDA Provider

This module provides interfaces to the openFDA API published by the US
Food and Drug Administration. openFDA exposes harmonized data on drugs,
medical devices, food, and animal/veterinary products covering adverse
events, recalls, and labeling.

License: openFDA data is in the public domain (US Government work) with
the caveats described at https://open.fda.gov/license/.

Environment variables:
- None strictly required. Applications may set an api_key query parameter
  to raise rate limits beyond the anonymous 240/min cap; this provider
  does not currently wire one in.

Features:
- Drug adverse events, labels, and enforcement (recalls)
- Device adverse events, recalls, and 510(k) clearances
- Food enforcement (recalls)
- Animal & Veterinary adverse events

All openFDA endpoints share the same query convention:
    ?search=<Lucene query>&limit=<n>&skip=<n>

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import http_get, serialize_for_llm

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.fda.gov"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


def _build_query(
    search: Optional[str], limit: int, skip: Optional[int] = None
) -> dict[str, Any]:
    """Build the standard openFDA query parameter dict."""
    query_params: dict[str, Any] = {"limit": limit}
    if search:
        query_params["search"] = search
    if skip is not None:
        query_params["skip"] = skip
    return query_params


###################
# Drug Events
###################


class OpenFDADrugEventsParams(BaseModel):
    """Parameters for openFDA drug adverse-event queries."""

    search: Optional[str] = Field(
        None,
        description="openFDA search query (Lucene-style, e.g. 'patient.drug.medicinalproduct:aspirin')",
    )
    limit: int = Field(default=10, description="Number of results to return (max 100)")
    skip: int = Field(default=0, description="Number of results to skip (pagination)")


def fetch_drug_events(params: OpenFDADrugEventsParams) -> Any:
    """Fetch drug adverse-event reports from openFDA."""
    query_params = _build_query(params.search, params.limit, params.skip)
    response = http_get(f"{BASE_URL}/drug/event.json", params=query_params)
    return response.json()


async def handle_drug_events(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openfda-drug-events tool call."""
    try:
        params = OpenFDADrugEventsParams(**(arguments or {}))
        data = fetch_drug_events(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching openFDA drug events: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openfda-drug-events",
        description="Query openFDA drug adverse-event reports (FAERS).",
        inputSchema=OpenFDADrugEventsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openfda-drug-events"] = handle_drug_events


###################
# Drug Labels
###################


class OpenFDADrugLabelsParams(BaseModel):
    """Parameters for openFDA drug labeling queries."""

    search: Optional[str] = Field(
        None, description="openFDA search query (e.g. 'openfda.brand_name:tylenol')"
    )
    limit: int = Field(default=10, description="Number of results to return (max 100)")


def fetch_drug_labels(params: OpenFDADrugLabelsParams) -> Any:
    """Fetch structured drug labeling from openFDA."""
    query_params = _build_query(params.search, params.limit)
    response = http_get(f"{BASE_URL}/drug/label.json", params=query_params)
    return response.json()


async def handle_drug_labels(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openfda-drug-labels tool call."""
    try:
        params = OpenFDADrugLabelsParams(**(arguments or {}))
        data = fetch_drug_labels(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching openFDA drug labels: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openfda-drug-labels",
        description="Query openFDA structured drug labeling.",
        inputSchema=OpenFDADrugLabelsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openfda-drug-labels"] = handle_drug_labels


###################
# Drug Enforcement
###################


class OpenFDADrugEnforcementParams(BaseModel):
    """Parameters for openFDA drug enforcement (recall) queries."""

    search: Optional[str] = Field(
        None, description="openFDA search query (e.g. 'classification:Class I')"
    )
    limit: int = Field(default=10, description="Number of results to return (max 100)")


def fetch_drug_enforcement(params: OpenFDADrugEnforcementParams) -> Any:
    """Fetch drug enforcement (recall) records from openFDA."""
    query_params = _build_query(params.search, params.limit)
    response = http_get(f"{BASE_URL}/drug/enforcement.json", params=query_params)
    return response.json()


async def handle_drug_enforcement(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openfda-drug-enforcement tool call."""
    try:
        params = OpenFDADrugEnforcementParams(**(arguments or {}))
        data = fetch_drug_enforcement(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching openFDA drug enforcement: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openfda-drug-enforcement",
        description="Query openFDA drug enforcement (recall) records.",
        inputSchema=OpenFDADrugEnforcementParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openfda-drug-enforcement"] = handle_drug_enforcement


###################
# Device Events
###################


class OpenFDADeviceEventsParams(BaseModel):
    """Parameters for openFDA device adverse-event queries."""

    search: Optional[str] = Field(
        None, description="openFDA search query (e.g. 'device.brand_name:pacemaker')"
    )
    limit: int = Field(default=10, description="Number of results to return (max 100)")


def fetch_device_events(params: OpenFDADeviceEventsParams) -> Any:
    """Fetch device adverse-event (MAUDE) reports from openFDA."""
    query_params = _build_query(params.search, params.limit)
    response = http_get(f"{BASE_URL}/device/event.json", params=query_params)
    return response.json()


async def handle_device_events(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openfda-device-events tool call."""
    try:
        params = OpenFDADeviceEventsParams(**(arguments or {}))
        data = fetch_device_events(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching openFDA device events: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openfda-device-events",
        description="Query openFDA medical-device adverse event reports (MAUDE).",
        inputSchema=OpenFDADeviceEventsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openfda-device-events"] = handle_device_events


###################
# Device Recalls
###################


class OpenFDADeviceRecallsParams(BaseModel):
    """Parameters for openFDA device recall queries."""

    search: Optional[str] = Field(
        None, description="openFDA search query (e.g. 'classification:Class I')"
    )
    limit: int = Field(default=10, description="Number of results to return (max 100)")


def fetch_device_recalls(params: OpenFDADeviceRecallsParams) -> Any:
    """Fetch device recall records from openFDA."""
    query_params = _build_query(params.search, params.limit)
    response = http_get(f"{BASE_URL}/device/recall.json", params=query_params)
    return response.json()


async def handle_device_recalls(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openfda-device-recalls tool call."""
    try:
        params = OpenFDADeviceRecallsParams(**(arguments or {}))
        data = fetch_device_recalls(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching openFDA device recalls: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openfda-device-recalls",
        description="Query openFDA medical-device recall records.",
        inputSchema=OpenFDADeviceRecallsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openfda-device-recalls"] = handle_device_recalls


###################
# Device 510(k)
###################


class OpenFDADevice510kParams(BaseModel):
    """Parameters for openFDA device 510(k) clearance queries."""

    search: Optional[str] = Field(
        None, description="openFDA search query (e.g. 'applicant:Medtronic')"
    )
    limit: int = Field(default=10, description="Number of results to return (max 100)")


def fetch_device_510k(params: OpenFDADevice510kParams) -> Any:
    """Fetch 510(k) device clearance records from openFDA."""
    query_params = _build_query(params.search, params.limit)
    response = http_get(f"{BASE_URL}/device/510k.json", params=query_params)
    return response.json()


async def handle_device_510k(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openfda-device-510k tool call."""
    try:
        params = OpenFDADevice510kParams(**(arguments or {}))
        data = fetch_device_510k(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching openFDA device 510k: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openfda-device-510k",
        description="Query openFDA 510(k) medical-device clearance records.",
        inputSchema=OpenFDADevice510kParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openfda-device-510k"] = handle_device_510k


###################
# Food Enforcement
###################


class OpenFDAFoodEnforcementParams(BaseModel):
    """Parameters for openFDA food enforcement (recall) queries."""

    search: Optional[str] = Field(
        None, description="openFDA search query (e.g. 'reason_for_recall:salmonella')"
    )
    limit: int = Field(default=10, description="Number of results to return (max 100)")


def fetch_food_enforcement(params: OpenFDAFoodEnforcementParams) -> Any:
    """Fetch food enforcement (recall) records from openFDA."""
    query_params = _build_query(params.search, params.limit)
    response = http_get(f"{BASE_URL}/food/enforcement.json", params=query_params)
    return response.json()


async def handle_food_enforcement(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openfda-food-enforcement tool call."""
    try:
        params = OpenFDAFoodEnforcementParams(**(arguments or {}))
        data = fetch_food_enforcement(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching openFDA food enforcement: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openfda-food-enforcement",
        description="Query openFDA food enforcement (recall) records.",
        inputSchema=OpenFDAFoodEnforcementParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openfda-food-enforcement"] = handle_food_enforcement


###################
# Animal & Veterinary Events
###################


class OpenFDAAnimalVeterinaryEventsParams(BaseModel):
    """Parameters for openFDA animal & veterinary adverse-event queries."""

    search: Optional[str] = Field(
        None,
        description="openFDA search query (e.g. 'animal.species:dog')",
    )
    limit: int = Field(default=10, description="Number of results to return (max 100)")


def fetch_animal_veterinary_events(
    params: OpenFDAAnimalVeterinaryEventsParams,
) -> Any:
    """Fetch animal & veterinary adverse-event reports from openFDA."""
    query_params = _build_query(params.search, params.limit)
    response = http_get(
        f"{BASE_URL}/animalandveterinary/event.json", params=query_params
    )
    return response.json()


async def handle_animal_veterinary_events(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the openfda-animalandveterinary-events tool call."""
    try:
        params = OpenFDAAnimalVeterinaryEventsParams(**(arguments or {}))
        data = fetch_animal_veterinary_events(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching openFDA animal & veterinary events: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="openfda-animalandveterinary-events",
        description="Query openFDA animal & veterinary adverse event reports.",
        inputSchema=OpenFDAAnimalVeterinaryEventsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["openfda-animalandveterinary-events"] = handle_animal_veterinary_events


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "us-fda-openfda", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
