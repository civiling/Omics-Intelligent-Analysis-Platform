# Microbiome read and feature table QC

## Purpose
Standardize basic quality-control review for microbiome reads, ASV/OTU feature tables, taxonomy tables, and sample metadata.

## Use when
Use this skill before downstream microbiome statistics, or when uploaded microbiome data need a structured QC checklist and filtering recommendation.

## Inputs
- reads
- feature_table
- taxonomy_table
- metadata

## Outputs
- qc_summary
- filtering_recommendation
- method_note
- risk_notes

## Primary tools
- FastQC
- MultiQC
- QIIME 2
- DADA2

## Default strategy
Record read depth, sample retention, feature retention, taxonomy availability, missing metadata, and any planned filtering thresholds. The registry only specifies this review and does not run the tools.

## Parameters
- min_reads_per_sample
- min_feature_prevalence
- taxonomy_confidence_threshold
- missing_metadata_policy

## QC checks
- Confirm sample identifiers are consistent across tables.
- Check read depth distribution and low-depth samples.
- Check feature prevalence and extreme sparsity.
- Check taxonomy table coverage and unassigned feature fraction.

## Interpretation limits
QC summaries do not establish biological differences. Filtering choices can change downstream conclusions and must be recorded.

## Risk notes
Over-aggressive filtering may remove rare but relevant features. Under-filtering may retain noise, contaminants, or failed samples.

## Next skills
- microbiome.differential_abundance
- multiomics.correlation_network
- reporting.evidence_report_generation

## Review requirement
Expert review is optional unless filtering removes many samples, groups become imbalanced, or contamination is suspected.
