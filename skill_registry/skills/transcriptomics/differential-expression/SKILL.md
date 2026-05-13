# Transcriptomics differential expression analysis

## Purpose
Standardize RNA-seq differential expression analysis for count matrices, annotations, metadata, and reporting requirements.

## Use when
Use this skill when comparing gene expression between groups or testing expression associations with covariates.

## Inputs
- count_matrix
- gene_annotation
- metadata

## Outputs
- differential_gene_table
- volcano_plot_spec
- method_note
- risk_notes

## Primary tools
- DESeq2
- edgeR
- limma
- PyDESeq2

## Default strategy
Use count-aware differential expression methods, record the design formula, batch variables, sample size, normalization strategy, FDR method, and independent filtering behavior.

## Parameters
- design_formula
- contrast
- batch_variables
- fdr_threshold
- lfc_threshold
- normalization_strategy

## QC checks
- Confirm sample identifiers match count matrix and metadata.
- Confirm sample size per group and batch distribution.
- Check library size distribution and low-count filtering.
- Record FDR and multiple-testing correction.

## Interpretation limits
Differential expression indicates statistical association under the model, not direct mechanism. Low sample size and batch imbalance can dominate results.

## Risk notes
Batch effects, small sample size, unrecorded covariates, and multiple testing can create unstable or misleading findings.

## Next skills
- multiomics.correlation_network
- reporting.evidence_report_generation

## Review requirement
Expert review is required before gene-level interpretation, pathway claims, or report finalization.
