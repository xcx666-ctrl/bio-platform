from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .config import ConfigError
from .plugins import ManifestError, discover_plugins
from .runner import execute

app = typer.Typer(help="BioKit: local-first bioinformatics analysis platform")
plugins_app = typer.Typer(help="Plugin management")


@app.command()
def version() -> None:
    """Show the installed BioKit version."""
    from . import __version__

    typer.echo(f"BioKit version: {__version__}")


@plugins_app.command("list")
def list_plugins() -> None:
    """List available plugins discovered from manifests."""
    try:
        plugins = discover_plugins()
    except ManifestError as exc:
        typer.echo(f"Error reading plugins: {exc}")
        raise typer.Exit(code=1)

    if not plugins:
        typer.echo("No plugins discovered.")
        raise typer.Exit()

    typer.echo("Available plugins:\n")
    for plugin in plugins.values():
        typer.echo(f"- {plugin.name} ({plugin.version}) : {plugin.description}")
        typer.echo(f"  Inputs: {', '.join(plugin.inputs)}")


@app.command()
def run(
    plugin: str = typer.Argument(..., help="Plugin name to execute"),
    config: Path = typer.Option(..., "--config", exists=True, readable=True, help="YAML config file"),
    manifest_root: Optional[Path] = typer.Option(None, help="Override plugin discovery root"),
) -> None:
    """Run a plugin with the provided configuration."""
    try:
        plugins = discover_plugins(plugin_root=manifest_root)
        if plugin not in plugins:
            available = ", ".join(sorted(plugins)) or "none"
            raise ManifestError(f"Plugin '{plugin}' not found. Available: {available}")

        run_dir = execute(plugins[plugin], config)
    except (ManifestError, ConfigError) as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)

    typer.echo(f"Run completed. Results stored at: {run_dir}")


app.add_typer(plugins_app, name="plugins")


if __name__ == "__main__":
    app()
