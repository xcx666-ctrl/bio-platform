#!/usr/bin/env Rscript
suppressWarnings({
  suppressMessages({
    library(jsonlite)
    library(dplyr)
    library(readr)
    library(clusterProfiler)
    library(org.Hs.eg.db)
  })
})

`%||%` <- function(x, y) if (is.null(x) || length(x) == 0) y else x

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: enrichment.R <config_json> <run_dir>")
}
config_path <- args[[1]]
run_dir <- args[[2]]

cfg <- jsonlite::fromJSON(config_path, simplifyVector = TRUE)
input <- cfg$input
params <- cfg$parameters %||% list()

ontology <- params$ontology %||% "BP"
organism <- params$organism %||% "human"
gsea_params <- params$gsea %||% list()

run_tables <- file.path(run_dir, "tables")
run_reports <- file.path(run_dir, "reports")
dir.create(run_tables, showWarnings = FALSE, recursive = TRUE)
dir.create(run_reports, showWarnings = FALSE, recursive = TRUE)

message("[enrichment] input type: ", input$type)

resolve_gene_ids <- function(symbols) {
  unique_symbols <- unique(symbols)
  mapping <- bitr(unique_symbols, fromType = "SYMBOL", toType = "ENTREZID", OrgDb = org.Hs.eg.db)
  mapping <- mapping[!is.na(mapping$ENTREZID), ]
  unique(mapping$ENTREZID)
}

# Load and prepare gene sets
if (identical(input$type, "deg_table")) {
  deg_path <- input$deg_path
  log2fc_cutoff <- as.numeric(input$log2fc_cutoff %||% 1.0)
  padj_cutoff <- as.numeric(input$padj_cutoff %||% 0.05)

  deg <- readr::read_csv(deg_path, show_col_types = FALSE)
  required_cols <- c("gene", "log2FC", "pvalue", "padj")
  missing_cols <- setdiff(required_cols, colnames(deg))
  if (length(missing_cols) > 0) {
    stop("Missing columns in deg table: ", paste(missing_cols, collapse = ", "))
  }

  gene_list <- deg %>% filter(!is.na(padj), padj <= padj_cutoff, abs(log2FC) >= log2fc_cutoff) %>% pull(gene)
  background <- deg$gene

  # Build ranked list for GSEA (named by Entrez IDs)
  rank_vector <- deg$log2FC
  names(rank_vector) <- deg$gene
  rank_vector <- sort(rank_vector, decreasing = TRUE)
  gene_map <- bitr(names(rank_vector), fromType = "SYMBOL", toType = "ENTREZID", OrgDb = org.Hs.eg.db)
  gene_map <- gene_map[!is.na(gene_map$ENTREZID), ]
  rank_vector <- rank_vector[gene_map$SYMBOL]
  names(rank_vector) <- gene_map$ENTREZID
} else if (identical(input$type, "gene_list_background")) {
  gene_list <- readLines(input$gene_list_path)
  background <- readLines(input$background_path)
  rank_vector <- NULL
} else {
  stop("Unsupported input type: ", input$type)
}

# Convert to Entrez IDs
foreground_ids <- resolve_gene_ids(gene_list)
background_ids <- resolve_gene_ids(background)
if (length(foreground_ids) == 0) {
  stop("No genes left after ID mapping; check identifiers.")
}

# GO enrichment
message("[enrichment] running GO (ontology=", ontology, ")")
go_res <- tryCatch(
  enrichGO(
    gene = foreground_ids,
    OrgDb = org.Hs.eg.db,
    keyType = "ENTREZID",
    ont = ontology,
    universe = background_ids,
    pAdjustMethod = "BH",
    readable = TRUE
  ),
  error = function(e) e
)

go_path <- file.path(run_tables, "go.tsv")
if (inherits(go_res, "enrichResult")) {
  readr::write_tsv(as.data.frame(go_res), go_path)
} else {
  readr::write_tsv(tibble(message = paste("GO error:", go_res$message)), go_path)
}

# KEGG enrichment (human -> hsa)
message("[enrichment] running KEGG")
kegg_res <- tryCatch(
  enrichKEGG(gene = foreground_ids, organism = "hsa", universe = background_ids, pAdjustMethod = "BH"),
  error = function(e) e
)

kegg_path <- file.path(run_tables, "kegg.tsv")
if (inherits(kegg_res, "enrichResult")) {
  readr::write_tsv(as.data.frame(kegg_res), kegg_path)
} else {
  readr::write_tsv(tibble(message = paste("KEGG error:", kegg_res$message)), kegg_path)
}

# GSEA using clusterProfiler::GSEA
gsea_path <- file.path(run_tables, "gsea.tsv")
if (!is.null(rank_vector)) {
  message("[enrichment] running GSEA")
  gsea_res <- tryCatch(
    GSEA(
      geneList = rank_vector,
      minGSSize = as.integer(gsea_params$min_size %||% 10),
      maxGSSize = as.integer(gsea_params$max_size %||% 500),
      pvalueCutoff = as.numeric(gsea_params$pvalue_cutoff %||% 0.25),
      pAdjustMethod = "BH"
    ),
    error = function(e) e
  )
  if (inherits(gsea_res, "gseaResult")) {
    readr::write_tsv(as.data.frame(gsea_res), gsea_path)
  } else {
    readr::write_tsv(tibble(message = paste("GSEA error:", gsea_res$message)), gsea_path)
  }
} else {
  readr::write_tsv(tibble(message = "GSEA skipped (no ranking available)"), gsea_path)
}

# Simple HTML report
report_path <- file.path(run_reports, "report.html")
html_lines <- c(
  "<html><head><title>BioKit Enrichment Report</title></head><body>",
  sprintf("<h1>BioKit Enrichment (%s)</h1>", input$type),
  sprintf("<p>Ontology: %s</p>", ontology),
  sprintf("<p>Genes: %d; Background: %d</p>", length(foreground_ids), length(background_ids)),
  sprintf("<p>GO rows: %d; KEGG rows: %d; GSEA rows: %s</p>",
          if (inherits(go_res, "enrichResult")) nrow(as.data.frame(go_res)) else 0,
          if (inherits(kegg_res, "enrichResult")) nrow(as.data.frame(kegg_res)) else 0,
          if (!is.null(rank_vector)) if (exists("gsea_res") && inherits(gsea_res, "gseaResult")) nrow(as.data.frame(gsea_res)) else 0 else "n/a"),
  "<p>See tables directory for full results.</p>",
  "</body></html>"
)
writeLines(html_lines, con = report_path)

# R metadata
metadata_r <- list(
  sessionInfo = capture.output(utils::sessionInfo()),
  timestamp = as.character(Sys.time()),
  input_type = input$type,
  ontology = ontology,
  organism = organism
)
jsonlite::write_json(metadata_r, file.path(run_dir, "metadata_r.json"), auto_unbox = TRUE, pretty = TRUE)

message("[enrichment] completed")
