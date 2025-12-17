# BioKit Plugin Roadmap

This roadmap outlines a phased delivery of mainstream bioinformatics analysis plugins aligned with the current CLI-first, local-first BioKit architecture. Each phase balances quick wins (lightweight, local execution) with foundations for heavier workflows that may later integrate a workflow engine such as Nextflow.

## Version v0.1 — Foundation & Quick Wins
Focus: local, lightweight implementations with minimal external dependencies, leveraging existing plugin contract (manifest + entrypoint + results layout).

| Plugin | Inputs | Outputs | Primary Tools | Complexity | Reference/Indexes | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| differential_expression (DESeq2) | Counts matrix (TSV) + sample sheet | deseq2_results.tsv, qc.html, metadata | R/DESeq2 | 中 | None beyond annotation packages | Already implemented; feeds enrichment via deg_table. |
| enrichment (GO/KEGG/GSEA) | deg_table or gene_list (+background) | go.tsv, kegg.tsv, gsea.tsv, report.html, metadata | R/clusterProfiler, org.*.eg.db | 中 | OrgDb packages; KEGG online | Implemented; remains local-first. |
| QC/fastp | FASTQ pairs | reports (HTML), trimmed FASTQ | fastp | 低 | None | Good local-first; fast turnaround. |
| Count-matrix generator | FASTQ + simple genome index (STAR-lite or kallisto) | counts matrix, log | kallisto or salmon | 中 | Transcriptome index | Lightweight transcript-level quant; stays local if index exists. |
| Simple variant annotation | VCF | annotated.tsv/json, metadata | bcftools + snpEff (local db) | 中 | snpEff database | Keep local if db bundled/cached. |

Local-first priority: QC/fastp, differential_expression, enrichment, count-matrix generator (with prebuilt index). Workflow engine optional.

## Version v0.2 — Expanded Modalities & Basic Orchestration
Focus: cover more modalities; begin optional orchestration for multi-step tasks; still favor single-node execution where possible.

| Plugin | Inputs | Outputs | Primary Tools | Complexity | Reference/Indexes | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| RNA-seq aligned DE (STAR + DESeq2) | FASTQ + genome index + GTF | BAM, counts, DE tables, QC report | STAR, featureCounts/htseq-count, DESeq2 | 高 | STAR genome index, GTF | Multi-step; benefits from workflow engine for larger cohorts. |
| Small variant calling (germline) | FASTQ + reference FASTA + known sites | VCF, metrics, report | bwa-mem2, samtools, GATK HaplotypeCaller | 高 | BWA index, dict, known sites (dbSNP/known indels) | Complex; recommend Nextflow for robustness. |
| scRNA-seq basic (10x) | FASTQ + reference | count matrix, QC plots | Cell Ranger or STARsolo | 高 | 10x reference or STAR index | Resource-heavy; workflow engine recommended. |
| WGS/WES QC | FASTQ/BAM | QC HTML, coverage stats | fastp, samtools stats/idxstats, mosdepth | 中 | Reference FASTA for coverage | Can start local; Nextflow helpful for batching. |
| Metagenomics profiling (light) | FASTQ | taxonomic profile tsv, report | Kraken2 or Centrifuge | 中 | Kraken2/Centrifuge DB | Local if DB present; downloads are large. |

Local-first candidates: WGS/WES QC, metagenomics profiling (with pre-downloaded DB). Nextflow-friendly: RNA-seq aligned DE, germline calling, scRNA.

## Version v1.0 — Production-Grade Pipelines & Scalability
Focus: robust, multi-step, production-grade pipelines; strong reproducibility; clear Nextflow (or similar) integration for heavy workloads.

| Plugin | Inputs | Outputs | Primary Tools | Complexity | Reference/Indexes | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Somatic variant calling (tumor/normal) | FASTQ/BAM + reference + panels | VCF (somatic), purity metrics, report | bwa-mem2, GATK Mutect2, Funcotator/VEP | 高 | Reference index, known sites, panel-of-normals | Nextflow strongly recommended. |
| RNA fusion detection | FASTQ/BAM + reference | fusion calls, report | STAR-Fusion / Arriba | 高 | STAR-Fusion resources | Heavy compute; workflow engine needed. |
| scRNA-seq full stack | FASTQ + reference + cell/hash whitelists | expression matrix, clustering, DE, QC reports | Cell Ranger / STARsolo + Seurat/Scanpy | 高 | 10x reference/STAR index | Needs batching/orchestration; Nextflow or similar. |
| Spatial transcriptomics | FASTQ + slide layout | matrix, images, report | Space Ranger | 高 | Vendor references | Engine recommended. |
| Metagenomics assembly + binning | FASTQ | contigs, bins, taxonomy report | MEGAHIT, MetaBAT, GTDB-Tk | 高 | Databases (GTDB) | Compute-intensive; Nextflow. |
| Epigenomics (ChIP/ATAC) | FASTQ + reference | peak calls, QC, reports | bowtie2/bwa, MACS2, deepTools | 高 | Reference index | Multi-step; workflow engine advised. |

Local-light: none by default (datasets large); provide “mini” demo modes with toy references for offline validation. Nextflow (or similar) becomes default for these pipelines.

## Prioritization for Local-Light vs Workflow Engine
- Local-light (do first): fastp QC, count-matrix generator (kallisto/salmon with prebuilt index), differential_expression, enrichment, WGS/WES QC, metagenomics profiling with pre-downloaded DBs.
- Workflow-engine-first: RNA-seq aligned DE, germline calling, scRNA, somatic calling, fusion detection, spatial, assembly/binning, epigenomics.

## Implementation Notes
- Maintain manifest-driven discovery and the standardized output contract (`results/<plugin>/<run_id>/logs|reports|tables|metadata.json`).
- For heavy pipelines, wrap Nextflow as the entrypoint while still emitting BioKit metadata and contract-compliant outputs.
- Provide “demo configs” and tiny test datasets for each plugin to keep CI local and fast; full production references downloaded separately.
