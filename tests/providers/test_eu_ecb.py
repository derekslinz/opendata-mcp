import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.eu_ecb import (
    handle_ecb_list_dataflows,
    handle_ecb_get_dataflow,
    handle_ecb_get_data,
    handle_ecb_get_codelist,
    handle_ecb_get_conceptscheme,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_ecb_list_dataflows_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {
                "dataflows": [
                    {"id": "EXR", "name": "Exchange Rates"},
                    {"id": "BSI", "name": "Balance Sheet Items"},
                ]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ecb_list_dataflows()
        assert "Exchange Rates" in result[0].text


@pytest.mark.anyio
async def test_ecb_list_dataflows_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("ECB unreachable")

        with pytest.raises(httpx.HTTPError):
            await handle_ecb_list_dataflows()


@pytest.mark.anyio
async def test_ecb_get_dataflow_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {"dataflows": [{"id": "EXR", "name": "Exchange Rates"}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ecb_get_dataflow({"id": "EXR"})
        assert "Exchange Rates" in result[0].text


@pytest.mark.anyio
async def test_ecb_get_dataflow_missing_id():
    with pytest.raises(Exception):
        await handle_ecb_get_dataflow({})


@pytest.mark.anyio
async def test_ecb_get_data_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {
                "dataSets": [
                    {"series": {"0:0:0:0:0": {"observations": {"0": [1.085]}}}}
                ]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ecb_get_data(
            {
                "flow": "EXR",
                "key": "D.USD.EUR.SP00.A",
                "lastNObservations": 1,
            }
        )
        assert "1.085" in result[0].text


@pytest.mark.anyio
async def test_ecb_get_data_missing_args():
    with pytest.raises(Exception):
        await handle_ecb_get_data({"flow": "EXR"})


@pytest.mark.anyio
async def test_ecb_get_codelist_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {
                "codelists": [
                    {
                        "id": "CL_CURRENCY",
                        "codes": [{"id": "USD", "name": "US Dollar"}],
                    }
                ]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ecb_get_codelist({"id": "CL_CURRENCY"})
        assert "US Dollar" in result[0].text


@pytest.mark.anyio
async def test_ecb_get_conceptscheme_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "data": {
                "conceptSchemes": [{"id": "ECB_CONCEPTS", "concepts": [{"id": "FREQ"}]}]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_ecb_get_conceptscheme({"id": "ECB_CONCEPTS"})
        assert "ECB_CONCEPTS" in result[0].text
