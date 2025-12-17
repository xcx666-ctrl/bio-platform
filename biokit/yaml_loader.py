from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict, Type


def load_yaml_file(path: Path, *, error_cls: Type[Exception]) -> Dict[str, Any]:
    """Load a YAML (or JSON) file with a graceful fallback when PyYAML is absent."""
    text = path.read_text(encoding="utf-8")

    yaml = None
    if importlib.util.find_spec("yaml"):
        yaml = importlib.import_module("yaml")

    if yaml is not None:
        data = yaml.safe_load(text) or {}
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover - exercised in runtime, hard to simulate
            raise error_cls(
                f"Unable to parse {path}. Install PyYAML or provide JSON-compatible YAML. Original error: {exc}"
            ) from exc

    if not isinstance(data, dict):
        raise error_cls(f"Expected a mapping in {path}, got {type(data).__name__}")

    return data
