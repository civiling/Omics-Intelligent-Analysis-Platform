from backend.services import PlatformObjectService
from backend.storage import (
    AnalysisMode,
    AnalysisModeRecommendation,
    ConfirmationStatus,
    DataType,
    ExpressionMatrix,
    FileRole,
    MatrixOrientation,
    MatrixType,
    MetadataStatus,
    Organism,
    PlatformRepository,
    ResultConfidenceLevel,
    SampleMetadata,
    ValidationStatus,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowTask,
)


def test_standard_objects_round_trip_through_json_repository(tmp_path):
    repository = PlatformRepository(tmp_path)
    project = repository.projects.save(
        repository.projects.model_cls(
            name="GSE demo",
            organism=Organism.HUMAN,
            default_analysis_mode=AnalysisMode.MULTI_SAMPLE_INTEGRATION.value,
        )
    )
    dataset = repository.datasets.save(
        repository.datasets.model_cls(
            project_id=project.project_id,
            dataset_name="demo scRNA",
            data_type=DataType.SCRNA_SEQ,
            organism=Organism.HUMAN,
        )
    )
    recommendation = AnalysisModeRecommendation(
        dataset_id=dataset.dataset_id,
        recommended_mode=AnalysisMode.FORMAL_PSEUDOBULK_DE,
        result_confidence=ResultConfidenceLevel.FORMAL_STATISTICAL,
        executable_modes=[
            AnalysisMode.MULTI_SAMPLE_INTEGRATION,
            AnalysisMode.FORMAL_PSEUDOBULK_DE,
        ],
        reasons=["Each condition has biological replicates."],
    )

    repository.analysis_mode_recommendations.save(recommendation)
    loaded = repository.analysis_mode_recommendations.require(recommendation.recommendation_id)

    assert loaded.recommended_mode == AnalysisMode.FORMAL_PSEUDOBULK_DE
    assert loaded.result_confidence == ResultConfidenceLevel.FORMAL_STATISTICAL
    assert loaded.executable_modes == [
        AnalysisMode.MULTI_SAMPLE_INTEGRATION,
        AnalysisMode.FORMAL_PSEUDOBULK_DE,
    ]
    assert repository.list_project_datasets(project.project_id)[0].dataset_id == dataset.dataset_id


def test_platform_object_service_updates_dataset_counts_and_metadata_status(tmp_path):
    repository = PlatformRepository(tmp_path)
    service = PlatformObjectService(repository)
    matrix_path = tmp_path / "GSM1.csv.gz"
    matrix_path.write_text("gene,cell1\nA,1\n", encoding="utf-8")

    project = service.create_project("Phase 1 project", organism=Organism.HUMAN)
    dataset = service.create_dataset(project.project_id, "single-cell test")
    uploaded_file = service.register_uploaded_file(
        dataset.dataset_id,
        original_name="GSM1.csv.gz",
        storage_path=matrix_path,
        file_type="csv.gz",
        detected_role=FileRole.EXPRESSION_MATRIX,
    )
    service.register_expression_matrix(
        ExpressionMatrix(
            dataset_id=dataset.dataset_id,
            file_id=uploaded_file.file_id,
            matrix_type=MatrixType.RAW_COUNT,
            orientation=MatrixOrientation.GENE_BY_CELL,
            organism=Organism.HUMAN,
            n_genes=1,
            n_cells=1,
            storage_path=str(matrix_path),
            is_raw_count=True,
            validation_status=ValidationStatus.VALID,
        )
    )
    service.save_sample_metadata(
        SampleMetadata(
            dataset_id=dataset.dataset_id,
            sample_id="sample_1",
            file_name="GSM1.csv.gz",
            condition="Tumor",
            confirmation_status=ConfirmationStatus.CONFIRMED,
        )
    )

    loaded_dataset = repository.datasets.require(dataset.dataset_id)

    assert loaded_dataset.file_count == 1
    assert loaded_dataset.matrix_count == 1
    assert loaded_dataset.sample_count == 1
    assert loaded_dataset.metadata_status == MetadataStatus.COMPLETE


def test_workflow_run_and_task_are_persisted_as_platform_objects(tmp_path):
    repository = PlatformRepository(tmp_path)
    service = PlatformObjectService(repository)
    project = service.create_project("Workflow project")
    dataset = service.create_dataset(project.project_id, "Workflow dataset")
    workflow_run = service.create_workflow_run(
        WorkflowRun(
            project_id=project.project_id,
            dataset_id=dataset.dataset_id,
            workflow_name="Data ingestion",
            analysis_mode=AnalysisMode.MULTI_SAMPLE_INTEGRATION,
            status=WorkflowRunStatus.RUNNING,
        )
    )
    workflow_task = service.create_workflow_task(
        WorkflowTask(
            workflow_run_id=workflow_run.workflow_run_id,
            task_name="MatrixFormatDetection",
            task_type="format_check",
        )
    )

    loaded_run = repository.workflow_runs.require(workflow_run.workflow_run_id)

    assert loaded_run.task_list == [workflow_task.task_id]
    assert repository.list_workflow_tasks(workflow_run.workflow_run_id)[0].task_name == "MatrixFormatDetection"
