# Multi-omics correlation network analysis

## Purpose
Standardize association network analysis across microbiome features, genes, metabolites, phenotypes, or other omics layers.

## Use when
Use this skill when constructing a multi-omics correlation or association network between matched sample-level matrices.

## Inputs
- feature_table
- expression_matrix
- metabolite_matrix
- metadata

## Outputs
- correlation_edge_table
- network_plot_spec
- method_note
- risk_notes

## Primary tools
- Spearman
- SparCC
- mixOmics

## Default strategy
Confirm sample mapping across omics layers, choose a correlation or multivariate method suitable for the data type, record preprocessing, correction method, and edge filtering rules.

## Parameters
- omics_layers
- sample_id_column
- correlation_method
- covariates
- fdr_threshold
- edge_filter
- network_layout

## QC checks
- Confirm identical or explicitly mapped sample identifiers across all matrices.
- Check missingness and feature filtering per omics layer.
- Record scaling, transformation, and compositional handling.
- Check whether network edges remain stable under reasonable thresholds.

## Interpretation limits
Correlation is not causation. Network edges are statistical associations and require biological and experimental review.

## Risk notes
Sample mapping must be strictly consistent. Confounding, compositional microbiome data, high dimensionality, and thresholding can create misleading edges.

## Next skills
- reporting.evidence_report_generation

## Review requirement
Expert review is required before mechanistic interpretation or prioritization of targets.
