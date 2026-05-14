# Metabolomics differential metabolite analysis

## Purpose
Standardize differential metabolite analysis for peak tables, metabolite annotations, sample metadata, and reporting constraints.

## Use when
Use this skill when comparing metabolite abundance or intensity between groups or testing metabolite associations with phenotypes.

## Inputs
- peak_table
- metabolite_annotation
- metadata

## Outputs
- differential_metabolite_table
- pathway_enrichment_spec
- method_note
- risk_notes

## Primary tools
- MetaboAnalystR
- pyOpenMS
- custom statistical scripts

## Default strategy
Record peak table preprocessing, normalization, transformation, missing-value handling, annotation confidence level, covariates, and multiple-testing correction.

## Parameters
- grouping_variable
- contrast
- normalization_strategy
- transformation
- missing_value_policy
- fdr_threshold
- annotation_level

## QC checks
- Confirm sample identifiers match peak table and metadata.
- Check missingness by feature and by sample.
- Record normalization and batch-correction steps.
- Record metabolite annotation level and database source.

## Interpretation limits
Differential peaks or metabolites depend on preprocessing and annotation confidence. A named metabolite with weak annotation should not be treated as confirmed identity.

## Risk notes
Metabolite annotation level, batch effects, peak table normalization, drift correction, and missing-value handling must be recorded.

## Next skills
- multiomics.correlation_network
- reporting.evidence_report_generation

## Review requirement
Expert review is required before biological pathway interpretation or biomarker reporting.
