# Single-cell RNA-seq QC and clustering preview

## Purpose

Run the first-stage scRNA-seq quality-control and result-display workflow after data ingestion and metadata design.

## Use when

Use this skill after expression matrices have been registered in a platform store and the user is ready to inspect cell-level QC, filtering thresholds, and first result-display plots.

## Inputs

- platform_store
- dataset_id

## Outputs

- cell_qc_metrics
- sample_qc_summary
- qc_clustering_report
- umap_embedding
- umap_plot_data
- qc_violin_plot_data
- method_note
- risk_notes

## Primary tools

- platform QcClusteringService

## Default strategy

Stream registered gene-by-cell count matrices, compute per-cell total counts, detected genes, and mitochondrial percentage, apply configurable filtering thresholds, and emit frontend-friendly table and plot payloads.

## Parameters

- min_genes
- max_genes
- min_counts
- max_counts
- max_mito_pct
- max_cells_per_sample
- cluster_count

## QC checks

- Check low detected genes.
- Check high detected genes when max_genes is set.
- Check low total counts.
- Check high total counts when max_counts is set.
- Check high mitochondrial percentage.
- Track matrix orientation warnings and preview sampling warnings.

## Interpretation limits

The first implementation emits a QC-derived preview embedding. It is useful for interface integration and data-readiness review, but it is not a final biological PCA, neighborhood graph, UMAP, or Leiden/Louvain clustering result.

## Risk notes

Preview clusters must not be used as final cell-type or biological cluster labels. Replace the computation kernel with Scanpy or Seurat before interpreting biology.

## Next skills

- reporting.evidence_report_generation

## Review requirement

Expert review is optional for the preview workflow, but QC thresholds and downstream biological interpretation require user or analyst confirmation.
