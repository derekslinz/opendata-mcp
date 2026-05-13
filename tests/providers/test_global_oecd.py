import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_oecd import (
    handle_list_dataflows,
    handle_get_dataflow,
    handle_get_datastructure,
    handle_get_data,
    handle_list_codelist,
    handle_list_conceptscheme,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_oecd_list_dataflows_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {
                "dataflows": [
                    {"id": "DF_QNA_EXPENDITURE", "name": "Quarterly National Accounts"}
                ]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_dataflows()
        assert "DF_QNA_EXPENDITURE" in result[0].text


@pytest.mark.anyio
async def test_oecd_list_dataflows_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_list_dataflows()


@pytest.mark.anyio
async def test_oecd_get_dataflow_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {"dataflows": [{"id": "DF_QNA_EXPENDITURE", "version": "1.0"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_dataflow(
            {"agencyId": "OECD.SDD.NAD", "flowId": "DF_QNA_EXPENDITURE"}
        )
        assert "DF_QNA_EXPENDITURE" in result[0].text


@pytest.mark.anyio
async def test_oecd_get_dataflow_missing_args():
    with pytest.raises(ValueError):
        await handle_get_dataflow({"agencyId": "OECD.SDD.NAD"})


@pytest.mark.anyio
async def test_oecd_get_datastructure_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {
                "dataStructures": [
                    {"id": "DSD_NAMAIN1", "name": "National Accounts main"}
                ]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_datastructure(
            {"agencyId": "OECD.SDD.NAD", "structureId": "DSD_NAMAIN1"}
        )
        assert "DSD_NAMAIN1" in result[0].text


@pytest.mark.anyio
async def test_oecd_get_data_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {"dataSets": [{"action": "Information", "series": {"0:0:0": {}}}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_get_data(
            {
                "agencyId": "OECD.SDD.NAD",
                "flowId": "DF_QNA_EXPENDITURE",
                "version": "1.0",
                "key": "USA",
                "startPeriod": "2020",
                "endPeriod": "2021",
            }
        )
        assert "dataSets" in result[0].text


@pytest.mark.anyio
async def test_oecd_get_data_missing_args():
    with pytest.raises(ValueError):
        await handle_get_data({"agencyId": "OECD.SDD.NAD"})


@pytest.mark.anyio
async def test_oecd_list_codelist_success():
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

        result = await handle_list_codelist(
            {"agencyId": "OECD.SDD.NAD", "codelistId": "CL_AREA"}
        )
        assert "CL_AREA" in result[0].text
        assert "United States" in result[0].text


@pytest.mark.anyio
async def test_oecd_list_codelist_missing_args():
    with pytest.raises(ValueError):
        await handle_list_codelist({"agencyId": "OECD.SDD.NAD"})


@pytest.mark.anyio
async def test_oecd_list_conceptscheme_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {"conceptSchemes": [{"id": "CS_GENERIC", "concepts": []}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_list_conceptscheme(
            {"agencyId": "OECD.SDD.NAD", "schemeId": "CS_GENERIC"}
        )
        assert "CS_GENERIC" in result[0].text
