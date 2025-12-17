from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .plugins import ALLOWED_INPUT_TYPES, Plugin
from .yaml_loader import load_yaml_file


class ConfigError(Exception):
    """Raised when the run configuration is invalid."""


def load_config(config_path: Path) -> Dict[str, Any]:
    path = config_path.resolve()
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    return load_yaml_file(path, error_cls=ConfigError)


def _require_fields(section: Dict[str, Any], required: set[str], context: str) -> None:
    missing = required - section.keys()
    if missing:
        raise ConfigError(
            f"Missing required fields in {context}: {', '.join(sorted(missing))}"
        )


def validate_config(config: Dict[str, Any], plugin: Plugin) -> Dict[str, Any]:
    if plugin.name != config.get("plugin", plugin.name):
        raise ConfigError(
            f"Config plugin '{config.get('plugin')}' does not match target plugin '{plugin.name}'"
        )

    if "input" not in config or not isinstance(config["input"], dict):
        raise ConfigError("Config must contain an 'input' mapping")

    input_block: Dict[str, Any] = config["input"]

    if "type" not in input_block:
        raise ConfigError("Input section must declare a 'type'")

    input_type = input_block["type"]
    if input_type not in ALLOWED_INPUT_TYPES:
        raise ConfigError(
            f"Unsupported input type '{input_type}'. Must be one of: {', '.join(sorted(ALLOWED_INPUT_TYPES))}"
        )
    if input_type not in plugin.inputs:
        raise ConfigError(
            f"Plugin '{plugin.name}' does not declare support for input type '{input_type}'"
        )

    if input_type == "counts":
        _require_fields(input_block, {"counts_path", "sample_sheet"}, "input.counts")
    elif input_type == "gene_list":
        _require_fields(input_block, {"gene_list_path"}, "input.gene_list")
    elif input_type == "deg_table":
        _require_fields(input_block, {"deg_path"}, "input.deg_table")
        input_block.setdefault("log2fc_cutoff", 1.0)
        input_block.setdefault("padj_cutoff", 0.05)
    elif input_type == "gene_list_background":
        _require_fields(
            input_block, {"gene_list_path", "background_path"}, "input.gene_list_background"
        )

    for key in [
        k
        for k in (
            "counts_path",
            "sample_sheet",
            "gene_list_path",
            "background_path",
            "deg_path",
        )
        if k in input_block
    ]:
        path = Path(input_block[key]).expanduser().resolve()
        if not path.is_file():
            raise ConfigError(f"Input file does not exist: {path}")
        input_block[key] = str(path)

    config["input"] = input_block
    config.setdefault("parameters", {})

    return config
