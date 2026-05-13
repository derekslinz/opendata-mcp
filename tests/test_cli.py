from unittest.mock import patch

import pytest
from click.testing import CliRunner

from meta_data_mcp.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_run_valid_provider(runner):
    # Create a mock module where main accepts transport, port, and host
    async def mock_main(transport="sse", port=8000, host="127.0.0.1"):
        pass

    mock_module = type("Module", (), {"main": mock_main})

    with patch("meta_data_mcp.cli._import_provider_module", return_value=mock_module):
        with patch("meta_data_mcp.cli.anyio.run") as mock_run:
            result = runner.invoke(cli, ["run", "test_provider"])

    assert result.exit_code == 0
    # The default transport is now sse, port 8000, host 127.0.0.1
    mock_run.assert_called_once_with(mock_module.main, "sse", 8000, "127.0.0.1")


def test_run_invalid_provider(runner):
    result = runner.invoke(cli, ["run", "nonexistent_provider"])
    assert result.exit_code == 1
    assert (
        "Provider 'nonexistent_provider' not found or has missing dependencies."
        in result.output
    )


def test_list_providers(runner):
    mock_modules = ["provider1", "provider2"]
    with patch("pkgutil.iter_modules") as mock_iter_modules:
        mock_iter_modules.return_value = [(None, name, False) for name in mock_modules]

        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "Available providers:" in result.output
        for provider in mock_modules:
            assert provider in result.output


def test_list_no_providers(runner):
    with patch("pkgutil.iter_modules") as mock_iter_modules:
        mock_iter_modules.return_value = []

        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "No providers available" in result.output


def test_info_valid_provider(runner):
    mock_module = type(
        "Module",
        (),
        {"__doc__": "Test provider description", "SUPPORTED_TYPES": ["type1", "type2"]},
    )

    with patch("importlib.import_module") as mock_import:
        mock_import.return_value = mock_module

        result = runner.invoke(cli, ["info", "test_provider"])

        assert result.exit_code == 0
        assert "Provider: test_provider" in result.output
        assert "Description: Test provider description" in result.output
        assert "Supported types: type1, type2" in result.output


def test_info_invalid_provider(runner):
    result = runner.invoke(cli, ["info", "nonexistent_provider"])
    assert result.exit_code == 1
    assert "Provider 'nonexistent_provider' not found" in result.output


def test_version_command(runner):
    with patch("meta_data_mcp.cli.__version__", "1.0.0"):
        result = runner.invoke(cli, ["version"])

    assert result.exit_code == 0
    assert "meta-data-mcp version: 1.0.0" in result.output


def test_setup_invalid_provider_does_not_write_config(runner, tmp_path):
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            result = runner.invoke(cli, ["setup", "nonexistent_provider"])

    assert result.exit_code == 1
    assert (
        "Provider 'nonexistent_provider' not found or has missing dependencies."
        in result.output
    )
    assert not config_path.exists()
