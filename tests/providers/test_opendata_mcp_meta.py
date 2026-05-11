import pytest

from opendata_mcp.providers.opendata_mcp_meta import (
    handle_find_providers,
    handle_list_domains,
    handle_list_regions,
    handle_describe_provider,
    handle_list_providers,
    TOOLS,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_meta_tools_registered():
    names = {tool.name for tool in TOOLS}
    assert names == {
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
async def test_find_providers_combined_filters():
    result = await handle_find_providers(
        {"query": "exchange rates", "domain": "finance", "limit": 5}
    )
    text = result[0].text
    assert "frankfurter" in text.lower() or "ecb" in text.lower()


@pytest.mark.anyio
async def test_find_providers_no_match_returns_empty():
    result = await handle_find_providers({"query": "zzzzzzzz_no_such_topic"})
    assert "'count': 0" in result[0].text


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
    assert "'total'" in text
    assert "'limit': 3" in text


@pytest.mark.anyio
async def test_list_providers_shows_required_env_when_present():
    result = await handle_list_providers({"limit": 200, "offset": 0})
    text = result[0].text
    # us_fred is in the registry and requires FRED_API_KEY
    assert "FRED_API_KEY" in text
