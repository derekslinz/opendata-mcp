from unittest.mock import patch

import pytest
from click.testing import CliRunner

from meta_data_mcp.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_run_starts_meta_server(runner):
    # run always starts meta_data_mcp; no provider arg accepted
    async def mock_main(transport="sse", port=8000, host="127.0.0.1"):
        pass

    mock_module = type("Module", (), {"main": mock_main})

    with patch("meta_data_mcp.cli._import_provider_module", return_value=mock_module):
        with patch("meta_data_mcp.cli.anyio.run") as mock_run:
            result = runner.invoke(cli, ["run"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(mock_module.main, "sse", 8000, "127.0.0.1")


def test_run_rejects_extra_args(runner):
    # run takes no positional arguments — extra args are a usage error
    result = runner.invoke(cli, ["run", "some_provider"])
    assert result.exit_code == 2


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


def test_setup_rejects_extra_args(runner):
    # setup takes no positional arguments — extra args are a usage error
    result = runner.invoke(cli, ["setup", "some_provider"])
    assert result.exit_code == 2


def test_setup_creates_backup_before_writing(runner, tmp_path):
    """setup writes a .json.bak before overwriting claude_desktop_config.json."""
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    original_content = '{"mcpServers": {}}'
    config_path.write_text(original_content)

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            runner.invoke(cli, ["setup", "--force"])

    backup_path = config_path.with_suffix(".json.bak")
    assert backup_path.exists(), ".json.bak should be created before writing config"
    assert backup_path.read_text() == original_content


def test_remove_creates_backup_before_writing(runner, tmp_path):
    """remove writes a .json.bak before overwriting claude_desktop_config.json."""
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    original_content = '{"mcpServers": {"meta-data-mcp": {}}}'
    config_path.write_text(original_content)

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            runner.invoke(cli, ["remove", "meta_data_mcp"])

    backup_path = config_path.with_suffix(".json.bak")
    assert backup_path.exists(), ".json.bak should be created before writing config"
    assert backup_path.read_text() == original_content


def test_cleanup_apply_creates_backup_before_writing(runner, tmp_path):
    """cleanup --apply writes a .json.bak before overwriting claude_desktop_config.json."""
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    original_content = '{"mcpServers": {"opendata-mcp-ch-sbb": {}}}'
    config_path.write_text(original_content)

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            runner.invoke(cli, ["cleanup", "--apply"])

    backup_path = config_path.with_suffix(".json.bak")
    assert backup_path.exists(), ".json.bak should be created before writing config"
    assert backup_path.read_text() == original_content


def test_strip_injected_server_keys_preserves_first_occurrence_only(tmp_path):
    """_strip_injected_server_keys keeps a command-name token only once."""
    import sys as _sys

    from meta_data_mcp.cli import _strip_injected_server_keys

    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    # Server key "setup" shares its name with the CLI subcommand.
    config_path.write_text('{"mcpServers": {"setup": {}, "opendata-mcp-all": {}}}')

    original_argv = _sys.argv[:]
    try:
        _sys.argv = ["meta-data-mcp", "setup", "setup", "opendata-mcp-all"]
        with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
            with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
                _strip_injected_server_keys()
        # The first "setup" is the real subcommand and must be kept;
        # the second "setup" and "opendata-mcp-all" are injected and must be stripped.
        assert _sys.argv == ["meta-data-mcp", "setup"]
    finally:
        _sys.argv = original_argv
