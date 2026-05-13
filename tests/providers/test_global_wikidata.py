import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_wikidata import (
    TOOLS,
    TOOLS_HANDLERS,
    handle_wikidata_get_entities,
    handle_wikidata_search_entities,
    handle_wikidata_get_claims,
    handle_wikidata_sparql,
    handle_wikidata_list_properties,
    handle_wikidata_get_by_title,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_tools_registered():
    names = [t.name for t in TOOLS]
    for name in names:
        assert name in TOOLS_HANDLERS


@pytest.mark.anyio
async def test_wikidata_get_entities_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "entities": {
                "Q42": {"id": "Q42", "labels": {"en": {"value": "Douglas Adams"}}}
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_wikidata_get_entities({"ids": "Q42"})
        assert len(result) == 1
        assert "Douglas Adams" in result[0].text


@pytest.mark.anyio
async def test_wikidata_get_entities_missing_ids():
    with pytest.raises(ValueError):
        await handle_wikidata_get_entities({})


@pytest.mark.anyio
async def test_wikidata_search_entities_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "search": [{"id": "Q42", "label": "Douglas Adams"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_wikidata_search_entities({"search": "Douglas Adams"})
        assert "Q42" in result[0].text


@pytest.mark.anyio
async def test_wikidata_get_claims_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "claims": {"P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q5"}}}}]}
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_wikidata_get_claims({"entity": "Q42", "property": "P31"})
        assert "P31" in result[0].text


@pytest.mark.anyio
async def test_wikidata_sparql_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "results": {
                "bindings": [{"item": {"value": "http://www.wikidata.org/entity/Q42"}}]
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_wikidata_sparql(
            {"query": "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 } LIMIT 1"}
        )
        assert "Q42" in result[0].text


@pytest.mark.anyio
async def test_wikidata_list_properties_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "search": [{"id": "P31", "label": "instance of"}]
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_wikidata_list_properties({"search": "instance of"})
        assert "P31" in result[0].text


@pytest.mark.anyio
async def test_wikidata_get_by_title_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "entities": {
                "Q937": {
                    "id": "Q937",
                    "sitelinks": {"enwiki": {"title": "Albert Einstein"}},
                }
            }
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_wikidata_get_by_title({"titles": "Albert Einstein"})
        assert "Q937" in result[0].text


@pytest.mark.anyio
async def test_wikidata_sparql_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network down")

        with pytest.raises(httpx.HTTPError):
            await handle_wikidata_sparql(
                {"query": "SELECT * WHERE { ?s ?p ?o } LIMIT 1"}
            )
