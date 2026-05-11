import pytest
from unittest.mock import patch, Mock
from opendata_mcp.providers.global_rcsb_pdb import (
    handle_pdb_entry,
    handle_pdb_polymer,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_pdb_entry_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "rcsb_id": "4HHB",
            "struct": {"title": "Hemoglobin"},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_pdb_entry({"entry_id": "4HHB"})
        assert len(result) == 1
        assert "4HHB" in result[0].text
        assert "Hemoglobin" in result[0].text


@pytest.mark.anyio
async def test_pdb_polymer_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "rcsb_id": "4HHB_1",
            "rcsb_polymer_entity": {"details": "Alpha chain"},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_pdb_polymer({"entry_id": "4HHB", "entity_id": "1"})
        assert len(result) == 1
        assert "Alpha chain" in result[0].text
