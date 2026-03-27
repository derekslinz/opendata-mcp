import pytest
from unittest.mock import patch, Mock
from odmcp.providers.eu_eurostat import (
    list_eurostat_datasets,
    EurostatListDatasetsParams,
    handle_eurostat_list_datasets,
    fetch_eurostat_data,
    EurostatDataParams,
    handle_eurostat_get_dataset,
    fetch_eurostat_metadata,
    EurostatMetadataParams,
    handle_eurostat_get_metadata,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_eurostat_toc_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<nt:tree xmlns:nt="urn:eu.europa.ec.eurostat.navtree">
  <nt:leaf type="table">
    <code>NAMA_10_GDP</code>
    <nt:code>nama_10_gdp</nt:code>
    <nt:title language="en">GDP and main components</nt:title>
    <nt:lastUpdate>2023-01-01</nt:lastUpdate>
    <nt:lastDataUpdate>2023-01-02</nt:lastDataUpdate>
  </nt:leaf>
  <nt:leaf type="dataset">
    <nt:code>prc_hicp_manr</nt:code>
    <nt:title language="en">HICP - monthly data</nt:title>
    <nt:lastUpdate>2023-02-01</nt:lastUpdate>
  </nt:leaf>
</nt:tree>"""


@pytest.fixture
def mock_eurostat_data_response():
    return {
        "version": "2.0",
        "class": "dataset",
        "label": "GDP and main components",
        "value": [100.5, 102.3],
    }


@pytest.fixture
def mock_eurostat_metadata_response():
    return {
        "id": "nama_10_gdp",
        "label": "GDP and main components",
        "dimensions": {
            "geo": {"label": "Geopolitical entity"},
            "time": {"label": "Time"},
        },
    }


def test_list_eurostat_datasets(mock_eurostat_toc_xml):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.content = mock_eurostat_toc_xml.encode("utf-8")
        mock_get.return_value.raise_for_status = Mock()

        # Test listing all
        params = EurostatListDatasetsParams(limit=10)
        datasets = list_eurostat_datasets(params)
        assert len(datasets) == 2
        assert datasets[0].code == "nama_10_gdp"
        assert datasets[1].code == "prc_hicp_manr"

        # Test search
        params = EurostatListDatasetsParams(search="GDP")
        datasets = list_eurostat_datasets(params)
        assert len(datasets) == 1
        assert datasets[0].code == "nama_10_gdp"


@pytest.mark.anyio
async def test_handle_eurostat_list_datasets(mock_eurostat_toc_xml):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.content = mock_eurostat_toc_xml.encode("utf-8")
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_eurostat_list_datasets({"search": "HICP"})
        assert len(result) == 1
        assert "prc_hicp_manr" in result[0].text


def test_fetch_eurostat_data(mock_eurostat_data_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_eurostat_data_response
        mock_get.return_value.raise_for_status = Mock()

        params = EurostatDataParams(dataset_code="nama_10_gdp")
        response = fetch_eurostat_data(params)
        assert response["version"] == "2.0"
        assert response["value"][0] == 100.5


@pytest.mark.anyio
async def test_handle_eurostat_get_dataset(mock_eurostat_data_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_eurostat_data_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_eurostat_get_dataset({"dataset_code": "nama_10_gdp"})
        assert len(result) == 1
        assert "100.5" in result[0].text


def test_fetch_eurostat_metadata(mock_eurostat_metadata_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_eurostat_metadata_response
        mock_get.return_value.raise_for_status = Mock()

        params = EurostatMetadataParams(dataset_code="nama_10_gdp")
        response = fetch_eurostat_metadata(params)
        assert response["id"] == "nama_10_gdp"
        assert "geo" in response["dimensions"]


@pytest.mark.anyio
async def test_handle_eurostat_get_metadata(mock_eurostat_metadata_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_eurostat_metadata_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_eurostat_get_metadata({"dataset_code": "nama_10_gdp"})
        assert len(result) == 1
        assert "Geopolitical entity" in result[0].text
