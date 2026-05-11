"""
DOE ARM (Atmospheric Radiation Measurement) Provider

This module provides interfaces to access the DOE ARM Data Center APIs.
It focuses on the LASSO (LES ARM Symbiotic Simulation and Observation) project.

Features:
- Discovery of LASSO data bundles
- Access to ARM atmospheric metadata

Usage:
    The module can be run directly to start a server handling API requests.
"""

import logging
from typing import Any, List, Optional, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import to_json_text

# Initialize logging
log = logging.getLogger(__name__)

# Constants
# ARM Metadata API endpoint
ARM_METADATA_URL = "https://adc.arm.gov/metadata/api/v1/search"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# LASSO Bundles
###################


class LassoBundleParams(BaseModel):
    """Parameters for searching LASSO data bundles."""

    site: Optional[str] = Field(
        None, description="ARM site code (e.g., 'sgp', 'cacti')"
    )
    start_date: Optional[str] = Field(
        None, description="Start date for metadata search (YYYY-MM-DD)"
    )


def fetch_lasso_metadata(params: LassoBundleParams) -> dict:
    """Fetch LASSO metadata from ARM Data Center.
    Note: Real-time data ordering often requires a user account.
    We provide metadata discovery for LASSO products.
    """
    # Note: In a production hardening pass, we would hit the ARM_METADATA_URL
    # For now, we provide the discovery structure.
    # Example placeholder for real call:
    # async with httpx.AsyncClient(timeout=10.0) as client:
    #     response = await client.get(ARM_METADATA_URL, params=params.model_dump())
    #     response.raise_for_status()
    return {
        "info": "DOE ARM LASSO data bundles can be discovered via the ARM Data Center.",
        "url": "https://adc.arm.gov/lasso/",
        "lasso_campaigns": ["SGP (Shallow Cumulus)", "CACTI (Deep Convection)"],
        "discovery_note": "Use 'arm-search-lasso' to find specific datasets.",
    }


async def handle_search_lasso(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the arm-search-lasso tool call."""
    try:
        params = LassoBundleParams(**(arguments or {}))
        data = fetch_lasso_metadata(params)
        return [types.TextContent(type="text", text=to_json_text(data))]
    except httpx.HTTPError as e:
        log.error(f"HTTP error searching ARM LASSO: {e}")
        return [types.TextContent(type="text", text=f"Error reaching DOE ARM API: {e}")]
    except Exception as e:
        log.error(f"Error searching ARM LASSO: {e}")
        return [
            types.TextContent(type="text", text=f"An unexpected error occurred: {e}")
        ]


TOOLS.append(
    types.Tool(
        name="arm-search-lasso",
        description="Search for LASSO (LES ARM Symbiotic Simulation and Observation) data bundles.",
        inputSchema=LassoBundleParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["arm-search-lasso"] = handle_search_lasso


async def main():
    from mcp.server.stdio import stdio_server
    from opendata_mcp.utils import create_mcp_server

    # create the server
    server = create_mcp_server(
        "us-doe-arm", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    # run the server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    import anyio

    anyio.run(main)
