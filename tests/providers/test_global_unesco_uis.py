import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.global_unesco_uis import (
    handle_unesco_uis_list_dataflows,
    handle_unesco_uis_get_data,
    handle_unesco_uis_get_codelist,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_unesco_uis_list_dataflows_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "Structure": {
                "Dataflows": {
                    "Dataflow": [
                        {"@id": "SDG4", "@agencyID": "UNESCO", "@version": "1.0"},
                        {"@id": "GLOBAL", "@agencyID": "UNESCO", "@version": "1.0"},
                    ]
                }
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_unesco_uis_list_dataflows({})
        assert "SDG4" in result[0].text


@pytest.mark.anyio
async def test_unesco_uis_list_dataflows_sends_subscription_key(monkeypatch):
    monkeypatch.setenv("UNESCO_UIS_SUBSCRIPTION_KEY", "my-uis-key")
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {}
        mock_get.return_value.raise_for_status = Mock()

        await handle_unesco_uis_list_dataflows({})

        headers = mock_get.call_args.kwargs.get("headers", {})
        assert headers.get("Ocp-Apim-Subscription-Key") == "my-uis-key"


@pytest.mark.anyio
async def test_unesco_uis_list_dataflows_no_key_without_env(monkeypatch):
    monkeypatch.delenv("UNESCO_UIS_SUBSCRIPTION_KEY", raising=False)
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {}
        mock_get.return_value.raise_for_status = Mock()

        await handle_unesco_uis_list_dataflows({})

        headers = mock_get.call_args.kwargs.get("headers", {})
        assert "Ocp-Apim-Subscription-Key" not in headers


@pytest.mark.anyio
async def test_unesco_uis_list_dataflows_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Unauthorized")
        with pytest.raises(httpx.HTTPError):
            await handle_unesco_uis_list_dataflows({})


@pytest.mark.anyio
async def test_unesco_uis_get_data_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "dataSets": [{"action": "Information", "series": {}}],
            "structure": {
                "dimensions": {"series": [{"id": "COUNTRY", "name": "Country"}]}
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_unesco_uis_get_data(
            {"dataflow_id": "UNESCO,SDG4,1.0", "key": "all"}
        )
        assert "dataSets" in result[0].text


@pytest.mark.anyio
async def test_unesco_uis_get_data_missing_param():
    with pytest.raises(ValueError):
        await handle_unesco_uis_get_data({})


@pytest.mark.anyio
async def test_unesco_uis_get_data_with_time_filter():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"dataSets": []}
        mock_get.return_value.raise_for_status = Mock()

        await handle_unesco_uis_get_data(
            {
                "dataflow_id": "UNESCO,SDG4,1.0",
                "key": "all",
                "startPeriod": "2020",
                "endPeriod": "2023",
            }
        )
        call_params = mock_get.call_args.kwargs.get("params", {})
        assert call_params.get("startPeriod") == "2020"
        assert call_params.get("endPeriod") == "2023"


@pytest.mark.anyio
async def test_unesco_uis_get_codelist_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "Structure": {
                "Codelists": {
                    "Codelist": {
                        "@id": "CL_AREA",
                        "Code": [
                            {
                                "@value": "AFG",
                                "Description": [{"#text": "Afghanistan"}],
                            },
                            {"@value": "ALB", "Description": [{"#text": "Albania"}]},
                        ],
                    }
                }
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_unesco_uis_get_codelist({"resourceID": "CL_AREA"})
        assert "Afghanistan" in result[0].text
        assert "CL_AREA" in result[0].text


@pytest.mark.anyio
async def test_unesco_uis_get_codelist_missing_param():
    with pytest.raises(ValueError):
        await handle_unesco_uis_get_codelist({})
