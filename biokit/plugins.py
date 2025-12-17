from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

ALLOWED_INPUT_TYPES = {"counts", "gene_list", "deg_table", "gene_list_background"}

from .yaml_loader import load_yaml_file


class ManifestError(Exception):
    """Raised when a plugin manifest is invalid."""


@dataclass
class Plugin:
    name: str
    version: str
    description: str
    inputs: List[str]
    path: Path
    manifest_path: Path
    entrypoint: str | None = None


def validate_manifest_data(data: dict, manifest_path: Path) -> None:
    required_fields = {"name", "version", "description", "inputs"}
    missing = required_fields - data.keys()
    if missing:
        raise ManifestError(
            f"Manifest {manifest_path} missing required fields: {', '.join(sorted(missing))}"
        )

    invalid_inputs = set(data.get("inputs", [])) - ALLOWED_INPUT_TYPES
    if invalid_inputs:
        raise ManifestError(
            f"Manifest {manifest_path} has unsupported input types: {', '.join(sorted(invalid_inputs))}"
        )


def load_manifest(manifest_path: Path) -> Plugin:
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise ManifestError(f"Manifest {manifest_path} does not exist")

    data = load_yaml_file(manifest_path, error_cls=ManifestError)
    validate_manifest_data(data, manifest_path)

    plugin_dir = manifest_path.parent

    return Plugin(
        name=data["name"],
        version=str(data["version"]),
        description=data["description"],
        inputs=list(data["inputs"]),
        path=plugin_dir,
        manifest_path=manifest_path,
        entrypoint=data.get("entrypoint"),
    )


def discover_plugins(plugin_root: Path | None = None) -> Dict[str, Plugin]:
    base_dir = plugin_root or Path(__file__).resolve().parent.parent / "plugins"
    plugins: Dict[str, Plugin] = {}

    if not base_dir.exists():
        return plugins

    for manifest_path in base_dir.glob("*/manifest.yaml"):
        plugin = load_manifest(manifest_path)
        if plugin.name in plugins:
            raise ManifestError(f"Duplicate plugin name detected: {plugin.name}")
        plugins[plugin.name] = plugin

    return plugins
