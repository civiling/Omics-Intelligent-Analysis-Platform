# Single-cell RNA-seq data ingestion and format detection

## Purpose

Register local single-cell RNA-seq expression matrix files as platform objects and produce a data readiness summary for downstream metadata and workflow decisions.

## Use when

Use this skill when a user uploads or points the platform at a directory of single-cell expression matrices that need format detection before analysis.

## Inputs

- matrix_directory

## Outputs

- expression_matrix_manifest
- sample_metadata_template
- data_readiness_report
- method_note
- risk_notes

## Primary tools

- platform MatrixFormatInspector
- platform DataIngestionService

## Default strategy

Scan supported matrix files, infer sample ids from filenames, detect matrix orientation, raw count status, organism, gene identifier type, dimensions, and register UploadedFile, ExpressionMatrix, and SampleMetadata draft objects.

## Parameters

- project_name
- dataset_name
- organism
- disease_context

## QC checks

- Check matrix dimensions.
- Check raw integer count compatibility.
- Check matrix orientation.
- Check duplicated row identifiers.
- Check empty rows and columns.

## Interpretation limits

Format detection does not perform biological QC, clustering, annotation, or differential expression. Inferred metadata must be reviewed before formal analysis.

## Risk notes

Filename-derived sample ids and organism inference are heuristic. Metadata fields such as condition, patient_id, and batch require user confirmation.

## Next skills

- scrna.metadata_design
- reporting.evidence_report_generation

## Review requirement

Expert review is optional for ingestion, but metadata confirmation is required before formal statistical conclusions.
