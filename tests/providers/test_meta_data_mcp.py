import json
from unittest.mock import AsyncMock, patch

import pytest

from opendata_mcp.providers.meta_data_mcp import (
    RESOURCES,
    PROMPTS,
    PROMPTS_HANDLERS,
    RESOURCES_HANDLERS,
    TOOLS,
    TOOLS_HANDLERS,
    handle_describe_provider,
    handle_discover_providers,
    handle_explain_choice,
    handle_find_providers,
    handle_list_domains,
    handle_list_providers,
    handle_list_regions,
    handle_read_all_providers,
)

EXPECTED_PROVIDER_FIELDS = {
    "id",
    "server_name",
    "title",
    "description",
    "domains",
    "regions",
    "keywords",
    "homepage",
    "license_note",
    "requires_env",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_meta_tools_registered():
    names = {tool.name for tool in TOOLS}
    assert names == {
        "opendata-explain-choice",
        "opendata-find-providers",
        "opendata-list-domains",
        "opendata-list-regions",
        "opendata-describe-provider",
        "opendata-list-providers",
    }


@pytest.mark.anyio
async def test_find_providers_by_query():
    result = await handle_find_providers({"query": "earthquake"})
    assert len(result) == 1
    assert "us_usgs_earthquake" in result[0].text


@pytest.mark.anyio
async def test_find_providers_by_domain():
    result = await handle_find_providers({"domain": "health"})
    text = result[0].text
    assert (
        "us_cdc_socrata" in text or "us_fda_openfda" in text or "global_who_gho" in text
    )


@pytest.mark.anyio
async def test_find_providers_by_region():
    result = await handle_find_providers({"region": "uk"})
    text = result[0].text
    assert "uk_gov" in text or "uk_ons" in text


@pytest.mark.anyio
async def test_find_providers_by_region_case_insensitive():
    result = await handle_find_providers({"region": "UK"})
    payload = json.loads(result[0].text)
    assert payload["count"] > 0


@pytest.mark.anyio
async def test_find_providers_without_query_uses_filters_only():
    result = await handle_find_providers({"domain": "health", "limit": 5})
    payload = json.loads(result[0].text)
    assert payload["count"] > 0


@pytest.mark.anyio
async def test_explain_choice_includes_breakdown():
    result = await handle_explain_choice({"query": "earthquake", "limit": 1})
    payload = json.loads(result[0].text)
    assert payload["results"]
    assert payload["results"][0]["scoring_breakdown"] is not None


@pytest.mark.anyio
async def test_find_providers_combined_filters():
    result = await handle_find_providers(
        {"query": "exchange rates", "domain": "finance", "limit": 5}
    )
    text = result[0].text
    assert "frankfurter" in text.lower() or "ecb" in text.lower()


@pytest.mark.anyio
async def test_find_providers_no_match_returns_empty():
    result = await handle_find_providers({"query": "zzzzzzzz_no_such_topic"})
    assert '"count": 0' in result[0].text


@pytest.mark.anyio
async def test_list_domains_returns_known_domains():
    result = await handle_list_domains({})
    text = result[0].text
    assert "health" in text
    assert "earth-science" in text
    assert "finance" in text


@pytest.mark.anyio
async def test_list_regions_returns_known_regions():
    result = await handle_list_regions({})
    text = result[0].text
    assert "us" in text
    assert "eu" in text
    assert "global" in text


@pytest.mark.anyio
async def test_describe_provider_known_id():
    result = await handle_describe_provider({"provider_id": "us_nasa"})
    text = result[0].text
    assert "us_nasa" in text
    assert "NASA" in text


@pytest.mark.anyio
async def test_describe_provider_unknown_id_returns_error_payload():
    result = await handle_describe_provider({"provider_id": "not_a_real_provider"})
    assert "not found" in result[0].text


@pytest.mark.anyio
async def test_describe_provider_requires_id():
    with pytest.raises(ValueError):
        await handle_describe_provider({})


@pytest.mark.anyio
async def test_list_providers_pagination():
    result = await handle_list_providers({"limit": 3, "offset": 0})
    text = result[0].text
    assert '"total"' in text
    assert '"limit": 3' in text


# Exception handler coverage tests
@pytest.mark.anyio
async def test_find_providers_exception_handling(caplog):
    """Test that exceptions in find_providers are logged and re-raised."""
    with patch("opendata_mcp.providers.meta_data_mcp.RoutingEngine") as mock_engine:
        mock_instance = AsyncMock()
        mock_instance.route.side_effect = RuntimeError("Test error")
        mock_engine.return_value = mock_instance

        with caplog.at_level("ERROR", logger="opendata_mcp.providers.meta_data_mcp"):
            with pytest.raises(RuntimeError, match="Test error"):
                await handle_find_providers({"query": "test"})

        assert "Error in opendata-find-providers: Test error" in caplog.text


@pytest.mark.anyio
async def test_explain_choice_exception_handling(caplog):
    """Test that exceptions in explain_choice are logged and re-raised."""
    with patch("opendata_mcp.providers.meta_data_mcp.RoutingEngine") as mock_engine:
        mock_instance = AsyncMock()
        mock_instance.route.side_effect = ValueError("Bad params")
        mock_engine.return_value = mock_instance

        with caplog.at_level("ERROR", logger="opendata_mcp.providers.meta_data_mcp"):
            with pytest.raises(ValueError, match="Bad params"):
                await handle_explain_choice({"query": "test"})

        assert "Error in opendata-explain-choice: Bad params" in caplog.text


@pytest.mark.anyio
async def test_list_domains_exception_handling(caplog):
    """Test that exceptions in list_domains are logged and re-raised."""
    with patch("opendata_mcp.providers.meta_data_mcp.list_domains") as mock_list:
        mock_list.side_effect = RuntimeError("Domain list error")

        with caplog.at_level("ERROR", logger="opendata_mcp.providers.meta_data_mcp"):
            with pytest.raises(RuntimeError, match="Domain list error"):
                await handle_list_domains({})

        assert "Error in opendata-list-domains: Domain list error" in caplog.text


@pytest.mark.anyio
async def test_list_regions_exception_handling(caplog):
    """Test that exceptions in list_regions are logged and re-raised."""
    with patch("opendata_mcp.providers.meta_data_mcp.list_regions") as mock_list:
        mock_list.side_effect = RuntimeError("Region list error")

        with caplog.at_level("ERROR", logger="opendata_mcp.providers.meta_data_mcp"):
            with pytest.raises(RuntimeError, match="Region list error"):
                await handle_list_regions({})

        assert "Error in opendata-list-regions: Region list error" in caplog.text


@pytest.mark.anyio
async def test_list_providers_exception_handling(caplog):
    """Test that exceptions in list_providers are logged and re-raised."""
    with patch("opendata_mcp.providers.meta_data_mcp.REGISTRY") as mock_registry:
        mock_registry.__getitem__.side_effect = RuntimeError("Registry error")

        with caplog.at_level("ERROR", logger="opendata_mcp.providers.meta_data_mcp"):
            with pytest.raises(RuntimeError, match="Registry error"):
                await handle_list_providers({"limit": 10})

        assert "Error in opendata-list-providers: Registry error" in caplog.text


# Resource handler coverage tests
def test_read_all_providers_returns_serialized_registry():
    """Test that resource handler returns serialized registry as string."""
    from pydantic import AnyUrl

    uri = AnyUrl("registry://all-providers")
    result = handle_read_all_providers(uri)
    # Verify it's a string and starts with JSON array
    assert isinstance(result, str)
    assert result.startswith("[")
    assert len(result) > 100  # Should have substantial content


def test_read_all_providers_includes_provider_data():
    """Test that resource handler includes expected provider fields."""
    from pydantic import AnyUrl

    uri = AnyUrl("registry://all-providers")
    with patch(
        "opendata_mcp.providers.meta_data_mcp.serialize_for_llm",
        side_effect=lambda payload: json.dumps(payload),
    ):
        result = handle_read_all_providers(uri)
    payload = json.loads(result)

    assert isinstance(payload, list)
    assert payload

    provider = payload[0]
    assert EXPECTED_PROVIDER_FIELDS.issubset(provider.keys())


# Prompt handler coverage tests
@pytest.mark.anyio
async def test_discover_providers_with_use_case():
    """Test discover_providers prompt handler with use case."""
    result = await handle_discover_providers({"use_case": "Build a weather dashboard"})
    assert result.description
    assert "weather dashboard" in result.description
    assert len(result.messages) == 1
    assert result.messages[0].role == "user"
    assert "weather dashboard" in result.messages[0].content.text


@pytest.mark.anyio
async def test_discover_providers_without_use_case():
    """Test discover_providers falls back to default when use_case missing."""
    result = await handle_discover_providers({})
    assert "General exploration" in result.description
    assert "General exploration" in result.messages[0].content.text


@pytest.mark.anyio
async def test_discover_providers_with_none_arguments():
    """Test discover_providers with None arguments."""
    result = await handle_discover_providers(None)
    assert result.description
    assert "General exploration" in result.description


# Use case prompt handlers
def test_all_use_case_prompts_registered():
    """Test that all use case prompts are registered."""
    prompt_names = {p.name for p in PROMPTS}
    assert "usecase-financial-research" in prompt_names
    assert "usecase-climate-dashboard" in prompt_names
    assert "usecase-healthcare-analytics" in prompt_names
    assert "usecase-academic-literature" in prompt_names


@pytest.mark.anyio
async def test_financial_research_use_case():
    """Test financial research use case prompt handler."""
    handler = PROMPTS_HANDLERS["usecase-financial-research"]
    result = await handler(None)
    assert (
        "financial" in result.description.lower()
        or "research" in result.description.lower()
    )
    assert "financial research tool" in result.messages[0].content.text.lower()


@pytest.mark.anyio
async def test_climate_dashboard_use_case():
    """Test climate dashboard use case prompt handler."""
    handler = PROMPTS_HANDLERS["usecase-climate-dashboard"]
    result = await handler(None)
    assert (
        "climate" in result.description.lower()
        or "environment" in result.description.lower()
    )
    assert "climate" in result.messages[0].content.text.lower()


@pytest.mark.anyio
async def test_healthcare_analytics_use_case():
    """Test healthcare analytics use case prompt handler."""
    handler = PROMPTS_HANDLERS["usecase-healthcare-analytics"]
    result = await handler(None)
    assert (
        "health" in result.description.lower()
        or "epidemiology" in result.description.lower()
    )
    assert "healthcare" in result.messages[0].content.text.lower()


@pytest.mark.anyio
async def test_academic_literature_use_case():
    """Test academic literature use case prompt handler."""
    handler = PROMPTS_HANDLERS["usecase-academic-literature"]
    result = await handler(None)
    assert (
        "literature" in result.description.lower()
        or "academic" in result.description.lower()
    )
    assert "literature review" in result.messages[0].content.text.lower()


# Explain choice with various parameters
@pytest.mark.anyio
async def test_explain_choice_with_domain_filter():
    """Test explain_choice with domain filter."""
    result = await handle_explain_choice(
        {"query": "epidemic", "domain": "health", "limit": 3}
    )
    payload = json.loads(result[0].text)
    assert payload["domain_filter"] == "health"
    assert payload["results"]


@pytest.mark.anyio
async def test_explain_choice_with_region_filter():
    """Test explain_choice with region filter."""
    result = await handle_explain_choice(
        {"query": "open data", "region": "us", "limit": 3}
    )
    payload = json.loads(result[0].text)
    assert payload["region_filter"] == "us"
    assert payload["results"]


@pytest.mark.anyio
async def test_explain_choice_without_query():
    """Test explain_choice with just domain filter, no query."""
    result = await handle_explain_choice({"domain": "finance", "limit": 2})
    payload = json.loads(result[0].text)
    assert payload["domain_filter"] == "finance"
    assert payload["results"]


# CLI/main entry point coverage tests
@pytest.mark.anyio
async def test_main_function_creates_server():
    """Test that main function creates MCP server with all resources/tools/prompts."""
    from opendata_mcp.providers.meta_data_mcp import main

    with patch("opendata_mcp.utils.create_mcp_server") as mock_create:
        with patch("opendata_mcp.utils.run_server") as mock_run:
            mock_server = object()
            mock_create.return_value = mock_server

            # Call main with mocked functions
            await main(transport="stdio", port=8000, host="127.0.0.1")

            # Verify the server was created with correct parameters
            mock_create.assert_called_once_with(
                "opendata-mcp-meta",
                resources=RESOURCES,
                resources_handlers=RESOURCES_HANDLERS,
                tools=TOOLS,
                tools_handlers=TOOLS_HANDLERS,
                prompts=PROMPTS,
                prompts_handlers=PROMPTS_HANDLERS,
            )

            # Verify run_server was called
            mock_run.assert_awaited_once_with(mock_server, "stdio", 8000, "127.0.0.1")
