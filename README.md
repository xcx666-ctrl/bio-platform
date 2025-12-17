# BioKit: Local-first Bioinformatics Platform

BioKit is a CLI-first, plugin-driven bioinformatics platform that favors local execution and reproducibility.

## Repository Layout
```
biokit/                 # Core Python package
  cli.py                # Typer-based CLI entrypoint
  config.py             # Config loading and validation
  plugins.py            # Manifest parsing and plugin discovery
  runner.py             # Run orchestration, metadata capture
plugins/
  example/
    manifest.yaml       # Example plugin manifest
    plugin.py           # Placeholder plugin module
  differential_expression/
    manifest.yaml       # DESeq2 plugin manifest
    differential_expression.R  # R entrypoint
    README.md           # Usage and configs
    configs/            # Example configs
    data/               # Example counts + sample sheet
  enrichment/
    manifest.yaml       # GO/KEGG/GSEA plugin manifest
    enrichment.R        # R entrypoint
    README.md           # Usage and configs
    configs/            # Example configs
    data/               # Example DEG table and gene lists
results/                # Output root (run artifacts materialize here)
tests/                  # Pytest suite
pyproject.toml          # Project metadata and dependencies
```

## Plugin Manifest Contract
Each plugin lives under `plugins/<name>` and must include a `manifest.yaml`.

Supported input types include:
- `counts`: counts matrix + sample sheet (example plugin)
- `gene_list`: newline-delimited identifiers (example plugin)
- `counts`: counts matrix + sample sheet (differential_expression plugin)
- `deg_table`: differential expression table with gene/log2FC/pvalue/padj (enrichment plugin)
- `gene_list_background`: gene list plus background universe (enrichment plugin)

If PyYAML is not installed, manifests and configs must remain JSON-compatible.

## Run Configuration Contract
A run config is a YAML/JSON mapping that names the plugin, declares the input, and adds optional parameters. Examples:

**Counts matrix + sample sheet (example plugin)**
```json
{ "plugin": "example", "input": { "type": "counts", "counts_path": "data/counts.csv", "sample_sheet": "data/samples.csv" }, "parameters": { "alpha": 0.05 } }
```

**Gene list (example plugin)**
```json
{ "plugin": "example", "input": { "type": "gene_list", "gene_list_path": "data/genes.txt" }, "parameters": {} }
```

**DEG table (enrichment plugin)**
```json
{ "plugin": "enrichment", "input": { "type": "deg_table", "deg_path": "plugins/enrichment/data/deg_example.csv", "log2fc_cutoff": 1.0, "padj_cutoff": 0.05 }, "parameters": { "organism": "human", "ontology": "BP" } }
```

**Gene list + background (enrichment plugin)**
```json
{ "plugin": "enrichment", "input": { "type": "gene_list_background", "gene_list_path": "plugins/enrichment/data/gene_list.txt", "background_path": "plugins/enrichment/data/background.txt" }, "parameters": { "organism": "human" } }
```

**Counts matrix + sample sheet (differential_expression plugin)**
```json
{ "plugin": "differential_expression", "input": { "type": "counts", "counts_path": "plugins/differential_expression/data/counts.tsv", "sample_sheet": "plugins/differential_expression/data/samples.tsv" }, "parameters": { "reference_condition": "control" } }
```

The run will fail early if required files are missing.

## CLI Usage
Install dependencies in a virtual environment, then install the package in editable mode (optional):

```bash
pip install -e .
```

The CLI depends on [`typer`](https://typer.tiangolo.com/) (declared in `pyproject.toml`).
If PyPI is unreachable, you can still run the library modules directly as long as dependencies are present locally.

Help and plugin discovery:
```bash
biokit --help
biokit plugins list
```

Running a plugin:
```bash
biokit run example --config config.json
biokit run differential_expression --config plugins/differential_expression/configs/example_counts.json
biokit run enrichment --config plugins/enrichment/configs/example_deg.json
```

Outputs follow the enforced layout `results/<plugin>/<run_id>/` with subfolders `logs/`, `reports/`, `tables/`, and a `metadata.json` capturing config, input hashes, and environment snapshots.

## Tests
Run the basic pytest suite:
```bash
pytest
```
