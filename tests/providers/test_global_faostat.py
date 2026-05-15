"""Tests for the global-faostat provider."""

from unittest.mock import Mock, patch

import pytest

from meta_data_mcp.providers.global_faostat import (
    FaostatDataParams,
    FaostatListDomainsParams,
    FaostatListItemsParams,
    fetch_faostat_data,
    fetch_faostat_list_domains,
    fetch_faostat_list_items,
    handle_faostat_data,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _ok(payload: dict) -> Mock:
    r = Mock()
    r.json.return_value = payload
    r.raise_for_status = Mock()
    r.status_code = 200
    r.headers = {}
    return r


def test_list_domains():
    payload = {
        "data": [{"domain_code": "QCL", "domain_name": "Crops and livestock products"}]
    }
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok(payload)
        result = fetch_faostat_list_domains(FaostatListDomainsParams())
        assert result["data"][0]["domain_code"] == "QCL"
        assert "groupsanddomains" in mock_get.call_args[0][0]


def test_list_items_uses_domain_in_path():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"data": [{"item_code": "56", "item": "Maize"}]})
        result = fetch_faostat_list_items(FaostatListItemsParams(domain_code="QCL"))
        assert result["data"][0]["item"] == "Maize"
        assert "/dimensions/QCL/items" in mock_get.call_args[0][0]


def test_list_items_rejects_empty_domain():
    with pytest.raises(Exception):
        FaostatListItemsParams(domain_code="")


def test_data_endpoint_threads_filters():
    payload = {"data": [{"area": "USA", "item": "Maize", "year": 2022, "value": 1.0}]}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok(payload)
        params = FaostatDataParams(
            domain_code="QCL",
            area_codes="231",
            item_codes="56",
            element_codes="5510",
            year="2020,2021,2022",
            limit=500,
        )
        result = fetch_faostat_data(params)
        assert result["data"][0]["area"] == "USA"
        url = mock_get.call_args[0][0]
        assert url.endswith("/data/QCL")
        sent = mock_get.call_args[1]["params"]
        assert sent["area"] == "231"
        assert sent["item"] == "56"
        assert sent["element"] == "5510"
        assert sent["year"] == "2020,2021,2022"
        assert sent["limit"] == 500


def test_data_endpoint_omits_unset_filters():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok({"data": []})
        fetch_faostat_data(FaostatDataParams(domain_code="QCL"))
        sent = mock_get.call_args[1]["params"]
        assert "area" not in sent
        assert "item" not in sent
        assert "element" not in sent
        assert "year" not in sent


def test_data_limit_validation():
    with pytest.raises(Exception):
        FaostatDataParams(domain_code="QCL", limit=0)
    with pytest.raises(Exception):
        FaostatDataParams(domain_code="QCL", limit=10001)


@pytest.mark.anyio
async def test_handle_data():
    payload = {"data": [{"area": "USA", "value": 100}]}
    with patch("httpx.get") as mock_get:
        mock_get.return_value = _ok(payload)
        result = await handle_faostat_data({"domain_code": "QCL"})
        assert "USA" in result[0].text
