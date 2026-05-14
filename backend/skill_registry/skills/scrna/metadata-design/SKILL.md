# Single-cell RNA-seq metadata and experiment design recognition

## Purpose

Import sample metadata, identify the experimental design, and recommend the appropriate single-cell analysis mode with a confidence gate.

## Use when

Use this skill after expression matrices have been registered and the user provides a sample-level metadata table.

## Inputs

- platform_store
- metadata_table

## Outputs

- metadata_import_report
- experiment_design_summary
- analysis_mode_recommendation
- confidence_gate_result
- sample_metadata_template
- method_note
- risk_notes

## Primary tools

- platform MetadataDesignService

## Default strategy

Copy the current platform object store into the workflow output directory, import metadata by sample id, GSM accession, or file name, then evaluate condition counts, biological replicates, patient pairing, batch availability, and raw count readiness.

## Parameters

- dataset_id
- confirm
- min_replicates_per_condition

## QC checks

- Check condition availability.
- Check at least two condition groups for group comparisons.
- Check per-condition replicate counts.
- Check patient pairing when patient_id exists.
- Check valid raw count matrices are available.

## Interpretation limits

This workflow determines analysis eligibility but does not execute QC, clustering, annotation, pseudobulk aggregation, or differential expression.

## Risk notes

Formal pseudobulk recommendations require correct metadata. If condition, patient_id, or batch are wrong, downstream statistical models will be wrong.

## Next skills

- transcriptomics.differential_expression
- reporting.evidence_report_generation

## Review requirement

Expert review is optional for metadata parsing, but the user must confirm sample metadata before formal statistical analysis.
