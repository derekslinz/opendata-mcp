"""Tests for the meta-data-mcp CLI.

The CLI exposes ONE server (``meta-data-mcp``). Commands like ``info``,
``setup``, ``remove``, and ``inspect`` therefore do not take a provider
argument; plugins are an internal concept.
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from meta_data_mcp.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_run_starts_the_server(runner):
    """`run` boots the unified meta-data-mcp server."""

    async def mock_main(transport="stdio", port=8000, host="127.0.0.1"):
        return None

    with patch(
        "meta_data_mcp.providers.meta_data_mcp.main", new=mock_main
    ):
        with patch("meta_data_mcp.cli.anyio.run") as mock_run:
            result = runner.invoke(cli, ["run"])

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once_with(mock_main, "sse", 8000, "127.0.0.1")


def test_run_rejects_positional_args(runner):
    """`run` takes no positional args (no per-provider server)."""
    result = runner.invoke(cli, ["run", "some_provider"])
    assert result.exit_code == 2


def test_list_shows_plugins(runner):
    plugin_names = ["us_nasa", "global_frankfurter"]
    with patch("pkgutil.iter_modules") as mock_iter:
        mock_iter.return_value = [(None, name, False) for name in plugin_names]
        result = runner.invoke(cli, ["list"])

    assert result.exit_code == 0
    for name in plugin_names:
        assert name in result.output
    assert "plugins bundled in meta-data-mcp" in result.output


def test_list_no_plugins(runner):
    with patch("pkgutil.iter_modules") as mock_iter:
        mock_iter.return_value = []
        result = runner.invoke(cli, ["list"])

    assert result.exit_code == 0
    assert "No plugins found" in result.output


def test_info_default_shows_server_overview(runner):
    result = runner.invoke(cli, ["info"])
    assert result.exit_code == 0
    assert "meta-data-mcp" in result.output
    assert "single MCP server" in result.output


def test_info_plugin_flag_shows_plugin_doc(runner):
    mock_module = type("Module", (), {"__doc__": "Test plugin description"})
    with patch("importlib.import_module", return_value=mock_module):
        result = runner.invoke(cli, ["info", "--plugin", "test_plugin"])

    assert result.exit_code == 0
    assert "Plugin: test_plugin" in result.output
    assert "Test plugin description" in result.output


def test_info_unknown_plugin_errors(runner):
    result = runner.invoke(cli, ["info", "--plugin", "nonexistent"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_version_command(runner):
    with patch("meta_data_mcp.cli.__version__", "1.0.0"):
        result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "meta-data-mcp version: 1.0.0" in result.output


def test_setup_writes_one_server_key(runner, tmp_path):
    """`setup` registers exactly one key: ``meta-data-mcp``."""
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            result = runner.invoke(cli, ["setup", "--force"])

    assert result.exit_code == 0, result.output
    import json

    config = json.loads(config_path.read_text())
    assert list(config["mcpServers"].keys()) == ["meta-data-mcp"]


def test_setup_migrates_legacy_entries(runner, tmp_path):
    """`setup` removes any legacy multi-server keys automatically."""
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    config_path.write_text(
        '{"mcpServers": {'
        '  "opendata-mcp-us-nasa": {},'
        '  "opendata-mcp-meta": {},'
        '  "opendata-mcp-all": {},'
        '  "unrelated-server": {}'
        "}}"
    )

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            result = runner.invoke(cli, ["setup", "--force"])

    assert result.exit_code == 0, result.output
    import json

    config = json.loads(config_path.read_text())
    assert "unrelated-server" in config["mcpServers"]
    assert "meta-data-mcp" in config["mcpServers"]
    # all legacy opendata-mcp-* entries were removed
    assert not any(
        k.startswith("opendata-mcp-") for k in config["mcpServers"]
    )


def test_setup_creates_backup_before_writing(runner, tmp_path):
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    original_content = '{"mcpServers": {}}'
    config_path.write_text(original_content)

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            runner.invoke(cli, ["setup", "--force"])

    backup = config_path.with_suffix(".json.bak")
    assert backup.exists()
    assert backup.read_text() == original_content


def test_remove_removes_the_server_key(runner, tmp_path):
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    config_path.write_text(
        '{"mcpServers": {"meta-data-mcp": {}, "other-server": {}}}'
    )

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            result = runner.invoke(cli, ["remove"])

    assert result.exit_code == 0
    import json

    config = json.loads(config_path.read_text())
    assert "meta-data-mcp" not in config["mcpServers"]
    assert "other-server" in config["mcpServers"]


def test_remove_creates_backup_before_writing(runner, tmp_path):
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    original_content = '{"mcpServers": {"meta-data-mcp": {}}}'
    config_path.write_text(original_content)

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            runner.invoke(cli, ["remove"])

    backup = config_path.with_suffix(".json.bak")
    assert backup.exists()
    assert backup.read_text() == original_content


def test_cleanup_dry_run_lists_legacy_entries(runner, tmp_path):
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    config_path.write_text(
        '{"mcpServers": {"opendata-mcp-us-nasa": {}, "opendata-mcp-meta": {}}}'
    )

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            result = runner.invoke(cli, ["cleanup"])

    assert result.exit_code == 0
    assert "opendata-mcp-us-nasa" in result.output
    assert "opendata-mcp-meta" in result.output
    assert "Dry run" in result.output
    # No write yet
    import json

    config = json.loads(config_path.read_text())
    assert "opendata-mcp-us-nasa" in config["mcpServers"]


def test_cleanup_apply_removes_legacy_entries(runner, tmp_path):
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    config_path.write_text(
        '{"mcpServers": {"opendata-mcp-us-nasa": {}, "opendata-mcp-all": {}}}'
    )

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            result = runner.invoke(cli, ["cleanup", "--apply"])

    assert result.exit_code == 0
    import json

    config = json.loads(config_path.read_text())
    assert not any(
        k.startswith("opendata-mcp-") for k in config.get("mcpServers", {})
    )


def test_cleanup_apply_creates_backup_before_writing(runner, tmp_path):
    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    original_content = '{"mcpServers": {"opendata-mcp-ch-sbb": {}}}'
    config_path.write_text(original_content)

    with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
        with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
            runner.invoke(cli, ["cleanup", "--apply"])

    backup = config_path.with_suffix(".json.bak")
    assert backup.exists()
    assert backup.read_text() == original_content


def test_strip_injected_server_keys_preserves_first_occurrence_only(tmp_path):
    """Injected server keys are stripped, but a real subcommand name is kept."""
    import sys as _sys

    from meta_data_mcp.cli import _strip_injected_server_keys

    claude_dir = tmp_path / "Library" / "Application Support" / "Claude"
    claude_dir.mkdir(parents=True)
    config_path = claude_dir / "claude_desktop_config.json"
    config_path.write_text('{"mcpServers": {"setup": {}, "meta-data-mcp": {}}}')

    original_argv = _sys.argv[:]
    try:
        _sys.argv = ["meta-data-mcp", "setup", "setup", "meta-data-mcp"]
        with patch("meta_data_mcp.cli.platform.system", return_value="Darwin"):
            with patch("meta_data_mcp.cli.Path.home", return_value=tmp_path):
                _strip_injected_server_keys()
        assert _sys.argv == ["meta-data-mcp", "setup"]
    finally:
        _sys.argv = original_argv
