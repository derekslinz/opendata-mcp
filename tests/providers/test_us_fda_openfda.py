import pytest
from unittest.mock import patch, Mock
import httpx

from opendata_mcp.providers.us_fda_openfda import (
    handle_drug_events,
    handle_drug_labels,
    handle_drug_enforcement,
    handle_device_events,
    handle_device_recalls,
    handle_device_510k,
    handle_food_enforcement,
    handle_animal_veterinary_events,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_openfda_drug_events_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"safetyreportid": "1234567-1"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_drug_events(
            {"search": "patient.drug.medicinalproduct:aspirin", "limit": 1}
        )
        assert "1234567-1" in result[0].text


@pytest.mark.anyio
async def test_openfda_drug_labels_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"openfda": {"brand_name": ["TYLENOL"]}}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_drug_labels(
            {"search": "openfda.brand_name:tylenol", "limit": 1}
        )
        assert "TYLENOL" in result[0].text


@pytest.mark.anyio
async def test_openfda_drug_enforcement_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"classification": "Class I", "recall_number": "D-001"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_drug_enforcement(
            {"search": "classification:Class I", "limit": 1}
        )
        assert "Class I" in result[0].text


@pytest.mark.anyio
async def test_openfda_device_events_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"event_type": "Malfunction"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_device_events({"search": "device.brand_name:pacemaker"})
        assert "Malfunction" in result[0].text


@pytest.mark.anyio
async def test_openfda_device_recalls_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"recall_number": "Z-1234-2024"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_device_recalls({"search": "classification:Class I"})
        assert "Z-1234-2024" in result[0].text


@pytest.mark.anyio
async def test_openfda_device_510k_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"k_number": "K123456", "applicant": "Medtronic"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_device_510k({"search": "applicant:Medtronic"})
        assert "K123456" in result[0].text


@pytest.mark.anyio
async def test_openfda_food_enforcement_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"reason_for_recall": "Salmonella contamination"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_food_enforcement(
            {"search": "reason_for_recall:salmonella"}
        )
        assert "Salmonella" in result[0].text


@pytest.mark.anyio
async def test_openfda_animal_veterinary_events_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": [{"animal": {"species": "Dog"}}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_animal_veterinary_events({"search": "animal.species:dog"})
        assert "Dog" in result[0].text


@pytest.mark.anyio
async def test_openfda_http_error_propagates():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Boom")
        with pytest.raises(httpx.HTTPError):
            await handle_drug_events({"search": "anything"})
