# Enrichment Plugin (GO / KEGG / GSEA)

This plugin performs functional enrichment for human gene sets using `clusterProfiler` and `org.Hs.eg.db`. It supports two input modes:

- **deg_table**: Differential expression table with columns `gene`, `log2FC`, `pvalue`, `padj`. Genes are filtered by `log2fc_cutoff` and `padj_cutoff` to build the gene list; the full table provides the ranked list for GSEA.
- **gene_list_background**: Predefined gene list plus a background gene universe.

## Dependencies
- R (>= 4.1 recommended)
- R packages: `clusterProfiler`, `org.Hs.eg.db`, `fgsea` (optional), `jsonlite`, `readr`, `dplyr`.
- KEGG support relies on internet access for pathway metadata; if offline, KEGG results may be empty.

## Files
- `manifest.yaml`: Plugin manifest for discovery
- `schema.yaml`: Human-readable config schema
- `enrichment.R`: Entrypoint script invoked by BioKit
- `configs/`: Example configs for both input modes
- `data/`: Example DEG table and gene lists

## Example configs

### DEG-driven enrichment
`plugins/enrichment/configs/example_deg.json`
```json
{
  "plugin": "enrichment",
  "input": {
    "type": "deg_table",
    "deg_path": "plugins/enrichment/data/deg_example.csv",
    "log2fc_cutoff": 1.0,
    "padj_cutoff": 0.05
  },
  "parameters": {
    "organism": "human",
    "ontology": "BP",
    "gsea": {
      "pvalue_cutoff": 0.25,
      "min_size": 5,
      "max_size": 500
    }
  }
}
```

### Gene list + background
`plugins/enrichment/configs/example_gene_list.json`
```json
{
  "plugin": "enrichment",
  "input": {
    "type": "gene_list_background",
    "gene_list_path": "plugins/enrichment/data/gene_list.txt",
    "background_path": "plugins/enrichment/data/background.txt"
  },
  "parameters": {
    "organism": "human",
    "ontology": "BP"
  }
}
```

## Running locally
After installing R packages, run:
```bash
biokit run enrichment --config plugins/enrichment/configs/example_deg.json
```
This writes outputs under `results/enrichment/<run_id>/`:
- `tables/go.tsv`, `tables/kegg.tsv`, `tables/gsea.tsv`
- `reports/report.html`
- `metadata.json` (BioKit), `metadata_r.json` (R session info)

If `Rscript` is unavailable or packages are missing, BioKit will still emit metadata and placeholder outputs; check `results/.../logs/run.log` for errors.
