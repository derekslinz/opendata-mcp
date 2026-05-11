import pytest
from unittest.mock import patch, Mock
from opendata_mcp.providers.global_dbnomics import (
    handle_dbnomics_search,
    handle_dbnomics_list_providers,
    handle_dbnomics_series,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_dbnomics_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "datasets": {"docs": [{"code": "WEO"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_dbnomics_search({"query": "GDP"})
        assert len(result) == 1
        assert "WEO" in result[0].text


@pytest.mark.anyio
async def test_dbnomics_list_providers_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "providers": {"docs": [{"code": "IMF"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_dbnomics_list_providers()
        assert len(result) == 1
        assert "IMF" in result[0].text


@pytest.mark.anyio
async def test_dbnomics_series_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "series": {"docs": [{"code": "NGDP"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_dbnomics_series({"series_ids": "IMF/WEO:NGDP"})
        assert len(result) == 1
        assert "NGDP" in result[0].text
