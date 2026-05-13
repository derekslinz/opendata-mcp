import pytest
from unittest.mock import patch, Mock
from meta_data_mcp.providers.global_pubchem import (
    handle_pubchem_compound,
    handle_pubchem_substance,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_pubchem_compound_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "PC_Compounds": [{"id": {"id": {"cid": 241}}}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_pubchem_compound(
            {"identifier": "aspirin", "namespace": "name"}
        )
        assert len(result) == 1
        assert "241" in result[0].text


@pytest.mark.anyio
async def test_pubchem_substance_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {"PC_Substances": [{"sid": 12345}]}
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_pubchem_substance({"sid": 12345})
        assert len(result) == 1
        assert "12345" in result[0].text
