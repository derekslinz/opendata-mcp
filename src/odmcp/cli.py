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


@click.group()
def cli():
    """OpenDataMCP CLI tool"""
    pass


@cli.command()
@click.argument("provider")
def run(provider: str):
    """Run a specific provider MCP server."""
    try:
        module = importlib.import_module(f"odmcp.providers.{provider}")
        anyio.run(module.main)
    except ImportError as e:
        import traceback

        click.echo(
            f"Provider '{provider}' not found or has missing dependencies.", err=True
        )
        click.echo(f"Error: {e}", err=True)
        # Optional: traceback.print_exc()
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

        import odmcp.providers as providers_pkg

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
        module = importlib.import_module(f"odmcp.providers.{provider}")

        click.echo(f"Provider: {provider}")
        if hasattr(module, "__doc__") and module.__doc__:
            click.echo(f"Description: {module.__doc__.strip()}")
        if hasattr(module, "SUPPORTED_TYPES"):
            click.echo(f"Supported types: {', '.join(module.SUPPORTED_TYPES)}")
    except ImportError:
        click.echo(f"Provider '{provider}' not found. Make sure it's installed with:")
        click.echo(f"uv pip install 'odmcp[{provider}]'")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error getting provider info: {e}")
        sys.exit(1)


@cli.command()
def version():
    """Show the odmcp version"""
    try:
        from importlib.metadata import version as get_version

        try:
            ver = get_version("odmcp")
        except importlib.metadata.PackageNotFoundError:
            # Fallback to reading version from __init__.py
            from odmcp import __version__ as ver
        click.echo(f"odmcp version: {ver}")
    except Exception as e:
        click.echo(f"Error getting odmcp version: {e}")
        sys.exit(1)


@cli.command()
@click.argument("provider")
def setup(provider: str):
    """Setup the MCP server for use with Claude Desktop"""
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
        config_path = Path(os.getenv("APPDATA")) / "Claude/claude_desktop_config.json"

    # Check if config directory exists
    if not config_path.parent.exists():
        click.echo(
            f"Couldn't find Claude configuration directory at {config_path.parent}. Have you installed the Claude Desktop app?"
        )
        sys.exit(1)

    # Create config file if it doesn't exist
    if not config_path.exists():
        with open(config_path, "w") as f:
            json.dump({}, f, indent=2)

    try:
        # Read existing config
        with open(config_path, "r") as f:
            config = json.load(f)

        # Get the package version
        try:
            from importlib.metadata import version as get_version

            get_version("odmcp")
        except importlib.metadata.PackageNotFoundError:
            # Fallback to reading version from __init__.py
            pass

        # Add or update mcpServers entry
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"][f"odmcp-{provider.replace('_', '-')}"] = {
            "command": "uv",
            "args": [
                "run",
                "--python",
                "3.12",
                "python",
                str(Path(__file__).resolve()),
                "run",
                provider,
            ],
            "cwd": str(Path(__file__).resolve().parent.parent.parent),
            "env": {"PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
        }

        # Write updated config
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        click.echo(
            f"Successfully configured MCP server for provider '{provider}'. You can now restart Claude Desktop."
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
        config_path = Path(os.getenv("APPDATA")) / "Claude/claude_desktop_config.json"

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

        # Check if mcpServers exists and provider is configured
        if "mcpServers" not in config or provider not in config["mcpServers"]:
            click.echo(f"Provider '{provider}' is not configured")
            return

        # Remove the provider
        del config["mcpServers"][provider]

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
def setup_all():
    """Setup all MCP servers for use with Claude Desktop"""
    try:
        import pkgutil
        import odmcp.providers as providers_pkg

        # Get all providers
        providers = [
            name
            for finder, name, ispkg in pkgutil.iter_modules(providers_pkg.__path__)
            if name not in ("__template__", "__init__", "utils")
        ]

        if not providers:
            click.echo("No providers available to setup.")
            return

        # Check platform and config path
        system = platform.system()
        if system == "Darwin":
            config_path = (
                Path.home()
                / "Library/Application Support/Claude/claude_desktop_config.json"
            )
        elif system == "Windows":
            config_path = (
                Path(os.getenv("APPDATA")) / "Claude/claude_desktop_config.json"
            )
        else:
            click.echo("Only Windows and macOS are supported.")
            sys.exit(1)

        if not config_path.parent.exists():
            click.echo(f"Claude directory not found at {config_path.parent}")
            sys.exit(1)

        # Build config
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            config = {}

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Get version
        try:
            from importlib.metadata import version as get_version

            get_version("odmcp")
        except Exception:
            pass

        for provider in providers:
            config["mcpServers"][f"odmcp-{provider.replace('_', '-')}"] = {
                "command": "uv",
                "args": [
                    "run",
                    "--python",
                    "3.12",
                    "python",
                    str(Path(__file__).resolve()),
                    "run",
                    provider,
                ],
                "cwd": str(Path(__file__).resolve().parent.parent.parent),
                "env": {"PYTHONPATH": str(Path(__file__).resolve().parent.parent)},
            }
            click.echo(f"Registered {provider}")

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        click.echo(
            f"\nSuccessfully configured {len(providers)} providers. Please restart Claude Desktop."
        )

    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
