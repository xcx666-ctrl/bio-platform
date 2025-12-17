from pathlib import Path

import pytest

from biokit.config import ConfigError, validate_config
from biokit.plugins import load_manifest


@pytest.fixture()
def example_plugin() -> Path:
    return Path(__file__).resolve().parent.parent / "plugins" / "example" / "manifest.yaml"


@pytest.fixture()
def enrichment_plugin() -> Path:
    return Path(__file__).resolve().parent.parent / "plugins" / "enrichment" / "manifest.yaml"


def test_validate_config_counts(tmp_path: Path, example_plugin: Path):
    counts = tmp_path / "counts.csv"
    samples = tmp_path / "samples.csv"
    counts.write_text("gene,a\nb,1", encoding="utf-8")
    samples.write_text("sample,group\ns1,A", encoding="utf-8")

    plugin = load_manifest(example_plugin)
    config = {
        "plugin": "example",
        "input": {
            "type": "counts",
            "counts_path": counts,
            "sample_sheet": samples,
        },
        "parameters": {"alpha": 0.05},
    }

    validated = validate_config(config, plugin)
    assert validated["input"]["counts_path"].endswith("counts.csv")


def test_validate_config_mismatched_plugin(tmp_path: Path, example_plugin: Path):
    gene_list = tmp_path / "genes.txt"
    gene_list.write_text("gene1\ngene2", encoding="utf-8")

    plugin = load_manifest(example_plugin)
    config = {
        "plugin": "wrong",
        "input": {"type": "gene_list", "gene_list_path": gene_list},
    }

    with pytest.raises(ConfigError):
        validate_config(config, plugin)


def test_validate_gene_list_background(tmp_path: Path, enrichment_plugin: Path):
    gene_list = tmp_path / "genes.txt"
    background = tmp_path / "background.txt"
    gene_list.write_text("gene1\ngene2", encoding="utf-8")
    background.write_text("gene1\ngene2\ngene3", encoding="utf-8")

    plugin = load_manifest(enrichment_plugin)
    config = {
        "plugin": "enrichment",
        "input": {
            "type": "gene_list_background",
            "gene_list_path": gene_list,
            "background_path": background,
        },
    }

    validated = validate_config(config, plugin)
    assert validated["input"]["background_path"].endswith("background.txt")
