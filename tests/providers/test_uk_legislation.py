import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.uk_legislation import (
    handle_uk_legislation_search,
    handle_uk_legislation_list_by_year,
    handle_uk_legislation_get_document_xml,
    handle_uk_legislation_get_document_html,
    handle_uk_legislation_list_types,
    handle_uk_legislation_changes_feed,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


ATOM_SAMPLE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<feed xmlns="http://www.w3.org/2005/Atom">'
    "<title>UK Legislation Search</title>"
    "<entry><title>Data Protection Act 2018</title>"
    '<link href="https://www.legislation.gov.uk/ukpga/2018/12"/>'
    "</entry></feed>"
)

XML_SAMPLE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<akomaNtoso><act><meta><identification><title>Test Act</title>"
    "</identification></meta></act></akomaNtoso>"
)

HTML_SAMPLE = (
    "<html><body><h1>Browse Legislation</h1><ul><li>ukpga</li></ul></body></html>"
)


@pytest.mark.anyio
async def test_uk_legislation_search_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_legislation_search({"title": "Data Protection"})
        assert "Data Protection Act 2018" in result[0].text


@pytest.mark.anyio
async def test_uk_legislation_search_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("legislation.gov.uk down")

        with pytest.raises(httpx.HTTPError):
            await handle_uk_legislation_search({"title": "anything"})


@pytest.mark.anyio
async def test_uk_legislation_search_uses_atom_accept_header():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        await handle_uk_legislation_search({"text": "data"})

        headers = mock_get.call_args.kwargs.get("headers", {})
        assert headers.get("Accept") == "application/atom+xml"


@pytest.mark.anyio
async def test_uk_legislation_list_by_year_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_legislation_list_by_year(
            {"type": "ukpga", "year": 2018}
        )
        assert "Data Protection Act 2018" in result[0].text


@pytest.mark.anyio
async def test_uk_legislation_list_by_year_requires_args():
    with pytest.raises(ValueError):
        await handle_uk_legislation_list_by_year({"type": "ukpga"})


@pytest.mark.anyio
async def test_uk_legislation_get_document_xml_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = XML_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_legislation_get_document_xml(
            {"type": "ukpga", "year": 2018, "number": 12}
        )
        assert "Test Act" in result[0].text
        assert "akomaNtoso" in result[0].text


@pytest.mark.anyio
async def test_uk_legislation_get_document_xml_url():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = XML_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        await handle_uk_legislation_get_document_xml(
            {"type": "ukpga", "year": 2018, "number": 12}
        )
        called_url = mock_get.call_args.args[0]
        assert called_url.endswith("/ukpga/2018/12/data.xml")


@pytest.mark.anyio
async def test_uk_legislation_get_document_html_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = HTML_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_legislation_get_document_html(
            {"type": "ukpga", "year": 2018, "number": 12}
        )
        assert "Browse Legislation" in result[0].text


@pytest.mark.anyio
async def test_uk_legislation_list_types_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = HTML_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_legislation_list_types({})
        assert "Browse Legislation" in result[0].text
        assert "ukpga" in result[0].text


@pytest.mark.anyio
async def test_uk_legislation_changes_feed_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.text = ATOM_SAMPLE
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_uk_legislation_changes_feed(
            {"type": "ukpga", "year": 2018, "number": 12}
        )
        assert "UK Legislation Search" in result[0].text


@pytest.mark.anyio
async def test_uk_legislation_changes_feed_requires_args():
    with pytest.raises(ValueError):
        await handle_uk_legislation_changes_feed({"type": "ukpga", "year": 2018})
