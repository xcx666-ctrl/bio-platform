# Differential Expression Plugin (DESeq2)

Performs differential expression using `DESeq2` on a counts matrix and sample sheet. Outputs are compatible with the enrichment plugin (`input.type=deg_table`).

## Inputs
- `counts_path` (TSV): First column `gene`, remaining columns are sample IDs with integer counts.
- `sample_sheet` (TSV): Columns `sample`, `condition`. Samples must match count column names.

## Outputs
- `tables/deseq2_results.tsv`: Columns `gene`, `baseMean`, `log2FC`, `stat`, `pvalue`, `padj`. This file can be fed to the enrichment plugin as `deg_path`.
- `reports/qc.html`: Quick report with PCA, sample distance heatmap, and size factor summary.
- `metadata.json` and `metadata_r.json`: Parameters, versions, and session info.

## Example config
`plugins/differential_expression/configs/example_counts.json`
```json
{
  "plugin": "differential_expression",
  "input": {
    "type": "counts",
    "counts_path": "plugins/differential_expression/data/counts.tsv",
    "sample_sheet": "plugins/differential_expression/data/samples.tsv"
  },
  "parameters": {
    "reference_condition": "control"
  }
}
```

## Run
```bash
biokit run differential_expression --config plugins/differential_expression/configs/example_counts.json
```

To chain into enrichment:
```bash
enrichment_cfg=$(mktemp)
cat > "$enrichment_cfg" <<'JSON'
{
  "plugin": "enrichment",
  "input": {
    "type": "deg_table",
    "deg_path": "REPLACE_WITH_RESULTS_PATH/tables/deseq2_results.tsv",
    "log2fc_cutoff": 1.0,
    "padj_cutoff": 0.05
  },
  "parameters": {"organism": "human", "ontology": "BP"}
}
JSON
# Replace REPLACE_WITH_RESULTS_PATH with the actual run directory from DE run
biokit run enrichment --config "$enrichment_cfg"
```
