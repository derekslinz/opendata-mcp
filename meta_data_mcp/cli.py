"""CLI entry point for meta-data-mcp.

There is ONE MCP server: ``meta-data-mcp``. The ~60 modules under
``meta_data_mcp/providers/`` are internal *plugins* of this server, not
separate servers. The CLI therefore does not take a "provider" argument —
all commands operate on the one server.

Commands:

    run       — start the server
    setup     — register the server in Claude Desktop's config
    remove    — unregister the server from Claude Desktop's config
    cleanup   — remove legacy individual-provider entries (pre-unified setups)
    inspect   — launch MCP Inspector against the server
    list      — informational: list internal plugins
    info      — informational: show server / plugin description
    version   — show the package version
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

# Add src to sys.path so this works when run from a source checkout.
_src_path = str(Path(__file__).parent.parent)
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

import anyio  # noqa: E402
import click  # noqa: E402

from meta_data_mcp import __version__  # noqa: E402

# The package name on PyPI and the CLI entry-point are identical.
LIB_NAME = "meta-data-mcp"

# The single Claude Desktop ``mcpServers`` key for the unified server.
SERVER_KEY = "meta-data-mcp"

# Legacy keys produced by earlier multi-server CLI versions. The cleanup
# logic removes/migrates these whenever setup or cleanup runs.
_LEGACY_PREFIX = "opendata-mcp-"
_LEGACY_DOUBLE_META = "opendata-mcp-meta-data-mcp"
_LEGACY_DOUBLE_ALL = "opendata-mcp-opendata-mcp-all"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return (
            Path.home()
            / "Library/Application Support/Claude/claude_desktop_config.json"
        )
    return Path(os.getenv("APPDATA") or "") / "Claude/claude_desktop_config.json"


def _backup_config(config_path: Path) -> None:
    if config_path.exists():
        config_path.with_suffix(".json.bak").write_text(config_path.read_text())


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text())
    except json.JSONDecodeError:
        click.echo(
            f"Error: {config_path} contains invalid JSON. Please fix it manually.",
            err=True,
        )
        sys.exit(1)


def _server_entry(use_local: bool, repo_root: Path) -> dict:
    """Build the Claude Desktop ``mcpServers`` entry for the one server."""
    if use_local:
        return {
            "command": "uv",
            "args": [
                "--directory",
                str(repo_root),
                "run",
                LIB_NAME,
                "run",
                "--transport",
                "stdio",
            ],
            "env": {"OTEL_SDK_DISABLED": "true"},
        }
    return {
        "command": "uvx",
        "args": [LIB_NAME, "run", "--transport", "stdio"],
    }


def _migrate_legacy_entries(config: dict) -> list[str]:
    """Remove every legacy multi-server entry from *config* (in place).

    Returns the sorted list of keys that were removed. Legacy keys are:

    - Any key starting with ``opendata-mcp-`` (individual providers, plus
      the old ``opendata-mcp-meta`` and ``opendata-mcp-all`` two-server
      install).
    - The double-prefixed mistakes from earlier CLI versions.
    """
    servers = config.get("mcpServers")
    if not isinstance(servers, dict):
        return []

    to_remove = sorted(
        k
        for k in servers
        if k.startswith(_LEGACY_PREFIX)
        or k
        in {
            _LEGACY_DOUBLE_META,
            _LEGACY_DOUBLE_ALL,
        }
    )
    for key in to_remove:
        del servers[key]
    return to_remove


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def cli() -> None:
    """meta-data-mcp — the single MCP server for ~60 open-data plugins."""


@cli.command()
@click.option(
    "--transport",
    default="sse",
    show_default=True,
    type=click.Choice(["stdio", "sse"]),
    help="Transport protocol (sse for interactive, stdio for Claude Desktop).",
)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=int,
    help="Port for SSE transport.",
)
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host for SSE transport.",
)
def run(transport: str, port: int, host: str) -> None:
    """Run the meta-data-mcp server."""
    try:
        from meta_data_mcp.providers import meta_data_mcp as server_module

        anyio.run(server_module.main, transport, port, host)
    except Exception as e:
        import traceback

        traceback.print_exc()
        click.echo(f"Error running server: {e}", err=True)
        sys.exit(1)


@cli.command()
def version() -> None:
    """Show the package version."""
    click.echo(f"{LIB_NAME} version: {__version__}")


@cli.command(name="list")
def list_plugins() -> None:
    """List the internal plugins bundled with this server (informational).

    Plugins are not separately installable or addressable; they are loaded
    automatically when the server starts.
    """
    import pkgutil

    import meta_data_mcp.providers as providers_pkg

    plugins = sorted(
        name
        for _, name, _ in pkgutil.iter_modules(providers_pkg.__path__)
        if name not in ("__template__", "__init__", "utils", "meta_data_mcp")
    )

    if not plugins:
        click.echo("No plugins found.")
        return

    click.echo(f"{len(plugins)} plugins bundled in {LIB_NAME}:")
    for name in plugins:
        click.echo(f"  - {name}")
    click.echo("\nAll plugin tools are exposed through the one `meta-data-mcp` server.")


@cli.command()
@click.option(
    "--plugin",
    default=None,
    help=(
        "Optional: show the docstring for a specific internal plugin. "
        "Without --plugin, shows the meta-server overview."
    ),
)
def info(plugin: str | None) -> None:
    """Show information about the server (or a specific internal plugin)."""
    if plugin is None:
        click.echo(f"{LIB_NAME} — single MCP server, version {__version__}.")
        click.echo(
            "Exposes discovery tools plus the tools of every bundled plugin "
            "under one tool namespace."
        )
        click.echo("\nUse `meta-data-mcp list` to enumerate the plugins.")
        return

    try:
        import importlib

        module = importlib.import_module(f"meta_data_mcp.providers.{plugin}")
    except ImportError as e:
        click.echo(f"Plugin '{plugin}' not found: {e}", err=True)
        sys.exit(1)

    click.echo(f"Plugin: {plugin}")
    doc = getattr(module, "__doc__", None)
    if doc:
        click.echo(f"Description: {doc.strip()}")


@cli.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.argument("_extra", nargs=-1)
@click.option(
    "--local", is_flag=True, help="Force local development mode using absolute paths."
)
@click.option("--force", is_flag=True, help="Overwrite an existing configuration.")
@click.option(
    "--print-json",
    "print_json",
    is_flag=True,
    help=(
        "Print the server's JSON configuration snippet to stdout and exit "
        "without touching any config file. Useful for piping into other "
        "MCP clients."
    ),
)
def setup(_extra: tuple, local: bool, force: bool, print_json: bool) -> None:
    """Register the one meta-data-mcp server in Claude Desktop's config.

    Any legacy multi-server entries from older CLI versions are removed
    automatically.
    """
    if print_json:
        repo_root = Path(__file__).parent.parent.resolve()
        is_local_repo = (repo_root / "pyproject.toml").exists()
        use_local = is_local_repo or local
        snippet = {SERVER_KEY: _server_entry(use_local, repo_root)}
        click.echo(json.dumps(snippet, indent=2))

        auth_token = os.getenv("META_DATA_MCP_AUTH_TOKEN")
        if auth_token:
            remote_snippet = {
                SERVER_KEY: {
                    "url": "https://YOUR-HOST/sse",
                    "headers": {"Authorization": f"Bearer {auth_token}"},
                }
            }
            click.echo(
                "\n# SSE bearer auth is enabled (META_DATA_MCP_AUTH_TOKEN is set).\n"
                "# The snippet above launches the server locally via stdio and does\n"
                "# NOT need auth. To wire a REMOTE MCP client to this server over\n"
                "# SSE, use the following client config (replace YOUR-HOST with\n"
                "# the public hostname, e.g. linzalytics.com):\n"
                f"#\n# {json.dumps(remote_snippet, indent=2).replace(chr(10), chr(10) + '# ')}",
                err=True,
            )
        return

    system = platform.system()
    if system not in ("Darwin", "Windows"):
        click.echo("Setup is only supported on macOS and Windows.", err=True)
        sys.exit(1)

    config_path = _config_path()
    if not config_path.parent.exists():
        click.echo(
            f"Couldn't find Claude config directory at {config_path.parent}.",
            err=True,
        )
        sys.exit(1)

    config = _load_config(config_path)
    config.setdefault("mcpServers", {})

    removed = _migrate_legacy_entries(config)
    if removed:
        click.echo(
            f"Migrated: removed {len(removed)} legacy entry/entries "
            f"({', '.join(removed[:5])}{'…' if len(removed) > 5 else ''})."
        )

    if SERVER_KEY in config["mcpServers"] and not force:
        click.confirm(
            f"Server '{SERVER_KEY}' is already configured. Overwrite?", abort=True
        )

    repo_root = Path(__file__).parent.parent.resolve()
    is_local_repo = (repo_root / "pyproject.toml").exists()
    use_local = is_local_repo or local
    mode_label = (
        f"LOCAL mode pointing to {repo_root}"
        if use_local
        else f"GLOBAL mode using 'uvx {LIB_NAME}'"
    )
    click.echo(f"Configuring '{SERVER_KEY}' in {mode_label}.")

    config["mcpServers"][SERVER_KEY] = _server_entry(use_local, repo_root)

    _backup_config(config_path)
    config_path.write_text(json.dumps(config, indent=2))
    click.echo(
        f"Successfully configured '{SERVER_KEY}'. Please restart Claude Desktop."
    )


@cli.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.argument("_extra", nargs=-1)
def remove(_extra: tuple) -> None:
    """Unregister the meta-data-mcp server from Claude Desktop's config."""
    config_path = _config_path()
    if not config_path.exists():
        click.echo("No Claude Desktop config file — nothing to remove.")
        return

    config = _load_config(config_path)
    servers = config.get("mcpServers", {})
    if SERVER_KEY not in servers:
        click.echo(f"'{SERVER_KEY}' is not configured.")
        return

    del servers[SERVER_KEY]
    if not servers:
        config.pop("mcpServers", None)
    _backup_config(config_path)
    config_path.write_text(json.dumps(config, indent=2))
    click.echo(f"Removed '{SERVER_KEY}'. Restart Claude Desktop to apply.")


@cli.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.argument("_extra", nargs=-1)
@click.option(
    "--apply",
    is_flag=True,
    help="Remove detected legacy entries (defaults to dry-run preview).",
)
def cleanup(_extra: tuple, apply: bool) -> None:
    """Detect and remove legacy multi-server entries from Claude Desktop config.

    Older versions of this CLI registered one MCP server per provider plus
    separate ``opendata-mcp-meta`` and ``opendata-mcp-all`` aggregators.
    The current architecture uses ONE server: ``meta-data-mcp``. This
    command finds and removes the obsolete entries.
    """
    config_path = _config_path()
    if not config_path.exists():
        click.echo("No Claude Desktop config — nothing to clean up.")
        return

    config = _load_config(config_path)
    servers = config.get("mcpServers", {})

    legacy = sorted(
        k
        for k in servers
        if k.startswith(_LEGACY_PREFIX)
        or k
        in {
            _LEGACY_DOUBLE_META,
            _LEGACY_DOUBLE_ALL,
        }
    )
    if not legacy:
        click.echo("No legacy entries found.")
        if SERVER_KEY in servers:
            click.echo(f"✓ '{SERVER_KEY}' is registered.")
        else:
            click.echo(f"Tip: run `{LIB_NAME} setup` to register the server.")
        return

    click.echo(f"Found {len(legacy)} legacy entry/entries:")
    for key in legacy:
        click.echo(f"  - {key}")

    if not apply:
        click.echo("\nDry run — no changes made. Re-run with --apply to remove.")
        return

    removed = _migrate_legacy_entries(config)
    _backup_config(config_path)
    config_path.write_text(json.dumps(config, indent=2))
    click.echo(f"\nRemoved {len(removed)} legacy entry/entries.")
    if SERVER_KEY not in config.get("mcpServers", {}):
        click.echo(f"Tip: run `{LIB_NAME} setup` to register the server.")


@cli.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.argument("_extra", nargs=-1)
@click.option(
    "--local", is_flag=True, help="Force local development mode using absolute paths."
)
def inspect(_extra: tuple, local: bool) -> None:
    """Launch MCP Inspector against the meta-data-mcp server.

    Requires Node.js / npx. Opens http://localhost:5173 where you can
    browse the server's tools and try them out.
    """
    import shutil
    import subprocess

    if shutil.which("npx") is None:
        click.echo(
            "npx not found. Install Node.js (https://nodejs.org/) to use mcp-inspector.",
            err=True,
        )
        sys.exit(1)

    repo_root = Path(__file__).parent.parent.resolve()
    is_local_repo = (repo_root / "pyproject.toml").exists()
    use_local = is_local_repo or local

    if use_local:
        server_cmd = [
            "uv",
            "--directory",
            str(repo_root),
            "run",
            LIB_NAME,
            "run",
            "--transport",
            "stdio",
        ]
    else:
        server_cmd = ["uvx", LIB_NAME, "run", "--transport", "stdio"]

    click.echo(f"Starting MCP Inspector against {LIB_NAME}…")
    click.echo("Open http://localhost:5173 in your browser (Ctrl-C to stop).")

    try:
        subprocess.run(
            ["npx", "-y", "@modelcontextprotocol/inspector"] + server_cmd,
            check=True,
        )
    except KeyboardInterrupt:
        pass
    except subprocess.CalledProcessError as e:
        click.echo(f"Inspector exited with code {e.returncode}.", err=True)
        sys.exit(e.returncode)


# ---------------------------------------------------------------------------
# Defensive: strip Claude Desktop injected mcpServers keys from sys.argv
# ---------------------------------------------------------------------------


def _strip_injected_server_keys() -> None:
    """Strip Claude Desktop ``mcpServers`` keys that get appended to sys.argv.

    When Claude Desktop restarts an MCP server, it sometimes appends the
    server's own config key as a positional arg. We strip those (but never
    a real subcommand name).
    """
    try:
        config_path = _config_path()
        if not config_path.exists():
            return
        config = json.loads(config_path.read_text())
        server_keys = set(config.get("mcpServers", {}).keys())
        if not server_keys:
            return
        known_commands = set(cli.commands.keys())
        already_preserved: set[str] = set()
        clean: list[str] = []
        for arg in sys.argv[1:]:
            if arg not in server_keys:
                clean.append(arg)
            elif arg in known_commands and arg not in already_preserved:
                clean.append(arg)
                already_preserved.add(arg)
            # else: drop the injected server key
        sys.argv[1:] = clean
    except Exception:
        pass  # never break the CLI if config can't be read


def main() -> None:
    _strip_injected_server_keys()
    cli()


if __name__ == "__main__":
    main()
