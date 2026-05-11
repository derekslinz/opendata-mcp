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
def run(provider: str):
    """Run a specific provider MCP server."""
    try:
        module = _import_provider_module(provider)
        anyio.run(module.main)
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


@cli.command()
@click.argument("provider")
@click.option(
    "--local", is_flag=True, help="Force local development mode using absolute paths."
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration.")
def setup(provider: str, local: bool, force: bool):
    """Setup the MCP server for use with Claude Desktop"""
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

    # Detection logic for local mode
    repo_root = Path(__file__).parent.parent.resolve()
    is_local_repo = (repo_root / "pyproject.toml").exists()

    if is_local_repo or local:
        # Use local execution via uv run
        config["mcpServers"][server_key] = {
            "command": "uv",
            "args": [
                "--directory",
                str(repo_root),
                "run",
                "opendata-mcp",
                "run",
                provider,
            ],
            "env": {
                "OTEL_SDK_DISABLED": "true"  # Optional: disable OTEL for cleaner logs if needed
            },
        }
        click.echo(f"Configuring in LOCAL mode pointing to {repo_root}")
    else:
        # Use global uvx
        config["mcpServers"][server_key] = {
            "command": "uvx",
            "args": [
                LIB_NAME,
                "run",
                provider,
            ],
        }
        click.echo(f"Configuring in GLOBAL mode using 'uvx {LIB_NAME}'")

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        click.echo(
            f"Successfully configured '{server_key}'. Please restart Claude Desktop."
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
def setup_all(local: bool, force: bool):
    """Setup all MCP servers for use with Claude Desktop"""
    try:
        import pkgutil
        import opendata_mcp.providers as providers_pkg

        providers = [
            name
            for finder, name, ispkg in pkgutil.iter_modules(providers_pkg.__path__)
            if name not in ("__template__", "__init__", "utils")
        ]

        if not providers:
            click.echo("No providers available to setup.")
            return

        # Check platform
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

        # Load config
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

        for provider in sorted(providers):
            server_key = f"{SERVER_PREFIX}{provider.replace('_', '-')}"
            if server_key in config["mcpServers"] and not force:
                click.echo(
                    f"Skipping '{server_key}' (already exists). Use --force to overwrite."
                )
                continue

            if is_local_repo or local:
                config["mcpServers"][server_key] = {
                    "command": "uv",
                    "args": [
                        "--directory",
                        str(repo_root),
                        "run",
                        "opendata-mcp",
                        "run",
                        provider,
                    ],
                }
                click.echo(f"Registered {provider} (LOCAL)")
            else:
                config["mcpServers"][server_key] = {
                    "command": "uvx",
                    "args": [
                        LIB_NAME,
                        "run",
                        provider,
                    ],
                }
                click.echo(f"Registered {provider} (GLOBAL)")

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        click.echo(
            f"\nSuccessfully configured {len(providers)} providers. Please restart Claude Desktop."
        )

    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


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
            provider,
        ]
    else:
        server_cmd = ["uvx", LIB_NAME, "run", provider]

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
