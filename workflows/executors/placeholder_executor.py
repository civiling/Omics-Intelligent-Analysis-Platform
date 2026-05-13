from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflows.models import WorkflowConfig, WorkflowResult, WorkflowStatus

from .base import BaseExecutor


PLACEHOLDER_OUTPUTS = {
    "microbiome.read_qc": {
        "tables/qc_summary.tsv": "metric\tvalue\nsamples_reviewed\tplaceholder\nfeatures_reviewed\tplaceholder\n",
        "figures/read_quality_chart_spec.json": {
            "chart": "read_quality",
            "x": "sample",
            "y": "quality_score",
            "source": "placeholder",
        },
        "notes/method_note.md": "# Method Note\n\nPlaceholder microbiome QC summary. No bioinformatics tool was executed.\n",
        "notes/risk_notes.md": "# Risk Notes\n\nQC thresholds and sample exclusions require project-specific review.\n",
    },
    "microbiome.differential_abundance": {
        "tables/differential_taxa.tsv": "feature_id\ttaxon\tlog_fold_change\tadjusted_p_value\nplaceholder_taxon\tUnclassified\t0.0\t1.0\n",
        "figures/volcano_plot_spec.json": {
            "chart": "volcano",
            "x": "log_fold_change",
            "y": "-log10_adjusted_p_value",
            "source": "placeholder",
        },
        "notes/method_note.md": "# Method Note\n\nPlaceholder differential abundance result. Compositional methods should be used in real execution.\n",
        "notes/risk_notes.md": "# Risk Notes\n\nRelative abundance changes are not absolute abundance changes; t-tests are not final evidence.\n",
    },
    "transcriptomics.differential_expression": {
        "tables/differential_genes.tsv": "gene_id\tlog2_fold_change\tadjusted_p_value\nplaceholder_gene\t0.0\t1.0\n",
        "figures/volcano_plot_spec.json": {
            "chart": "volcano",
            "x": "log2_fold_change",
            "y": "-log10_adjusted_p_value",
            "source": "placeholder",
        },
        "notes/method_note.md": "# Method Note\n\nPlaceholder differential expression result. No RNA-seq model was fitted.\n",
        "notes/risk_notes.md": "# Risk Notes\n\nBatch, sample size, FDR, and multiple testing require explicit review.\n",
    },
    "metabolomics.differential_metabolites": {
        "tables/differential_metabolites.tsv": "metabolite_id\tannotation_level\tlog_fold_change\tadjusted_p_value\nplaceholder_metabolite\tunknown\t0.0\t1.0\n",
        "figures/pca_plot_spec.json": {
            "chart": "pca",
            "source": "placeholder",
        },
        "figures/volcano_plot_spec.json": {
            "chart": "volcano",
            "x": "log_fold_change",
            "y": "-log10_adjusted_p_value",
            "source": "placeholder",
        },
        "notes/method_note.md": "# Method Note\n\nPlaceholder differential metabolite result. No peak processing or model was executed.\n",
        "notes/risk_notes.md": "# Risk Notes\n\nAnnotation confidence, batch effects, normalization, and missingness must be recorded.\n",
    },
    "multiomics.correlation_network": {
        "tables/feature_associations.tsv": "source_feature\ttarget_feature\tassociation\tadjusted_p_value\nplaceholder_microbe\tplaceholder_gene\t0.0\t1.0\n",
        "figures/network_plot_spec.json": {
            "chart": "network",
            "edge_table": "feature_associations.tsv",
            "source": "placeholder",
        },
        "notes/method_note.md": "# Method Note\n\nPlaceholder multi-omics association network. No correlation model was executed.\n",
        "notes/risk_notes.md": "# Risk Notes\n\nCorrelation is not causation, and sample mapping must be strictly consistent.\n",
    },
    "reporting.evidence_report_generation": {
        "tables/evidence_queries.tsv": "result_id\tquery\tevidence_level\nplaceholder_result\tplaceholder literature query\tpending_review\n",
        "notes/report_draft.md": "# Report Draft\n\nPlaceholder report draft. Expert review is required before release.\n",
        "notes/evidence_notes.md": "# Evidence Notes\n\nEvidence labels are placeholders and require verified citations.\n",
        "notes/risk_notes.md": "# Risk Notes\n\nLiterature relevance does not prove mechanism.\n",
    },
}


class PlaceholderExecutor(BaseExecutor):
    def execute(
        self,
        workflow_config: WorkflowConfig,
        run_dir: Path,
        input_files: dict[str, str],
        parameters: dict[str, Any],
    ) -> WorkflowResult:
        output_specs = PLACEHOLDER_OUTPUTS.get(workflow_config.id)
        if output_specs is None:
            return WorkflowResult(
                run_id=run_dir.name,
                status=WorkflowStatus.FAILED,
                error_message=f"No placeholder output specification for {workflow_config.id}.",
                logs={"stdout": "", "stderr": f"No placeholder output specification for {workflow_config.id}."},
            )

        output_files: dict[str, str] = {}
        for relative_path, content in output_specs.items():
            path = run_dir / "outputs" / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, dict):
                path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
            else:
                path.write_text(content, encoding="utf-8")
            output_files[relative_path] = str(path)

        metrics = {
            "placeholder": True,
            "input_count": len(input_files),
            "parameter_count": len(parameters),
            "output_count": len(output_files),
        }
        return WorkflowResult(
            run_id=run_dir.name,
            status=WorkflowStatus.SUCCESS,
            output_files=output_files,
            metrics=metrics,
            logs={
                "stdout": f"Generated placeholder outputs for {workflow_config.id}.\n",
                "stderr": "",
            },
        )
