from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.services.data_ingestion import open_text_matrix
from backend.storage.models import MatrixOrientation
from backend.storage.repositories import PlatformRepository


@dataclass(frozen=True)
class QcParameters:
    min_genes: int = 200
    max_genes: int | None = None
    min_counts: int = 0
    max_counts: int | None = None
    max_mito_pct: float = 20.0
    max_cells_per_sample: int = 2000
    cluster_count: int = 4


@dataclass(frozen=True)
class CellQcMetric:
    cell_id: str
    sample_id: str
    file_name: str
    total_counts: float
    detected_genes: int
    mitochondrial_counts: float
    mitochondrial_pct: float
    passed_qc: bool
    failed_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "sample_id": self.sample_id,
            "file_name": self.file_name,
            "total_counts": round(self.total_counts, 6),
            "detected_genes": self.detected_genes,
            "mitochondrial_counts": round(self.mitochondrial_counts, 6),
            "mitochondrial_pct": round(self.mitochondrial_pct, 6),
            "passed_qc": self.passed_qc,
            "failed_reasons": self.failed_reasons,
        }


@dataclass(frozen=True)
class EmbeddingPoint:
    cell_id: str
    sample_id: str
    cluster_id: str
    umap_1: float
    umap_2: float
    total_counts: float
    detected_genes: int
    mitochondrial_pct: float
    passed_qc: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "sample_id": self.sample_id,
            "cluster_id": self.cluster_id,
            "umap_1": round(self.umap_1, 6),
            "umap_2": round(self.umap_2, 6),
            "total_counts": round(self.total_counts, 6),
            "detected_genes": self.detected_genes,
            "mitochondrial_pct": round(self.mitochondrial_pct, 6),
            "passed_qc": self.passed_qc,
        }


@dataclass(frozen=True)
class QcClusteringResult:
    dataset_id: str
    parameters: QcParameters
    cell_qc_metrics: list[CellQcMetric]
    embedding: list[EmbeddingPoint]
    sample_summary: list[dict[str, Any]]
    filtering_summary: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


class QcClusteringService:
    """Compute a lightweight scRNA QC and clustering preview from registered count matrices."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def run(
        self,
        dataset_id: str,
        parameters: QcParameters | None = None,
    ) -> QcClusteringResult:
        params = parameters or QcParameters()
        self.repository.datasets.require(dataset_id)
        matrices = sorted(
            self.repository.list_dataset_matrices(dataset_id),
            key=lambda item: item.storage_path,
        )
        metadata_by_file = {
            row.file_name: row
            for row in self.repository.list_dataset_sample_metadata(dataset_id)
        }
        warnings: list[str] = []
        all_metrics: list[CellQcMetric] = []

        for matrix in matrices:
            if matrix.orientation == MatrixOrientation.CELL_BY_GENE:
                warnings.append(
                    f"Skipped {Path(matrix.storage_path).name}: only gene_by_cell matrices are supported for the preview QC workflow."
                )
                continue
            if matrix.orientation == MatrixOrientation.UNKNOWN:
                warnings.append(
                    f"{Path(matrix.storage_path).name}: matrix orientation is unknown; assuming gene_by_cell for preview QC."
                )
            path = Path(matrix.storage_path)
            sample_metadata = metadata_by_file.get(path.name)
            sample_id = sample_metadata.sample_id if sample_metadata else Path(path.name).name.split(".")[0]
            metrics, matrix_warnings = self._compute_gene_by_cell_metrics(path, sample_id, params)
            all_metrics.extend(metrics)
            warnings.extend(matrix_warnings)

        embedding = build_qc_embedding(all_metrics, params.cluster_count)
        return QcClusteringResult(
            dataset_id=dataset_id,
            parameters=params,
            cell_qc_metrics=all_metrics,
            embedding=embedding,
            sample_summary=summarize_by_sample(all_metrics),
            filtering_summary=summarize_filtering(all_metrics),
            warnings=warnings,
        )

    def _compute_gene_by_cell_metrics(
        self,
        matrix_path: Path,
        sample_id: str,
        parameters: QcParameters,
    ) -> tuple[list[CellQcMetric], list[str]]:
        warnings: list[str] = []
        delimiter = "\t" if matrix_path.name.lower().endswith((".tsv", ".tsv.gz")) else ","
        with open_text_matrix(matrix_path) as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            try:
                header = next(reader)
            except StopIteration:
                return [], [f"Skipped empty matrix file: {matrix_path.name}."]

            cell_ids = [value.strip() for value in header[1:]]
            if not cell_ids:
                return [], [f"Skipped matrix without cell columns: {matrix_path.name}."]

            selected_indices = select_cell_indices(len(cell_ids), parameters.max_cells_per_sample)
            if len(selected_indices) < len(cell_ids):
                warnings.append(
                    f"{matrix_path.name}: sampled {len(selected_indices)} of {len(cell_ids)} cells for preview QC."
                )

            total_counts = [0.0 for _ in selected_indices]
            detected_genes = [0 for _ in selected_indices]
            mitochondrial_counts = [0.0 for _ in selected_indices]
            row_count = 0
            malformed_rows = 0

            for row in reader:
                if not row:
                    continue
                row_count += 1
                gene_id = row[0].strip()
                is_mito = is_mitochondrial_gene(gene_id)
                if len(row) < len(cell_ids) + 1:
                    malformed_rows += 1

                for output_index, cell_index in enumerate(selected_indices):
                    value = parse_count(row[cell_index + 1]) if cell_index + 1 < len(row) else 0.0
                    if value <= 0:
                        continue
                    total_counts[output_index] += value
                    detected_genes[output_index] += 1
                    if is_mito:
                        mitochondrial_counts[output_index] += value

            if row_count == 0:
                warnings.append(f"{matrix_path.name}: matrix has no gene rows.")
            if malformed_rows:
                warnings.append(f"{matrix_path.name}: detected {malformed_rows} short row(s).")

        metrics = []
        for output_index, cell_index in enumerate(selected_indices):
            total = total_counts[output_index]
            mito = mitochondrial_counts[output_index]
            mito_pct = (mito / total * 100.0) if total else 0.0
            failed_reasons = qc_failed_reasons(total, detected_genes[output_index], mito_pct, parameters)
            metrics.append(
                CellQcMetric(
                    cell_id=cell_ids[cell_index],
                    sample_id=sample_id,
                    file_name=matrix_path.name,
                    total_counts=total,
                    detected_genes=detected_genes[output_index],
                    mitochondrial_counts=mito,
                    mitochondrial_pct=mito_pct,
                    passed_qc=not failed_reasons,
                    failed_reasons=failed_reasons,
                )
            )
        return metrics, warnings


def select_cell_indices(cell_count: int, max_cells: int) -> list[int]:
    if max_cells <= 0 or cell_count <= max_cells:
        return list(range(cell_count))
    if max_cells == 1:
        return [0]
    step = (cell_count - 1) / (max_cells - 1)
    return sorted({round(index * step) for index in range(max_cells)})


def parse_count(value: str) -> float:
    try:
        count = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(count) or count < 0:
        return 0.0
    return count


def is_mitochondrial_gene(gene_id: str) -> bool:
    normalized = gene_id.strip()
    upper = normalized.upper()
    return upper.startswith("MT-") or upper.startswith("MT.")


def qc_failed_reasons(
    total_counts: float,
    detected_genes: int,
    mitochondrial_pct: float,
    parameters: QcParameters,
) -> list[str]:
    reasons: list[str] = []
    if detected_genes < parameters.min_genes:
        reasons.append("low_detected_genes")
    if parameters.max_genes is not None and detected_genes > parameters.max_genes:
        reasons.append("high_detected_genes")
    if total_counts < parameters.min_counts:
        reasons.append("low_total_counts")
    if parameters.max_counts is not None and total_counts > parameters.max_counts:
        reasons.append("high_total_counts")
    if mitochondrial_pct > parameters.max_mito_pct:
        reasons.append("high_mitochondrial_pct")
    return reasons


def build_qc_embedding(metrics: list[CellQcMetric], cluster_count: int) -> list[EmbeddingPoint]:
    if not metrics:
        return []

    log_counts = [math.log1p(metric.total_counts) for metric in metrics]
    log_genes = [math.log1p(metric.detected_genes) for metric in metrics]
    mito = [metric.mitochondrial_pct for metric in metrics]
    count_center, count_scale = center_and_scale(log_counts)
    gene_center, gene_scale = center_and_scale(log_genes)
    mito_center, mito_scale = center_and_scale(mito)
    effective_cluster_count = max(1, cluster_count)

    points: list[EmbeddingPoint] = []
    for index, metric in enumerate(metrics):
        x = (log_counts[index] - count_center) / count_scale
        y = (log_genes[index] - gene_center) / gene_scale - 0.35 * ((mito[index] - mito_center) / mito_scale)
        qc_score = x + y - 0.5 * ((mito[index] - mito_center) / mito_scale)
        cluster_index = int(abs(math.floor((qc_score + 3.0) * effective_cluster_count / 6.0))) % effective_cluster_count
        points.append(
            EmbeddingPoint(
                cell_id=metric.cell_id,
                sample_id=metric.sample_id,
                cluster_id=f"cluster_{cluster_index + 1}",
                umap_1=x,
                umap_2=y,
                total_counts=metric.total_counts,
                detected_genes=metric.detected_genes,
                mitochondrial_pct=metric.mitochondrial_pct,
                passed_qc=metric.passed_qc,
            )
        )
    return points


def center_and_scale(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    center = sum(values) / len(values)
    variance = sum((value - center) ** 2 for value in values) / len(values)
    scale = math.sqrt(variance) or 1.0
    return center, scale


def summarize_by_sample(metrics: list[CellQcMetric]) -> list[dict[str, Any]]:
    by_sample: dict[str, list[CellQcMetric]] = {}
    for metric in metrics:
        by_sample.setdefault(metric.sample_id, []).append(metric)

    summaries: list[dict[str, Any]] = []
    for sample_id, sample_metrics in sorted(by_sample.items()):
        passed = [metric for metric in sample_metrics if metric.passed_qc]
        summaries.append(
            {
                "sample_id": sample_id,
                "cell_count": len(sample_metrics),
                "passed_cell_count": len(passed),
                "failed_cell_count": len(sample_metrics) - len(passed),
                "median_total_counts": median([metric.total_counts for metric in sample_metrics]),
                "median_detected_genes": median([metric.detected_genes for metric in sample_metrics]),
                "median_mitochondrial_pct": median([metric.mitochondrial_pct for metric in sample_metrics]),
            }
        )
    return summaries


def summarize_filtering(metrics: list[CellQcMetric]) -> dict[str, Any]:
    failure_reasons: dict[str, int] = {}
    for metric in metrics:
        for reason in metric.failed_reasons:
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    passed_count = sum(1 for metric in metrics if metric.passed_qc)
    return {
        "evaluated_cell_count": len(metrics),
        "passed_cell_count": passed_count,
        "failed_cell_count": len(metrics) - passed_count,
        "pass_rate": round(passed_count / len(metrics), 6) if metrics else 0.0,
        "failure_reasons": dict(sorted(failure_reasons.items())),
    }


def median(values: list[float | int]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return round(float(sorted_values[midpoint]), 6)
    return round((float(sorted_values[midpoint - 1]) + float(sorted_values[midpoint])) / 2, 6)
