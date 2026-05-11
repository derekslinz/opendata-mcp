"""
Eurostat Data API Client

This module provides interfaces to access the Eurostat Statistics API and Catalogue API.
It allows querying various European statistical datasets, including economic,
geographic, and social data.

Features:
- Dataset discovery through the Table of Contents (TOC)
- Data retrieval in JSON-stat 2.0 format
- Metadata retrieval for dataset dimensions and labels

Usage:
    The module can be run directly to start a server handling API requests,
    or its components can be imported and used individually.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any, List, Optional, Sequence

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

from opendata_mcp.utils import to_json_text

# Initialize logging
log = logging.getLogger(__name__)

# Constants
BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination"
TOC_URL = f"{BASE_URL}/catalogue/toc/xml?lang=en"
DATA_URL = f"{BASE_URL}/statistics/1.0/data"
METADATA_URL = f"{BASE_URL}/statistics/1.0/metadata/dataset"

# Namespaces for TOC XML
NAMESPACES = {"nt": "urn:eu.europa.ec.eurostat.navtree"}

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}

###################
# Eurostat Dataset Discovery
###################


class EurostatListDatasetsParams(BaseModel):
    """Parameters for listing or searching Eurostat datasets."""

    search: Optional[str] = Field(
        None, description="Keyword to search in dataset titles or codes"
    )
    limit: int = Field(default=20, description="Maximum number of datasets to return")


class EurostatDatasetInfo(BaseModel):
    """Basic information about a Eurostat dataset."""

    code: str = Field(..., description="The unique code of the dataset")
    title: str = Field(..., description="The title of the dataset")
    type: str = Field(..., description="Type of the node (table, dataset, etc.)")
    last_update: Optional[str] = Field(None, description="Last update of the metadata")
    last_data_update: Optional[str] = Field(None, description="Last update of the data")


def list_eurostat_datasets(
    params: EurostatListDatasetsParams,
) -> List[EurostatDatasetInfo]:
    """Search or list available Eurostat datasets from the TOC XML."""
    response = httpx.get(TOC_URL, timeout=30.0)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    datasets = []

    # We look for <nt:leaf> elements which represent actual data products
    for leaf in root.findall(".//nt:leaf", NAMESPACES):
        code_elem = leaf.find("nt:code", NAMESPACES)
        title_elem = leaf.find("nt:title[@language='en']", NAMESPACES)

        if code_elem is None or title_elem is None:
            continue

        code = code_elem.text or ""
        title = title_elem.text or ""
        node_type = leaf.get("type", "unknown")

        # Filtering
        if params.search:
            search_lower = params.search.lower()
            if search_lower not in code.lower() and search_lower not in title.lower():
                continue

        last_update = leaf.findtext("nt:lastUpdate", namespaces=NAMESPACES)
        last_data_update = leaf.findtext("nt:lastDataUpdate", namespaces=NAMESPACES)

        datasets.append(
            EurostatDatasetInfo(
                code=code,
                title=title,
                type=node_type,
                last_update=last_update,
                last_data_update=last_data_update,
            )
        )

        if len(datasets) >= params.limit:
            break

    return datasets


async def handle_eurostat_list_datasets(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the eurostat-list-datasets tool call."""
    try:
        params = EurostatListDatasetsParams(**(arguments or {}))
        datasets = list_eurostat_datasets(params)
        return [
            types.TextContent(
                type="text", text=to_json_text([d.model_dump() for d in datasets])
            )
        ]
    except Exception as e:
        log.error(f"Error listing Eurostat datasets: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="eurostat-list-datasets",
        description="Search or list available Eurostat datasets from the Table of Contents.",
        inputSchema=EurostatListDatasetsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["eurostat-list-datasets"] = handle_eurostat_list_datasets

###################
# Eurostat Data Retrieval
###################


class EurostatDataParams(BaseModel):
    """Parameters for fetching data from a Eurostat dataset."""

    dataset_code: str = Field(
        ..., description="The code of the dataset (e.g., 'nama_10_gdp')"
    )
    lang: str = Field(
        default="en", description="Language of labels: 'en', 'fr', or 'de'"
    )


def fetch_eurostat_data(params: EurostatDataParams) -> dict:
    """Fetch data from a specific Eurostat dataset in JSON-stat format."""
    endpoint = f"{DATA_URL}/{params.dataset_code}"
    query_params = {"format": "JSON", "lang": params.lang}

    response = httpx.get(endpoint, params=query_params, timeout=30.0)
    response.raise_for_status()
    return response.json()


async def handle_eurostat_get_dataset(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the eurostat-get-dataset tool call."""
    try:
        if not arguments or "dataset_code" not in arguments:
            raise ValueError("dataset_code is required")

        params = EurostatDataParams(**arguments)
        data = fetch_eurostat_data(params)
        return [
            types.TextContent(type="text", text=to_json_text(data, max_chars=20000))
        ]
    except Exception as e:
        log.error(f"Error fetching Eurostat data: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="eurostat-get-dataset",
        description="Fetch data from a specific Eurostat dataset in JSON-stat format.",
        inputSchema=EurostatDataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["eurostat-get-dataset"] = handle_eurostat_get_dataset

###################
# Eurostat Metadata
###################


class EurostatMetadataParams(BaseModel):
    """Parameters for fetching metadata for a Eurostat dataset."""

    dataset_code: str = Field(
        ..., description="The code of the dataset (e.g., 'nama_10_gdp')"
    )
    lang: str = Field(default="en", description="Language: 'en', 'fr', or 'de'")


def fetch_eurostat_metadata(params: EurostatMetadataParams) -> dict:
    """Fetch dimension/label metadata for a specific Eurostat dataset.

    Returns only the 'dimension' and 'label' keys from the JSON-stat response,
    which contain the dataset structure (variables, categories, labels) without
    the full data values.
    """
    endpoint = f"{DATA_URL}/{params.dataset_code}"
    query_params = {"format": "JSON", "lang": params.lang}

    response = httpx.get(endpoint, params=query_params, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    # Return only structural metadata, not the full data values
    return {
        "id": data.get("id"),
        "size": data.get("size"),
        "dimension": data.get("dimension"),
        "label": data.get("label"),
        "updated": data.get("updated"),
        "source": data.get("source"),
    }


async def handle_eurostat_get_metadata(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the eurostat-get-metadata tool call."""
    try:
        if not arguments or "dataset_code" not in arguments:
            raise ValueError("dataset_code is required")

        params = EurostatMetadataParams(**arguments)
        metadata = fetch_eurostat_metadata(params)
        return [types.TextContent(type="text", text=to_json_text(metadata))]
    except Exception as e:
        log.error(f"Error fetching Eurostat metadata: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="eurostat-get-metadata",
        description="Fetch metadata (dimensions, labels) for a specific Eurostat dataset.",
        inputSchema=EurostatMetadataParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["eurostat-get-metadata"] = handle_eurostat_get_metadata


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "eu-eurostat", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


# Server initialization
if __name__ == "__main__":
    import anyio

    anyio.run(main)
