import pytest

from opendata_mcp.routing import RoutingEngine


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_route_without_query_returns_filtered_results():
    engine = RoutingEngine()
    results = await engine.route(domain="health", limit=5)
    assert results
    assert all("health" in result.entry.domains for result in results)
    assert all(result.score == 1.0 for result in results)


@pytest.mark.anyio
async def test_route_cache_distinguishes_explain_and_limit():
    engine = RoutingEngine()

    first = await engine.route(query="earthquake", limit=1, explain=False)
    assert first

    second = await engine.route(query="earthquake", limit=5, explain=False)
    assert len(second) >= len(first)

    explained = await engine.route(query="earthquake", limit=1, explain=True)
    assert explained
    assert explained[0].breakdown is not None


@pytest.mark.anyio
async def test_route_filters_are_case_insensitive():
    engine = RoutingEngine()
    lower = await engine.route(region="uk", limit=10)
    upper = await engine.route(region="UK", limit=10)
    assert [item.entry.id for item in lower] == [item.entry.id for item in upper]
