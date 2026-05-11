import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_imf import (
    handle_list_dataflows,
    handle_get_dataflow,
    handle_get_data,
    handle_get_datastructure,
    handle_list_codelist,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_imf_list_dataflows_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {
                "dataflows": [
                    {"id": "IFS", "name": "International Financial Statistics"}
                ]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_dataflows()
        assert "IFS" in result[0].text


@pytest.mark.anyio
async def test_imf_list_dataflows_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_list_dataflows()


@pytest.mark.anyio
async def test_imf_list_dataflows_custom_agency():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {"dataflows": [{"id": "BOP"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_dataflows({"agencyId": "IMF.STA"})
        assert "BOP" in result[0].text


@pytest.mark.anyio
async def test_imf_get_dataflow_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {"dataflows": [{"id": "IFS", "version": "1.0"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_dataflow({"flowId": "IFS"})
        assert "IFS" in result[0].text


@pytest.mark.anyio
async def test_imf_get_dataflow_missing_args():
    with pytest.raises(ValueError):
        await handle_get_dataflow({})


@pytest.mark.anyio
async def test_imf_get_data_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {"dataSets": [{"action": "Information", "series": {"0:0:0": {}}}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_data(
            {
                "flowRef": "IMF.STA,IFS,1.0",
                "key": "USA",
                "startPeriod": "2020",
                "endPeriod": "2021",
            }
        )
        assert "dataSets" in result[0].text


@pytest.mark.anyio
async def test_imf_get_data_missing_args():
    with pytest.raises(ValueError):
        await handle_get_data({})


@pytest.mark.anyio
async def test_imf_get_datastructure_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {"dataStructures": [{"id": "DSD_IFS"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_datastructure({"structureId": "DSD_IFS"})
        assert "DSD_IFS" in result[0].text


@pytest.mark.anyio
async def test_imf_list_codelist_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {
                "codelists": [
                    {
                        "id": "CL_AREA",
                        "codes": [{"id": "USA", "name": "United States"}],
                    }
                ]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_codelist({"codelistId": "CL_AREA"})
        assert "CL_AREA" in result[0].text


@pytest.mark.anyio
async def test_imf_list_codelist_missing_args():
    with pytest.raises(ValueError):
        await handle_list_codelist({})
