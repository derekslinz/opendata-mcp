import importlib
import json
import os
import platform
import sys
from pathlib import Path

# Add src to sys.path to allow running from source
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import anyio  # noqa: E402
import click  # noqa: E402
from opendata_mcp import __version__  # noqa: E402

LIB_NAME = "opendata-mcp"
SERVER_PREFIX = "opendata-mcp-"


@click.group()
def cli():
    """OpenDataMCP CLI tool - Build and use open data MCP servers."""
    pass


def _import_provider_module(provider: str):
    return importlib.import_module(f"opendata_mcp.providers.{provider}")


@cli.command()
@click.argument("provider")
@click.option(
    "--transport",
    default="sse",
    show_default=True,
    type=click.Choice(["stdio", "sse"]),
    help="Transport protocol to use (stdio or sse)",
)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=int,
    help="Port to listen on for SSE transport",
)
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host to listen on for SSE transport",
)
def run(provider: str, transport: str, port: int, host: str):
    """Run a specific provider MCP server."""
    try:
        module = _import_provider_module(provider)
        # Check if main accepts host
        import inspect

        sig = inspect.signature(module.main)
        if "host" in sig.parameters:
            anyio.run(module.main, transport, port, host)
        else:
            anyio.run(module.main, transport, port)
    except ImportError as e:
        click.echo(
            f"Provider '{provider}' not found or has missing dependencies.", err=True
        )
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        click.echo(f"Error running provider: {e}", err=True)
        sys.exit(1)


@cli.command()
def list():
    """List all available providers"""
    try:
        import pkgutil

        import opendata_mcp.providers as providers_pkg

        # Get all modules in the providers package
        providers = [
            name
            for finder, name, ispkg in pkgutil.iter_modules(providers_pkg.__path__)
            if name not in ("__template__", "__init__", "utils")
        ]

        if not providers:
            click.echo("No providers available")
            return

        click.echo("Available providers:")
        for provider in sorted(providers):
            click.echo(f"  - {provider}")
    except Exception as e:
        click.echo(f"Error listing providers: {e}")
        sys.exit(1)


@cli.command()
@click.argument("provider")
def info(provider: str):
    """Show detailed information about a provider"""
    try:
        module = _import_provider_module(provider)

        click.echo(f"Provider: {provider}")
        if hasattr(module, "__doc__") and module.__doc__:
            click.echo(f"Description: {module.__doc__.strip()}")
        if hasattr(module, "SUPPORTED_TYPES"):
            click.echo(f"Supported types: {', '.join(module.SUPPORTED_TYPES)}")
    except ImportError:
        click.echo(f"Provider '{provider}' not found. Make sure it's installed with:")
        click.echo(f"uv pip install 'opendata_mcp[{provider}]'")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error getting provider info: {e}")
        sys.exit(1)


@cli.command()
def version():
    """Show the version of opendata-mcp"""
    try:
        click.echo(f"opendata-mcp version: {__version__}")
    except Exception as e:
        click.echo(f"Error getting version: {e}")
        sys.exit(1)


def _build_server_entry(provider: str, is_local: bool, repo_root: Path) -> dict:
    """Return a Claude Desktop mcpServers entry dict for *provider*."""
    if is_local:
        return {
            "command": "uv",
            "args": [
                "--directory",
                str(repo_root),
                "run",
                "opendata-mcp",
                "run",
                "--transport",
                "stdio",
                provider,
            ],
            "env": {"OTEL_SDK_DISABLED": "true"},
        }
    return {
        "command": "uvx",
        "args": [LIB_NAME, "run", "--transport", "stdio", provider],
    }


@cli.command()
@click.argument("provider")
@click.option(
    "--local", is_flag=True, help="Force local development mode using absolute paths."
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration.")
def setup(provider: str, local: bool, force: bool):
    """Setup the MCP server for use with Claude Desktop.

    When PROVIDER is 'opendata_mcp_meta', the companion aggregator server
    'opendata_mcp_all' is registered automatically alongside it.  This gives
    Claude both provider discovery (meta) and access to all 300+ tools (all)
    from a single command:

        uv run opendata-mcp setup opendata_mcp_meta
    """
    try:
        _import_provider_module(provider)
    except ImportError as e:
        click.echo(
            f"Provider '{provider}' not found or has missing dependencies.", err=True
        )
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Check platform
    system = platform.system()
    if system not in ["Darwin", "Windows"]:
        click.echo("This command is only supported on Windows and macOS")
        sys.exit(1)

    # Determine config path
    if system == "Darwin":
        config_path = (
            Path.home()
            / "Library/Application Support/Claude/claude_desktop_config.json"
        )
    else:  # Windows
        config_path = (
            Path(os.getenv("APPDATA") or "") / "Claude/claude_desktop_config.json"
        )

    if not config_path.parent.exists():
        click.echo(
            f"Couldn't find Claude configuration directory at {config_path.parent}"
        )
        sys.exit(1)

    # Load or create config
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            click.echo(
                f"Error: {config_path} contains invalid JSON. Please fix it manually."
            )
            sys.exit(1)
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    server_key = f"{SERVER_PREFIX}{provider.replace('_', '-')}"
    if server_key in config["mcpServers"] and not force:
        click.confirm(
            f"Server '{server_key}' is already configured. Overwrite?", abort=True
        )

    repo_root = Path(__file__).parent.parent.resolve()
    is_local_repo = (repo_root / "pyproject.toml").exists()
    use_local = is_local_repo or local

    config["mcpServers"][server_key] = _build_server_entry(provider, use_local, repo_root)
    mode_label = f"LOCAL mode pointing to {repo_root}" if use_local else f"GLOBAL mode using 'uvx {LIB_NAME}'"
    click.echo(f"Configuring in {mode_label}")

    # When setting up the meta provider, automatically register the aggregator
    # companion so Claude has both discovery tools and access to all 300+ data tools.
    companion_key = None
    if provider == "opendata_mcp_meta":
        companion = "opendata_mcp_all"
        companion_key = f"{SERVER_PREFIX}{companion.replace('_', '-')}"
        if companion_key not in config["mcpServers"] or force:
            config["mcpServers"][companion_key] = _build_server_entry(companion, use_local, repo_root)
            click.echo(f"  + also registering companion '{companion_key}' (aggregator, all 300+ tools)")
        else:
            click.echo(f"  ✓ companion '{companion_key}' already configured — skipping")

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        configured = [server_key] + ([companion_key] if companion_key else [])
        click.echo(
            f"Successfully configured {', '.join(repr(k) for k in configured)}. "
            "Please restart Claude Desktop."
        )
    except Exception as e:
        click.echo(f"Error updating config file: {e}")
        sys.exit(1)


@cli.command()
@click.argument("provider")
def remove(provider: str):
    """Remove MCP server configuration for a provider"""
    # Check platform
    system = platform.system()
    if system not in ["Darwin", "Windows"]:
        click.echo("This command is only supported on Windows and macOS")
        sys.exit(1)

    # Determine config path
    if system == "Darwin":
        config_path = (
            Path.home()
            / "Library/Application Support/Claude/claude_desktop_config.json"
        )
    else:  # Windows
        config_path = (
            Path(os.getenv("APPDATA") or "") / "Claude/claude_desktop_config.json"
        )

    # Check if config file exists
    if not config_path.exists():
        click.echo(
            f"Couldn't find claude_desktop_config.json at {config_path}. Have you installed the Claude Desktop app?"
        )
        sys.exit(1)

    try:
        # Read existing config
        with open(config_path, "r") as f:
            config = json.load(f)

        # Normalize key to match setup() format
        server_key = f"{SERVER_PREFIX}{provider.replace('_', '-')}"

        # Check if mcpServers exists and provider is configured
        if "mcpServers" not in config or server_key not in config["mcpServers"]:
            click.echo(f"Provider '{provider}' is not configured")
            return

        # Remove the provider
        del config["mcpServers"][server_key]

        # Remove mcpServers if it's empty
        if not config["mcpServers"]:
            del config["mcpServers"]

        # Write updated config
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        click.echo(
            f"Successfully removed MCP server configuration for provider '{provider}'. You can now restart Claude Desktop."
        )

    except Exception as e:
        click.echo(f"Error updating config file: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--local", is_flag=True, help="Force local development mode using absolute paths."
)
@click.option("--force", is_flag=True, help="Overwrite existing configurations.")
@click.option(
    "--individual-providers",
    is_flag=True,
    help="Also register every individual provider server (not recommended — prefer the default meta + aggregator setup).",
)
def setup_all(local: bool, force: bool, individual_providers: bool):
    """Setup Claude Desktop for full OpenData MCP access.

    By default registers two servers that together give Claude everything:

    \b
      opendata-mcp-meta   — 5 discovery tools (find-providers, describe-provider, …)
      opendata-mcp-all    — 300+ data tools aggregated from all providers

    This is equivalent to: uv run opendata-mcp setup opendata_mcp_meta

    Pass --individual-providers to also register every provider as its own
    separate server (55+ entries).  Not recommended unless you need to
    run providers on different ports or with different env vars.
    """
    try:
        system = platform.system()
        if system == "Darwin":
            config_path = (
                Path.home()
                / "Library/Application Support/Claude/claude_desktop_config.json"
            )
        elif system == "Windows":
            config_path = (
                Path(os.getenv("APPDATA") or "") / "Claude/claude_desktop_config.json"
            )
        else:
            click.echo("Only Windows and macOS are supported.")
            sys.exit(1)

        if not config_path.parent.exists():
            click.echo(f"Claude directory not found at {config_path.parent}")
            sys.exit(1)

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                click.echo(f"Error: {config_path} contains invalid JSON.")
                sys.exit(1)
        else:
            config = {}

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        repo_root = Path(__file__).parent.parent.resolve()
        is_local_repo = (repo_root / "pyproject.toml").exists()
        use_local = is_local_repo or local
        mode_label = "LOCAL" if use_local else "GLOBAL"

        registered = []

        # Always register the meta + aggregator pair.
        for provider in ("opendata_mcp_meta", "opendata_mcp_all"):
            key = f"{SERVER_PREFIX}{provider.replace('_', '-')}"
            if key in config["mcpServers"] and not force:
                click.echo(f"Skipping '{key}' (already exists). Use --force to overwrite.")
            else:
                config["mcpServers"][key] = _build_server_entry(provider, use_local, repo_root)
                click.echo(f"Registered {key} ({mode_label})")
                registered.append(key)

        # Optionally register every individual provider too.
        if individual_providers:
            import pkgutil
            import opendata_mcp.providers as providers_pkg

            skip = {"__template__", "opendata_mcp_meta", "opendata_mcp_all"}
            all_providers = [
                name
                for finder, name, ispkg in pkgutil.iter_modules(providers_pkg.__path__)
                if name not in skip
            ]
            for provider in sorted(all_providers):
                key = f"{SERVER_PREFIX}{provider.replace('_', '-')}"
                if key in config["mcpServers"] and not force:
                    click.echo(f"Skipping '{key}' (already exists). Use --force to overwrite.")
                    continue
                config["mcpServers"][key] = _build_server_entry(provider, use_local, repo_root)
                click.echo(f"Registered {key} ({mode_label})")
                registered.append(key)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        click.echo(
            f"\nConfigured {len(registered)} server(s). Please restart Claude Desktop."
        )

    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--apply",
    is_flag=True,
    help="Remove detected legacy entries and install the meta + aggregator pair.",
)
@click.option(
    "--local", is_flag=True, help="Force local development mode (used with --apply)."
)
def cleanup(apply: bool, local: bool):
    """Detect and remove legacy individual provider configurations.

    Scans Claude Desktop config for opendata-mcp-* entries that are individual
    data providers (not opendata-mcp-meta or opendata-mcp-all) and reports them.

    Without --apply: dry-run — lists what would be removed, no changes made.
    With --apply:    removes the legacy entries and installs the recommended
                     opendata-mcp-meta + opendata-mcp-all pair.

    \b
    Example workflow:
        uv run opendata-mcp cleanup            # preview changes
        uv run opendata-mcp cleanup --apply    # apply
    """
    system = platform.system()
    if system not in ["Darwin", "Windows"]:
        click.echo("This command is only supported on Windows and macOS")
        sys.exit(1)

    config_path = (
        Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
        if system == "Darwin"
        else Path(os.getenv("APPDATA") or "") / "Claude/claude_desktop_config.json"
    )

    if not config_path.exists():
        click.echo("No Claude Desktop config found — nothing to clean up.")
        return

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        click.echo(f"Error: {config_path} contains invalid JSON. Please fix it manually.")
        sys.exit(1)

    servers = config.get("mcpServers", {})
    keep = {f"{SERVER_PREFIX}meta", f"{SERVER_PREFIX}all"}

    legacy = [
        key for key in servers
        if key.startswith(SERVER_PREFIX) and key not in keep
    ]

    if not legacy:
        click.echo("No legacy opendata-mcp provider entries found.")
        has_meta = f"{SERVER_PREFIX}meta" in servers
        has_all = f"{SERVER_PREFIX}all" in servers
        if has_meta and has_all:
            click.echo("✓ Already running the recommended meta + aggregator setup.")
        else:
            click.echo("Tip: run `uv run opendata-mcp setup-all` to install the recommended setup.")
        return

    click.echo(f"Found {len(legacy)} legacy provider entry/entries:")
    for key in sorted(legacy):
        click.echo(f"  - {key}")

    if not apply:
        click.echo(
            f"\nDry run — no changes made. Re-run with --apply to remove these "
            f"and install opendata-mcp-meta + opendata-mcp-all."
        )
        return

    # Remove legacy entries.
    for key in legacy:
        del servers[key]
    click.echo(f"\nRemoved {len(legacy)} legacy entry/entries.")

    # Install meta + aggregator if not already present.
    repo_root = Path(__file__).parent.parent.resolve()
    is_local_repo = (repo_root / "pyproject.toml").exists()
    use_local = is_local_repo or local
    mode_label = "LOCAL" if use_local else "GLOBAL"

    installed = []
    for provider in ("opendata_mcp_meta", "opendata_mcp_all"):
        key = f"{SERVER_PREFIX}{provider.replace('_', '-')}"
        if key not in servers:
            servers[key] = _build_server_entry(provider, use_local, repo_root)
            click.echo(f"Installed {key} ({mode_label})")
            installed.append(key)
        else:
            click.echo(f"✓ {key} already present — keeping.")

    config["mcpServers"] = servers
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    click.echo("\nDone. Please restart Claude Desktop.")


@cli.command()
@click.argument("provider")
@click.option(
    "--local", is_flag=True, help="Force local development mode using absolute paths."
)
def inspect(provider: str, local: bool):
    """Launch MCP Inspector against a provider for interactive testing.

    Requires Node.js / npx. Opens a browser-based UI at http://localhost:5173
    where you can browse tools, send requests, and inspect responses.

    Example:
        uv run opendata-mcp inspect us_nasa
    """
    import shutil
    import subprocess

    if shutil.which("npx") is None:
        click.echo(
            "npx not found. Install Node.js (https://nodejs.org/) to use mcp-inspector.",
            err=True,
        )
        sys.exit(1)

    try:
        _import_provider_module(provider)
    except ImportError as e:
        click.echo(
            f"Provider '{provider}' not found or has missing dependencies.", err=True
        )
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    repo_root = Path(__file__).parent.parent.resolve()
    is_local_repo = (repo_root / "pyproject.toml").exists()

    if is_local_repo or local:
        server_cmd = [
            "uv",
            "--directory",
            str(repo_root),
            "run",
            LIB_NAME,
            "run",
            "--transport",
            "stdio",
            provider,
        ]
    else:
        server_cmd = ["uvx", LIB_NAME, "run", "--transport", "stdio", provider]

    click.echo(f"Starting MCP Inspector for provider '{provider}'…")
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


def main():
    cli()


if __name__ == "__main__":
    main()
