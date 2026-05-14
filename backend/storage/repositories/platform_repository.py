from __future__ import annotations

from pathlib import Path

from backend.storage.models import (
    AnalysisModeRecommendation,
    ConfidenceGateResult,
    Dataset,
    ExpressionMatrix,
    Project,
    SampleMetadata,
    UploadedFile,
    WorkflowRun,
    WorkflowTask,
)

from .json_repository import JsonRepository


class PlatformRepository:
    """Container for the Phase 1 platform object repositories."""

    def __init__(self, storage_dir: str | Path) -> None:
        base_dir = Path(storage_dir).resolve()
        self.projects = JsonRepository(Project, "project_id", base_dir, "projects")
        self.datasets = JsonRepository(Dataset, "dataset_id", base_dir, "datasets")
        self.uploaded_files = JsonRepository(UploadedFile, "file_id", base_dir, "uploaded_files")
        self.expression_matrices = JsonRepository(ExpressionMatrix, "matrix_id", base_dir, "expression_matrices")
        self.sample_metadata = JsonRepository(SampleMetadata, "sample_metadata_id", base_dir, "sample_metadata")
        self.workflow_runs = JsonRepository(WorkflowRun, "workflow_run_id", base_dir, "workflow_runs")
        self.workflow_tasks = JsonRepository(WorkflowTask, "task_id", base_dir, "workflow_tasks")
        self.analysis_mode_recommendations = JsonRepository(
            AnalysisModeRecommendation,
            "recommendation_id",
            base_dir,
            "analysis_mode_recommendations",
        )
        self.confidence_gate_results = JsonRepository(
            ConfidenceGateResult,
            "gate_result_id",
            base_dir,
            "confidence_gate_results",
        )

    def list_project_datasets(self, project_id: str) -> list[Dataset]:
        return self.datasets.filter_by(project_id=project_id)

    def list_dataset_files(self, dataset_id: str) -> list[UploadedFile]:
        return self.uploaded_files.filter_by(dataset_id=dataset_id)

    def list_dataset_matrices(self, dataset_id: str) -> list[ExpressionMatrix]:
        return self.expression_matrices.filter_by(dataset_id=dataset_id)

    def list_dataset_sample_metadata(self, dataset_id: str) -> list[SampleMetadata]:
        return self.sample_metadata.filter_by(dataset_id=dataset_id)

    def list_dataset_workflow_runs(self, dataset_id: str) -> list[WorkflowRun]:
        return self.workflow_runs.filter_by(dataset_id=dataset_id)

    def list_workflow_tasks(self, workflow_run_id: str) -> list[WorkflowTask]:
        return self.workflow_tasks.filter_by(workflow_run_id=workflow_run_id)
