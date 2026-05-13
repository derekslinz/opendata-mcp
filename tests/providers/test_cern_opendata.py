import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.cern_opendata import (
    handle_search_records,
    handle_get_record,
    handle_list_collections,
    handle_search_by_experiment,
    handle_search_software,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_cern_search_records_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "hits": {"hits": [{"metadata": {"title": "Higgs boson dataset"}}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_records({"q": "higgs", "size": 5})
        assert len(result) == 1
        assert "Higgs" in result[0].text


@pytest.mark.anyio
async def test_cern_get_record_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "metadata": {"recid": 12345, "title": "CMS run 2011"}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_record({"record_id": 12345})
        assert "CMS run 2011" in result[0].text


@pytest.mark.anyio
async def test_cern_get_record_missing_id():
    with pytest.raises(ValueError, match="record_id is required"):
        await handle_get_record({})


@pytest.mark.anyio
async def test_cern_list_collections_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "hits": {"hits": [{"metadata": {"title": "Dataset A"}}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_collections({"size": 10})
        assert "Dataset A" in result[0].text


@pytest.mark.anyio
async def test_cern_search_by_experiment_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "hits": {
                "hits": [{"metadata": {"experiment": "CMS", "title": "CMS analysis"}}]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_by_experiment(
            {"experiment": "CMS", "q": "jets", "size": 5}
        )
        assert "CMS analysis" in result[0].text


@pytest.mark.anyio
async def test_cern_search_by_experiment_missing_experiment():
    with pytest.raises(ValueError, match="experiment is required"):
        await handle_search_by_experiment({})


@pytest.mark.anyio
async def test_cern_search_software_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "hits": {"hits": [{"metadata": {"title": "CMSSW Release"}}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_search_software({"q": "cmssw", "size": 5})
        assert "CMSSW" in result[0].text


@pytest.mark.anyio
async def test_cern_http_error_propagates():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Boom")
        with pytest.raises(httpx.HTTPError):
            await handle_search_records({"q": "anything"})
