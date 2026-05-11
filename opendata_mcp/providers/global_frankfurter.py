"""
Frankfurter (ECB FX rates) Provider

This module exposes the Frankfurter API, a free, key-less wrapper around the
European Central Bank's published reference exchange rates.

License / source:
    Data is sourced from the European Central Bank statistical data
    warehouse. The Frankfurter project itself is open source. ECB
    reference rates are typically published once per working day around
    16:00 CET; consult the ECB's terms of use before redistribution.

Features:
- Latest reference rates against a base currency
- Historical reference rates for a specific date
- Time-series rates between two dates
- List of supported currencies
- Simple amount conversion between two currencies

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
BASE_URL = "https://api.frankfurter.app"

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# Latest rates
###################


class FrankfurterLatestParams(BaseModel):
    """Parameters for fetching the latest FX rates."""

    base: str = Field(
        default="USD",
        description="Base currency (ISO 4217 code, e.g. USD, EUR, GBP).",
    )
    targets: Optional[str] = Field(
        default=None,
        description="Comma-separated target currency codes (e.g. 'EUR,CHF,GBP'). Leave blank for all.",
    )


def fetch_frankfurter_latest(params: FrankfurterLatestParams) -> dict:
    """Fetch the latest ECB reference rates."""
    query_params: dict[str, Any] = {"from": params.base}
    if params.targets:
        query_params["to"] = params.targets
    response = http_get(f"{BASE_URL}/latest", params=query_params)
    return response.json()


async def handle_frankfurter_latest(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the frankfurter-latest tool call."""
    try:
        params = FrankfurterLatestParams(**(arguments or {}))
        data = fetch_frankfurter_latest(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Frankfurter latest rates: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="frankfurter-latest",
        description="Get the latest ECB reference FX rates for a base currency and optional target list.",
        inputSchema=FrankfurterLatestParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["frankfurter-latest"] = handle_frankfurter_latest


###################
# Historical rates
###################


class FrankfurterHistoricalParams(BaseModel):
    """Parameters for fetching FX rates on a specific historical date."""

    date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Historical date (YYYY-MM-DD). Must be on or after 1999-01-04.",
    )
    base: str = Field(
        default="USD",
        description="Base currency (ISO 4217 code).",
    )
    targets: Optional[str] = Field(
        default=None,
        description="Comma-separated target currency codes. Leave blank for all.",
    )


def fetch_frankfurter_historical(params: FrankfurterHistoricalParams) -> dict:
    """Fetch ECB reference rates for a specific date."""
    query_params: dict[str, Any] = {"from": params.base}
    if params.targets:
        query_params["to"] = params.targets
    response = http_get(f"{BASE_URL}/{params.date}", params=query_params)
    return response.json()


async def handle_frankfurter_historical(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the frankfurter-historical tool call."""
    try:
        if not arguments or "date" not in arguments:
            raise ValueError("date is required")
        params = FrankfurterHistoricalParams(**arguments)
        data = fetch_frankfurter_historical(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Frankfurter historical rates: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="frankfurter-historical",
        description="Get ECB reference FX rates for a specific historical date.",
        inputSchema=FrankfurterHistoricalParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["frankfurter-historical"] = handle_frankfurter_historical


###################
# Time series
###################


class FrankfurterTimeSeriesParams(BaseModel):
    """Parameters for fetching a time series of FX rates."""

    start: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Start date (YYYY-MM-DD).",
    )
    end: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="End date (YYYY-MM-DD).",
    )
    base: str = Field(
        default="USD",
        description="Base currency (ISO 4217 code).",
    )
    targets: Optional[str] = Field(
        default=None,
        description="Comma-separated target currency codes. Leave blank for all.",
    )


def fetch_frankfurter_time_series(params: FrankfurterTimeSeriesParams) -> dict:
    """Fetch a time series of ECB reference rates."""
    query_params: dict[str, Any] = {"from": params.base}
    if params.targets:
        query_params["to"] = params.targets
    response = http_get(f"{BASE_URL}/{params.start}..{params.end}", params=query_params)
    return response.json()


async def handle_frankfurter_time_series(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the frankfurter-time-series tool call."""
    try:
        if not arguments or "start" not in arguments or "end" not in arguments:
            raise ValueError("start and end are required")
        params = FrankfurterTimeSeriesParams(**arguments)
        data = fetch_frankfurter_time_series(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Frankfurter time series: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="frankfurter-time-series",
        description="Get a time series of ECB reference FX rates between two dates.",
        inputSchema=FrankfurterTimeSeriesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["frankfurter-time-series"] = handle_frankfurter_time_series


###################
# Currencies
###################


class FrankfurterCurrenciesParams(BaseModel):
    """Parameters for listing supported currencies (no inputs)."""


def fetch_frankfurter_currencies(_: FrankfurterCurrenciesParams) -> dict:
    """Fetch the list of supported currencies."""
    response = http_get(f"{BASE_URL}/currencies")
    return response.json()


async def handle_frankfurter_currencies(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the frankfurter-currencies tool call."""
    try:
        params = FrankfurterCurrenciesParams(**(arguments or {}))
        data = fetch_frankfurter_currencies(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error fetching Frankfurter currencies: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="frankfurter-currencies",
        description="List the currencies supported by Frankfurter (ECB reference rates).",
        inputSchema=FrankfurterCurrenciesParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["frankfurter-currencies"] = handle_frankfurter_currencies


###################
# Convert
###################


class FrankfurterConvertParams(BaseModel):
    """Parameters for converting an amount between two currencies."""

    amount: float = Field(
        ...,
        description="Amount to convert (in the source currency).",
    )
    base: str = Field(
        ...,
        description="Source currency ISO 4217 code (e.g. USD).",
    )
    target: str = Field(
        ...,
        description="Target currency ISO 4217 code (e.g. EUR).",
    )


def fetch_frankfurter_convert(params: FrankfurterConvertParams) -> dict:
    """Convert an amount between two currencies using the latest ECB rates."""
    query_params: dict[str, Any] = {
        "amount": params.amount,
        "from": params.base,
        "to": params.target,
    }
    response = http_get(f"{BASE_URL}/latest", params=query_params)
    return response.json()


async def handle_frankfurter_convert(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the frankfurter-convert tool call."""
    try:
        if (
            not arguments
            or "amount" not in arguments
            or "base" not in arguments
            or "target" not in arguments
        ):
            raise ValueError("amount, base, and target are required")
        params = FrankfurterConvertParams(**arguments)
        data = fetch_frankfurter_convert(params)
        return [types.TextContent(type="text", text=serialize_for_llm(data))]
    except Exception as e:
        log.error(f"Error performing Frankfurter conversion: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="frankfurter-convert",
        description="Convert an amount from one currency to another using the latest ECB reference rate.",
        inputSchema=FrankfurterConvertParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["frankfurter-convert"] = handle_frankfurter_convert


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from opendata_mcp.utils import create_mcp_server, run_server

    server = create_mcp_server(
        "global-frankfurter", RESOURCES, RESOURCES_HANDLERS, TOOLS, TOOLS_HANDLERS
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
