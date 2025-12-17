#!/usr/bin/env Rscript
suppressWarnings({
  suppressMessages({
    library(jsonlite)
    library(readr)
    library(dplyr)
    library(ggplot2)
    library(pheatmap)
    library(DESeq2)
  })
})

`%||%` <- function(x, y) if (is.null(x) || length(x) == 0) y else x

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: differential_expression.R <config_json> <run_dir>")
}
config_path <- args[[1]]
run_dir <- args[[2]]

cfg <- jsonlite::fromJSON(config_path, simplifyVector = TRUE)
input <- cfg$input
params <- cfg$parameters %||% list()

run_tables <- file.path(run_dir, "tables")
run_reports <- file.path(run_dir, "reports")
dir.create(run_tables, showWarnings = FALSE, recursive = TRUE)
dir.create(run_reports, showWarnings = FALSE, recursive = TRUE)

counts_path <- input$counts_path
sample_sheet_path <- input$sample_sheet

counts_df <- readr::read_delim(counts_path, delim = ",", col_types = readr::cols())
if (!all(c("gene") %in% colnames(counts_df))) {
  stop("Counts file must have a 'gene' column followed by samples")
}
gene_ids <- counts_df$gene
count_matrix <- as.matrix(counts_df[ , -1])
mode(count_matrix) <- "integer"
rownames(count_matrix) <- gene_ids

samples <- readr::read_delim(sample_sheet_path, delim = "\t", col_types = readr::cols())
if (!all(c("sample", "condition") %in% colnames(samples))) {
  stop("Sample sheet must have columns: sample, condition")
}
if (!all(colnames(count_matrix) %in% samples$sample)) {
  stop("Sample IDs in counts do not match sample sheet")
}
samples <- samples[match(colnames(count_matrix), samples$sample), ]
samples$condition <- factor(samples$condition)
if (!is.null(params$reference_condition)) {
  samples$condition <- relevel(samples$condition, ref = params$reference_condition)
}

dds <- DESeqDataSetFromMatrix(countData = count_matrix, colData = samples, design = ~ condition)
dds <- DESeq(dds)
res <- results(dds)
res_df <- as.data.frame(res)
res_df$gene <- rownames(res_df)
res_df <- res_df %>% select(gene, baseMean, log2FoldChange, stat, pvalue, padj)
colnames(res_df)[colnames(res_df) == "log2FoldChange"] <- "log2FC"
res_df <- res_df[order(res_df$padj), ]

res_path <- file.path(run_tables, "deseq2_results.tsv")
readr::write_tsv(res_df, res_path)

# PCA plot
vsd <- vst(dds, blind = TRUE)
pca <- plotPCA(vsd, intgroup = "condition", returnData = TRUE)
pvar <- round(100 * attr(pca, "percentVar"), 1)
p_pca <- ggplot(pca, aes(PC1, PC2, color = condition)) +
  geom_point(size = 3) +
  xlab(paste0("PC1: ", pvar[1], "%")) +
  ylab(paste0("PC2: ", pvar[2], "%")) +
  theme_minimal()

pca_png <- file.path(run_reports, "pca.png")
ggsave(pca_png, p_pca, width = 6, height = 4, dpi = 150)

# Sample distance heatmap
dists <- dist(t(assay(vsd)))
dist_mat <- as.matrix(dists)
heat_png <- file.path(run_reports, "sample_distance.png")
pheatmap::pheatmap(dist_mat, filename = heat_png)

# Size factors
size_factors <- sizeFactors(dds)
size_png <- file.path(run_reports, "size_factors.png")
size_df <- data.frame(sample = names(size_factors), size_factor = size_factors)
p_sf <- ggplot(size_df, aes(sample, size_factor, fill = sample)) +
  geom_col() + theme_minimal() + theme(axis.text.x = element_text(angle = 45, hjust = 1))
ggsave(size_png, p_sf, width = 6, height = 4, dpi = 150)

# Simple HTML report
report_path <- file.path(run_reports, "qc.html")
html_lines <- c(
  "<html><head><title>DESeq2 QC</title></head><body>",
  sprintf("<h1>DESeq2 QC</h1>"),
  sprintf("<p>Design: ~ condition; reference: %s</p>", params$reference_condition %||% "(first level)"),
  sprintf("<p>Samples: %s</p>", paste(samples$sample, collapse = ", ")),
  sprintf("<p>Conditions: %s</p>", paste(levels(samples$condition), collapse = ", ")),
  "<h2>PCA</h2>", sprintf("<img src='pca.png' alt='PCA' width='600'>"),
  "<h2>Sample distance heatmap</h2>", sprintf("<img src='sample_distance.png' alt='Heatmap' width='600'>"),
  "<h2>Size factors</h2>", sprintf("<img src='size_factors.png' alt='Size factors' width='600'>"),
  "<p>DE results: tables/deseq2_results.tsv (gene, baseMean, log2FC, stat, pvalue, padj)</p>",
  "<p>This table can be used as input for the enrichment plugin with input.type=deg_table.</p>",
  "</body></html>"
)
writeLines(html_lines, con = report_path)

metadata_r <- list(
  sessionInfo = capture.output(utils::sessionInfo()),
  timestamp = as.character(Sys.time()),
  parameters = params,
  input_paths = list(counts_path = counts_path, sample_sheet = sample_sheet_path)
)
jsonlite::write_json(metadata_r, file.path(run_dir, "metadata_r.json"), auto_unbox = TRUE, pretty = TRUE)

message("[differential_expression] completed")
