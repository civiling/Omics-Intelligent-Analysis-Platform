# Differential abundance analysis

## Purpose
Standardize differential microbiome abundance analysis and make compositional data assumptions explicit.

## Use when
Use this skill when comparing microbial taxa, ASVs, OTUs, or functional features between groups or along covariates.

## Inputs
- feature_table
- taxonomy_table
- metadata

## Outputs
- differential_taxa_table
- volcano_plot_spec
- method_note
- risk_notes

## Primary tools
- ANCOM-BC2
- ALDEx2
- MaAsLin2

## Default strategy
Prefer methods designed for compositional microbiome data. Record normalization, covariates, contrasts, multiple-testing correction, and the chosen effect-size definition.

## Parameters
- grouping_variable
- contrast
- covariates
- prevalence_filter
- fdr_threshold
- normalization_strategy

## QC checks
- Confirm sample identifiers match feature and metadata tables.
- Confirm group sizes and covariate completeness.
- Check feature sparsity and prevalence filters.
- Record FDR method and adjusted p-value threshold.

## Interpretation limits
Relative abundance changes do not necessarily imply absolute microbial load changes. A simple t-test on relative abundance cannot be treated as final evidence.

## Risk notes
Microbiome tables are compositional and sparse. Method choice, zero handling, prevalence filters, and covariate modeling can materially change results.

## Next skills
- multiomics.correlation_network
- reporting.evidence_report_generation

## Review requirement
Expert review is required before biological claims, biomarker nomination, or report finalization.
