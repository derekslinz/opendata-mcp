import pytest
from unittest.mock import patch, Mock
from opendata_mcp.providers.nl_tweedekamer import (
    list_tk_entities,
    query_tk_entity,
    TkQueryEntityParams,
    handle_tk_query,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_odata_response():
    return {
        "value": [
            {
                "Id": "fab499e2-93b6-4bba-8266-00014175f6a6",
                "Voornamen": "Jan",
                "Achternaam": "de Vries",
            }
        ]
    }


def test_list_tk_entities():
    entities = list_tk_entities()
    assert "Persoon" in entities
    assert "Fractie" in entities
    assert len(entities) > 10


def test_query_tk_entity(mock_odata_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_odata_response
        mock_get.return_value.raise_for_status = Mock()

        params = TkQueryEntityParams(
            entity="Persoon",
            filter="Achternaam eq 'de Vries'",
            select="Id,Voornamen,Achternaam",
            top=1,
        )
        result = query_tk_entity(params)

        # Verify URL construction
        args, kwargs = mock_get.call_args
        assert args[0] == "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/Persoon"
        assert kwargs["params"]["$filter"] == "Achternaam eq 'de Vries'"
        assert kwargs["params"]["$select"] == "Id,Voornamen,Achternaam"

        assert result["value"][0]["Voornamen"] == "Jan"


@pytest.mark.anyio
async def test_handle_tk_query(mock_odata_response):
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = mock_odata_response
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_tk_query({"entity": "Persoon", "top": 1})
        assert len(result) == 1
        assert "Jan" in result[0].text
        assert "de Vries" in result[0].text
