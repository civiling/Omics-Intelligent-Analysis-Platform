from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services import QcClusteringService, QcParameters
from backend.storage import PlatformRepository
from skill_registry.loader import _load_yaml_file


def main() -> int:
    args = parse_args()
    outputs_dir = Path(args.outputs_dir).resolve()
    inputs = json.loads(Path(args.inputs_json).read_text(encoding="utf-8"))
    parameters = _load_yaml_file(Path(args.parameters_yaml))

    platform_store = Path(inputs["platform_store"]).resolve()
    dataset_id = str(parameters["dataset_id"])
    qc_parameters = QcParameters(
        min_genes=int(parameters.get("min_genes", 200)),
        max_genes=optional_int(parameters.get("max_genes")),
        min_counts=int(parameters.get("min_counts", 0)),
        max_counts=optional_int(parameters.get("max_counts")),
        max_mito_pct=float(parameters.get("max_mito_pct", 20.0)),
        max_cells_per_sample=int(parameters.get("max_cells_per_sample", 2000)),
        cluster_count=int(parameters.get("cluster_count", 4)),
    )
    result = QcClusteringService(PlatformRepository(platform_store)).run(dataset_id, qc_parameters)

    cell_qc_rows = [metric.to_dict() for metric in result.cell_qc_metrics]
    embedding_rows = [point.to_dict() for point in result.embedding]
    qc_report = {
        "dataset_id": result.dataset_id,
        "parameters": result.parameters.__dict__,
        "filtering_summary": result.filtering_summary,
        "sample_summary": result.sample_summary,
        "warnings": result.warnings,
        "normalization": {
            "method": "log1p counts-per-cell scaling preview",
            "note": "The first workflow version uses QC-derived coordinates for preview clustering; Scanpy PCA/UMAP can replace this kernel while keeping the same output contract.",
        },
        "embedding": {
            "method": "qc_preview_embedding",
            "point_count": len(embedding_rows),
            "cluster_count": len({row["cluster_id"] for row in embedding_rows}),
        },
    }

    write_csv(outputs_dir / "tables" / "cell_qc_metrics.csv", cell_qc_rows)
    write_csv(outputs_dir / "tables" / "sample_qc_summary.csv", result.sample_summary)
    write_json(outputs_dir / "tables" / "umap_embedding.json", embedding_rows)
    write_json(outputs_dir / "figures" / "umap_plot_data.json", build_umap_plot_data(embedding_rows))
    write_json(outputs_dir / "figures" / "qc_violin_plot_data.json", build_qc_violin_plot_data(cell_qc_rows))
    write_json(outputs_dir / "reports" / "qc_clustering_report.json", qc_report)
    write_text(
        outputs_dir / "notes" / "method_note.md",
        "# Method Note\n\nThis workflow computes per-cell QC metrics from registered gene-by-cell count matrices, applies configurable filtering thresholds, and emits a lightweight QC-derived embedding for first-stage result display.\n",
    )
    write_text(
        outputs_dir / "notes" / "risk_notes.md",
        "# Risk Notes\n\nThe current embedding is a preview based on QC metrics, not a replacement for a full Scanpy/Seurat PCA, neighborhood graph, UMAP, and Leiden/Louvain clustering analysis.\n",
    )
    write_json(
        outputs_dir / "metrics.json",
        {
            "workflow_id": "scrna.qc_clustering",
            "dataset_id": dataset_id,
            "platform_store": str(platform_store),
            "evaluated_cell_count": result.filtering_summary["evaluated_cell_count"],
            "passed_cell_count": result.filtering_summary["passed_cell_count"],
            "failed_cell_count": result.filtering_summary["failed_cell_count"],
            "pass_rate": result.filtering_summary["pass_rate"],
            "embedding_point_count": len(embedding_rows),
            "warning_count": len(result.warnings),
        },
    )
    print(f"scrna.qc_clustering completed for dataset {dataset_id}")
    print(json.dumps({"dataset_id": dataset_id, "platform_store": str(platform_store)}, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scRNA QC and clustering preview workflow.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--inputs-json", required=True)
    parser.add_argument("--parameters-yaml", required=True)
    parser.add_argument("--outputs-dir", required=True)
    return parser.parse_args()


def optional_int(value: Any) -> int | None:
    if value in (None, "", "null"):
        return None
    return int(value)


def write_json(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_umap_plot_data(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "scatter/v1",
        "x": "umap_1",
        "y": "umap_2",
        "color": "cluster_id",
        "shape": "passed_qc",
        "points": rows,
    }


def build_qc_violin_plot_data(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "qc_violin/v1",
        "group_by": "sample_id",
        "metrics": ["total_counts", "detected_genes", "mitochondrial_pct"],
        "rows": rows,
    }


if __name__ == "__main__":
    raise SystemExit(main())
