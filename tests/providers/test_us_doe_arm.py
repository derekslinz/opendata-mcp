import pytest
from odmcp.providers.us_doe_arm import handle_search_lasso


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_arm_search_lasso_success():
    # Currently it's static, so it should just work.
    result = await handle_search_lasso({"site": "sgp"})
    assert len(result) == 1
    assert "SGP (Shallow Cumulus)" in result[0].text


@pytest.mark.anyio
async def test_arm_search_lasso_empty_results():
    # If the logic changes to a real API we'll mock it. Current handler provides success info.
    result = await handle_search_lasso({"site": "unknown"})
    assert "DOE ARM LASSO" in result[0].text
