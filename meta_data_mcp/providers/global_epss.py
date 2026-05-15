"""global-epss provider.

FIRST.org Exploit Prediction Scoring System (EPSS) API — daily-updated
probability that a CVE will be exploited in the wild over the next 30
days, plus a percentile rank against all scored CVEs. Useful for
prioritizing patching beyond raw CVSS severity.

Homepage: https://www.first.org/epss/
License: EPSS data is published under CC BY 4.0; cite FIRST.org.
Auth: None required.
"""

import logging
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import BaseModel, Field

from meta_data_mcp.utils import (
    create_mcp_server,
    http_get,
    run_server,
    serialize_for_llm,
)

log = logging.getLogger(__name__)

PROVIDER_ID = "global-epss"
BASE_URL = "https://api.first.org/data/v1"

RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# epss-scores
###################


class EpssScoresParams(BaseModel):
    """Parameters for epss-scores."""

    cve: Optional[str] = Field(
        None,
        description=(
            "Comma-separated CVE id list (e.g. 'CVE-2021-44228,CVE-2024-3094'). "
            "Returns the latest EPSS score for each."
        ),
    )
    days: Optional[int] = Field(
        None,
        ge=1,
        le=30,
        description="Return scores updated in the last N days (1-30).",
    )
    epss_gt: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Filter to scores strictly greater than this probability (0.0-1.0).",
    )
    percentile_gt: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Filter to percentile rank strictly greater than this (0-100).",
    )
    order: Optional[str] = Field(
        None,
        description="Sort field — use '!epss' for descending EPSS, '!percentile' for top percentile.",
    )
    limit: Optional[int] = Field(
        100,
        ge=1,
        le=2000,
        description="Maximum number of results to return (default 100, max 2000).",
    )
    offset: Optional[int] = Field(
        0,
        ge=0,
        description="Pagination offset (0-indexed).",
    )


def fetch_epss_scores(params: EpssScoresParams) -> Any:
    """Query the EPSS API for CVE exploitation probability scores."""
    query: dict[str, Any] = {"envelope": "true", "pretty": "false"}
    if params.cve is not None:
        query["cve"] = params.cve
    if params.days is not None:
        query["days"] = params.days
    if params.epss_gt is not None:
        query["epss-gt"] = params.epss_gt
    if params.percentile_gt is not None:
        query["percentile-gt"] = params.percentile_gt
    if params.order is not None:
        query["order"] = params.order
    if params.limit is not None:
        query["limit"] = params.limit
    if params.offset is not None:
        query["offset"] = params.offset
    response = http_get(f"{BASE_URL}/epss", params=query, provider=PROVIDER_ID)
    return response.json()


async def handle_epss_scores(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the epss-scores tool call."""
    params = EpssScoresParams(**(arguments or {}))
    data = fetch_epss_scores(params)
    return [types.TextContent(type="text", text=serialize_for_llm(data))]


TOOLS.append(
    types.Tool(
        name="epss-scores",
        description=(
            "Query FIRST.org EPSS scores for one or more CVEs, or filter by "
            "probability / percentile / recency. Returns the daily-updated "
            "30-day exploitation probability and percentile rank for each CVE."
        ),
        inputSchema=EpssScoresParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["epss-scores"] = handle_epss_scores


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    server = create_mcp_server(
        "global-epss",
        RESOURCES,
        RESOURCES_HANDLERS,
        TOOLS,
        TOOLS_HANDLERS,
    )
    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
