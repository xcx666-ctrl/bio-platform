from pathlib import Path

import pytest

from biokit.plugins import ManifestError, discover_plugins, load_manifest


def test_load_manifest_success():
    manifest = Path(__file__).resolve().parent.parent / "plugins" / "example" / "manifest.yaml"
    plugin = load_manifest(manifest)
    assert plugin.name == "example"
    assert "counts" in plugin.inputs


def test_load_manifest_missing_field(tmp_path: Path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("name: bad\nversion: 1.0\n", encoding="utf-8")

    with pytest.raises(ManifestError):
        load_manifest(manifest)


def test_discover_plugins_finds_example():
    plugins = discover_plugins(Path(__file__).resolve().parent.parent / "plugins")
    assert "example" in plugins
