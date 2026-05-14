from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from backend.storage.models import (
    AnalysisModeRecommendation,
    ConfidenceGateResult,
    ConfirmationStatus,
    DataSource,
    DataType,
    Dataset,
    ExpressionMatrix,
    FileRole,
    MetadataStatus,
    Organism,
    Project,
    SampleMetadata,
    UploadedFile,
    WorkflowRun,
    WorkflowTask,
)
from backend.storage.repositories import PlatformRepository


class PlatformObjectService:
    """Creation and persistence service for Phase 1 platform objects."""

    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def create_project(
        self,
        name: str,
        description: str = "",
        organism: Organism = Organism.UNKNOWN,
        disease_context: str = "",
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            organism=organism,
            disease_context=disease_context,
        )
        return self.repository.projects.save(project)

    def create_dataset(
        self,
        project_id: str,
        dataset_name: str,
        data_type: DataType = DataType.SCRNA_SEQ,
        source: DataSource = DataSource.USER_UPLOAD,
        organism: Organism = Organism.UNKNOWN,
    ) -> Dataset:
        self.repository.projects.require(project_id)
        dataset = Dataset(
            project_id=project_id,
            dataset_name=dataset_name,
            data_type=data_type,
            source=source,
            organism=organism,
        )
        saved = self.repository.datasets.save(dataset)
        self._touch_project(project_id)
        return saved

    def register_uploaded_file(
        self,
        dataset_id: str,
        original_name: str,
        storage_path: str | Path,
        file_type: str,
        detected_role: FileRole = FileRole.UNKNOWN,
        calculate_md5: bool = False,
    ) -> UploadedFile:
        self.repository.datasets.require(dataset_id)
        path = Path(storage_path)
        uploaded_file = UploadedFile(
            dataset_id=dataset_id,
            original_name=original_name,
            storage_path=str(path),
            file_type=file_type,
            file_size=path.stat().st_size if path.exists() else 0,
            md5=_md5(path) if calculate_md5 and path.exists() else None,
            detected_role=detected_role,
        )
        saved = self.repository.uploaded_files.save(uploaded_file)
        self._refresh_dataset_counts(dataset_id)
        return saved

    def register_expression_matrix(self, matrix: ExpressionMatrix) -> ExpressionMatrix:
        self.repository.datasets.require(matrix.dataset_id)
        if matrix.file_id:
            self.repository.uploaded_files.require(matrix.file_id)
        saved = self.repository.expression_matrices.save(matrix)
        self._refresh_dataset_counts(matrix.dataset_id)
        return saved

    def save_sample_metadata(self, metadata: SampleMetadata) -> SampleMetadata:
        self.repository.datasets.require(metadata.dataset_id)
        saved = self.repository.sample_metadata.save(metadata)
        self._refresh_dataset_counts(metadata.dataset_id)
        return saved

    def create_workflow_run(self, workflow_run: WorkflowRun) -> WorkflowRun:
        self.repository.projects.require(workflow_run.project_id)
        self.repository.datasets.require(workflow_run.dataset_id)
        return self.repository.workflow_runs.save(workflow_run)

    def create_workflow_task(self, workflow_task: WorkflowTask) -> WorkflowTask:
        self.repository.workflow_runs.require(workflow_task.workflow_run_id)
        saved = self.repository.workflow_tasks.save(workflow_task)
        workflow_run = self.repository.workflow_runs.require(workflow_task.workflow_run_id)
        if workflow_task.task_id not in workflow_run.task_list:
            workflow_run.task_list.append(workflow_task.task_id)
            self.repository.workflow_runs.save(workflow_run)
        return saved

    def save_analysis_mode_recommendation(
        self,
        recommendation: AnalysisModeRecommendation,
    ) -> AnalysisModeRecommendation:
        self.repository.datasets.require(recommendation.dataset_id)
        return self.repository.analysis_mode_recommendations.save(recommendation)

    def save_confidence_gate_result(self, gate_result: ConfidenceGateResult) -> ConfidenceGateResult:
        self.repository.datasets.require(gate_result.dataset_id)
        return self.repository.confidence_gate_results.save(gate_result)

    def _refresh_dataset_counts(self, dataset_id: str) -> None:
        dataset = self.repository.datasets.require(dataset_id)
        files = self.repository.list_dataset_files(dataset_id)
        matrices = self.repository.list_dataset_matrices(dataset_id)
        sample_metadata = self.repository.list_dataset_sample_metadata(dataset_id)
        confirmed_samples = {
            row.sample_id
            for row in sample_metadata
            if row.sample_id
        }

        dataset.file_count = len(files)
        dataset.matrix_count = len(matrices)
        dataset.sample_count = len(confirmed_samples)
        if not sample_metadata:
            dataset.metadata_status = MetadataStatus.MISSING
        elif any(row.condition is None or row.confirmation_status != ConfirmationStatus.CONFIRMED for row in sample_metadata):
            dataset.metadata_status = MetadataStatus.PARTIAL
        else:
            dataset.metadata_status = MetadataStatus.COMPLETE
        self.repository.datasets.save(dataset)
        self._touch_project(dataset.project_id)

    def _touch_project(self, project_id: str) -> None:
        project = self.repository.projects.require(project_id)
        project.updated_at = datetime.now()
        self.repository.projects.save(project)


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
