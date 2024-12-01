import importlib
import sys

import anyio
import click


@click.group()
def cli():
    """OpenSwissMCP CLI tool"""
    pass


@cli.command()
@click.argument("provider")
def run(provider: str):
    """Run a specific provider MCP server."""
    try:
        module = importlib.import_module(f"osmcp.providers.{provider}")
        anyio.run(module.main)
    except ImportError:
        click.echo(f"Provider '{provider}' not found.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error running provider: {e}")
        sys.exit(1)


@cli.command()
def list():
    """List all available providers"""
    try:
        import pkgutil

        import osmcp.providers as providers_pkg

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
        module = importlib.import_module(f"osmcp.providers.{provider}")

        click.echo(f"Provider: {provider}")
        if hasattr(module, "__doc__") and module.__doc__:
            click.echo(f"Description: {module.__doc__.strip()}")
        if hasattr(module, "SUPPORTED_TYPES"):
            click.echo(f"Supported types: {', '.join(module.SUPPORTED_TYPES)}")
    except ImportError:
        click.echo(f"Provider '{provider}' not found. Make sure it's installed with:")
        click.echo(f"uv pip install 'osmcp[{provider}]'")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error getting provider info: {e}")
        sys.exit(1)


@cli.command()
def version():
    """Show the OSMCP version"""
    try:
        from importlib.metadata import version as get_version

        try:
            ver = get_version("osmcp")
        except importlib.metadata.PackageNotFoundError:
            # Fallback to reading version from __init__.py
            from osmcp import __version__ as ver
        click.echo(f"OSMCP version: {ver}")
    except Exception as e:
        click.echo(f"Error getting OSMCP version: {e}")
        sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
