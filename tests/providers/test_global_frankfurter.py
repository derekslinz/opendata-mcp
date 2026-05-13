import pytest
from unittest.mock import patch, Mock
import httpx

from meta_data_mcp.providers.global_frankfurter import (
    handle_frankfurter_latest,
    handle_frankfurter_historical,
    handle_frankfurter_time_series,
    handle_frankfurter_currencies,
    handle_frankfurter_convert,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_frankfurter_latest_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "amount": 1.0,
            "base": "USD",
            "date": "2024-04-01",
            "rates": {"EUR": 0.92, "CHF": 0.91, "GBP": 0.79},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_frankfurter_latest(
            {"base": "USD", "targets": "EUR,CHF,GBP"}
        )
        assert "EUR" in result[0].text
        assert "0.92" in result[0].text


@pytest.mark.anyio
async def test_frankfurter_latest_default_base():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "amount": 1.0,
            "base": "USD",
            "rates": {"EUR": 0.92},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_frankfurter_latest()
        assert "USD" in result[0].text


@pytest.mark.anyio
async def test_frankfurter_latest_http_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network failure")

        with pytest.raises(httpx.HTTPError):
            await handle_frankfurter_latest()


@pytest.mark.anyio
async def test_frankfurter_historical_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "amount": 1.0,
            "base": "USD",
            "date": "2024-01-02",
            "rates": {"EUR": 0.91},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_frankfurter_historical(
            {"date": "2024-01-02", "base": "USD", "targets": "EUR"}
        )
        assert "2024-01-02" in result[0].text
        assert "0.91" in result[0].text


@pytest.mark.anyio
async def test_frankfurter_historical_missing_date():
    with pytest.raises(Exception):
        await handle_frankfurter_historical({})


@pytest.mark.anyio
async def test_frankfurter_time_series_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "amount": 1.0,
            "base": "USD",
            "start_date": "2024-01-01",
            "end_date": "2024-01-03",
            "rates": {
                "2024-01-02": {"EUR": 0.91},
                "2024-01-03": {"EUR": 0.90},
            },
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_frankfurter_time_series(
            {"start": "2024-01-01", "end": "2024-01-03", "targets": "EUR"}
        )
        assert "0.91" in result[0].text
        assert "2024-01-03" in result[0].text


@pytest.mark.anyio
async def test_frankfurter_currencies_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "USD": "United States Dollar",
            "EUR": "Euro",
            "GBP": "British Pound",
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_frankfurter_currencies()
        assert "Euro" in result[0].text


@pytest.mark.anyio
async def test_frankfurter_convert_success():
    with patch("httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "amount": 100.0,
            "base": "USD",
            "date": "2024-04-01",
            "rates": {"EUR": 92.0},
        }
        mock_get.return_value.raise_for_status = Mock()

        result = await handle_frankfurter_convert(
            {"amount": 100.0, "base": "USD", "target": "EUR"}
        )
        assert "92.0" in result[0].text
