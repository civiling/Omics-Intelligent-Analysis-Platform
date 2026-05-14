from backend.services import MetadataDesignService, PlatformObjectService
from backend.storage import (
    AnalysisMode,
    ConfirmationStatus,
    ExpressionMatrix,
    MatrixOrientation,
    MatrixType,
    Organism,
    PlatformRepository,
    ResultConfidenceLevel,
    SampleMetadata,
    ValidationStatus,
)


def create_dataset_with_samples(tmp_path, sample_ids):
    repository = PlatformRepository(tmp_path)
    platform_service = PlatformObjectService(repository)
    project = platform_service.create_project("Metadata project", organism=Organism.HUMAN)
    dataset = platform_service.create_dataset(project.project_id, "Metadata dataset", organism=Organism.HUMAN)
    for sample_id in sample_ids:
        platform_service.save_sample_metadata(
            SampleMetadata(
                dataset_id=dataset.dataset_id,
                sample_id=sample_id,
                file_name=f"{sample_id}.csv.gz",
                species=Organism.HUMAN,
            )
        )
        platform_service.register_expression_matrix(
            ExpressionMatrix(
                dataset_id=dataset.dataset_id,
                matrix_type=MatrixType.RAW_COUNT,
                orientation=MatrixOrientation.GENE_BY_CELL,
                organism=Organism.HUMAN,
                n_genes=100,
                n_cells=50,
                is_raw_count=True,
                validation_status=ValidationStatus.VALID,
            )
        )
    return repository, platform_service, dataset


def test_metadata_template_and_no_condition_recommends_multi_sample_integration(tmp_path):
    repository, platform_service, dataset = create_dataset_with_samples(tmp_path, ["sample_1", "sample_2"])
    service = MetadataDesignService(platform_service)

    template = service.build_metadata_template(dataset.dataset_id)
    result = service.evaluate_design(dataset.dataset_id)

    assert [row["sample_id"] for row in template] == ["sample_1", "sample_2"]
    assert result.summary.has_condition is False
    assert result.recommendation.recommended_mode == AnalysisMode.MULTI_SAMPLE_INTEGRATION
    assert result.recommendation.result_confidence == ResultConfidenceLevel.DESCRIPTIVE
    assert "condition" in result.recommendation.missing_information
    assert repository.analysis_mode_recommendations.get(result.recommendation.recommendation_id) is not None


def test_two_conditions_with_insufficient_replicates_downgrades_to_exploratory(tmp_path):
    _, platform_service, dataset = create_dataset_with_samples(tmp_path, ["normal_1", "tumor_1"])
    service = MetadataDesignService(platform_service)

    service.update_sample_metadata(
        dataset.dataset_id,
        {
            "normal_1": {"condition": "Normal", "batch": "b1"},
            "tumor_1": {"condition": "Tumor", "batch": "b1"},
        },
    )
    result = service.evaluate_design(dataset.dataset_id)

    assert result.summary.condition_counts == {"Normal": 1, "Tumor": 1}
    assert result.summary.can_run_formal_pseudobulk is False
    assert result.recommendation.recommended_mode == AnalysisMode.EXPLORATORY_PSEUDOBULK_DE
    assert result.recommendation.result_confidence == ResultConfidenceLevel.EXPLORATORY
    assert result.confidence_gate.downgrade_from == ResultConfidenceLevel.FORMAL_STATISTICAL
    assert result.confidence_gate.checks["has_min_replicates"] is False


def test_paired_patient_metadata_recommends_paired_pseudobulk(tmp_path):
    repository, platform_service, dataset = create_dataset_with_samples(
        tmp_path,
        ["p1_normal", "p1_tumor", "p2_normal", "p2_tumor"],
    )
    service = MetadataDesignService(platform_service)

    service.update_sample_metadata(
        dataset.dataset_id,
        {
            "p1_normal": {"condition": "Normal", "patient_id": "patient_1", "batch": "b1"},
            "p1_tumor": {"condition": "Tumor", "patient_id": "patient_1", "batch": "b1"},
            "p2_normal": {"condition": "Normal", "patient_id": "patient_2", "batch": "b2"},
            "p2_tumor": {"condition": "Tumor", "patient_id": "patient_2", "batch": "b2"},
        },
    )
    result = service.evaluate_design(dataset.dataset_id)
    rows = repository.list_dataset_sample_metadata(dataset.dataset_id)
    loaded_dataset = repository.datasets.require(dataset.dataset_id)

    assert loaded_dataset.metadata_status.name == "COMPLETE"
    assert all(row.confirmation_status == ConfirmationStatus.CONFIRMED for row in rows)
    assert result.summary.condition_counts == {"Normal": 2, "Tumor": 2}
    assert result.summary.can_run_formal_pseudobulk is True
    assert result.summary.can_run_paired_pseudobulk is True
    assert result.recommendation.recommended_mode == AnalysisMode.PAIRED_PSEUDOBULK_DE
    assert result.recommendation.result_confidence == ResultConfidenceLevel.FORMAL_STATISTICAL
    assert result.confidence_gate.passed is True
    assert result.confidence_gate.checks["is_paired"] is True


def test_metadata_csv_import_matches_gsm_ids_and_recommends_paired_design(tmp_path):
    repository, platform_service, dataset = create_dataset_with_samples(
        tmp_path,
        [
            "GSM5573466_sample1",
            "GSM5573467_sample2",
            "GSM5573468_sample3",
            "GSM5573469_sample4",
        ],
    )
    service = MetadataDesignService(platform_service)
    metadata_path = tmp_path / "metadata.csv"
    metadata_path.write_text(
        "\n".join(
            [
                "gsm,group,patient,batch",
                "GSM5573466,Normal,p1,b1",
                "GSM5573467,Tumor,p1,b1",
                "GSM5573468,Normal,p2,b2",
                "GSM5573469,Tumor,p2,b2",
                "GSM9999999,Tumor,p9,b9",
            ]
        ),
        encoding="utf-8",
    )

    import_result = service.import_metadata_file(dataset.dataset_id, metadata_path)
    design = service.evaluate_design(dataset.dataset_id)

    assert import_result.matched_sample_ids == [
        "GSM5573466_sample1",
        "GSM5573467_sample2",
        "GSM5573468_sample3",
        "GSM5573469_sample4",
    ]
    assert len(import_result.unmatched_rows) == 1
    assert import_result.missing_samples == []
    assert design.recommendation.recommended_mode == AnalysisMode.PAIRED_PSEUDOBULK_DE
    assert design.summary.condition_counts == {"Normal": 2, "Tumor": 2}
    assert design.summary.paired_patient_count == 2
    assert repository.datasets.require(dataset.dataset_id).metadata_status.name == "COMPLETE"


def test_metadata_tsv_import_can_match_by_file_name_and_reports_missing_samples(tmp_path):
    _, platform_service, dataset = create_dataset_with_samples(
        tmp_path,
        ["sample_1", "sample_2", "sample_3"],
    )
    service = MetadataDesignService(platform_service)
    metadata_path = tmp_path / "metadata.tsv"
    metadata_path.write_text(
        "\n".join(
            [
                "file_name\tcondition\tbatch",
                "sample_1.csv.gz\tNormal\tb1",
                "sample_2.csv.gz\tTumor\tb1",
            ]
        ),
        encoding="utf-8",
    )

    import_result = service.import_metadata_file(dataset.dataset_id, metadata_path)

    assert import_result.matched_sample_ids == ["sample_1", "sample_2"]
    assert import_result.missing_samples == ["sample_3"]
    assert import_result.unmatched_rows == []


def test_write_metadata_template_outputs_csv(tmp_path):
    _, platform_service, dataset = create_dataset_with_samples(tmp_path, ["sample_1"])
    service = MetadataDesignService(platform_service)
    output_path = tmp_path / "template.csv"

    written_path = service.write_metadata_template(dataset.dataset_id, output_path)

    text = written_path.read_text(encoding="utf-8")
    assert "sample_id,file_name,condition,patient_id,batch" in text
    assert "sample_1,sample_1.csv.gz" in text
