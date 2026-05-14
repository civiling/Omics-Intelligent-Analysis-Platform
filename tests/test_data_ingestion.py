import gzip
from pathlib import Path

from backend.services import DataIngestionService, MatrixFormatInspector, PlatformObjectService
from backend.storage import (
    GeneIdType,
    MatrixOrientation,
    MatrixType,
    MetadataStatus,
    Organism,
    ParseStatus,
    PlatformRepository,
    ValidationStatus,
)


def write_gzip(path: Path, text: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write(text)


def test_matrix_format_inspector_detects_gene_by_cell_raw_count_csv_gz(tmp_path):
    matrix_path = tmp_path / "GSM123_sample1.csv.gz"
    write_gzip(
        matrix_path,
        "\n".join(
            [
                ",AAACCTGAGGCTACGA_1,AAACCTGAGGTTCCTA_1",
                "MT-ND1,0,2",
                "LINC00115,1,0",
                "FAM41C,0,3",
            ]
        ),
    )

    inspection = MatrixFormatInspector().inspect(matrix_path)

    assert inspection.sample_id == "GSM123_sample1"
    assert inspection.file_type == "csv.gz"
    assert inspection.orientation == MatrixOrientation.GENE_BY_CELL
    assert inspection.matrix_type == MatrixType.RAW_COUNT
    assert inspection.is_raw_count is True
    assert inspection.organism == Organism.HUMAN
    assert inspection.gene_id_type == GeneIdType.SYMBOL
    assert inspection.n_genes == 3
    assert inspection.n_cells == 2
    assert inspection.validation_status == ValidationStatus.VALID


def test_matrix_format_inspector_marks_normalized_values_as_warning(tmp_path):
    matrix_path = tmp_path / "normalized.csv.gz"
    write_gzip(
        matrix_path,
        "\n".join(
            [
                ",AAACCTGAGGCTACGA_1,AAACCTGAGGTTCCTA_1",
                "MT-ND1,0.4,2.1",
                "LINC00115,1.0,0.0",
            ]
        ),
    )

    inspection = MatrixFormatInspector().inspect(matrix_path)

    assert inspection.matrix_type == MatrixType.NORMALIZED
    assert inspection.is_raw_count is False
    assert inspection.validation_status == ValidationStatus.WARNING
    assert any("formal count-based DE should be disabled" in warning for warning in inspection.warnings)


def test_data_ingestion_service_persists_uploaded_files_matrices_and_metadata(tmp_path):
    repository = PlatformRepository(tmp_path / "store")
    service = DataIngestionService(PlatformObjectService(repository))
    data_dir = tmp_path / "GSE183904_RAW"
    data_dir.mkdir()
    write_gzip(
        data_dir / "GSM5573466_sample1.csv.gz",
        "\n".join(
            [
                ",AAACCTGAGGCTACGA_8,AAACCTGAGGTTCCTA_8",
                "AL627309.1,0,0",
                "MT-ND1,3,0",
            ]
        ),
    )
    write_gzip(
        data_dir / "GSM5573467_sample2.csv.gz",
        "\n".join(
            [
                ",AAACCTGAGGAGTAGA_9,AAACCTGAGGGTGTTG_9,AAACCTGAGGTTCCTA_9",
                "AL627309.1,0,1,0",
                "MT-ND1,2,0,0",
            ]
        ),
    )

    result = service.ingest_directory(
        data_dir,
        project_name="GSE183904 gastric cancer scRNA analysis",
        organism=Organism.HUMAN,
        disease_context="gastric cancer",
    )

    dataset = repository.datasets.require(result.dataset.dataset_id)
    matrices = repository.list_dataset_matrices(dataset.dataset_id)
    metadata_rows = repository.list_dataset_sample_metadata(dataset.dataset_id)
    uploaded_files = repository.list_dataset_files(dataset.dataset_id)

    assert dataset.file_count == 2
    assert dataset.matrix_count == 2
    assert dataset.sample_count == 2
    assert dataset.metadata_status == MetadataStatus.PARTIAL
    assert result.total_cells == 5
    assert result.total_genes == 2
    assert {row.sample_id for row in metadata_rows} == {"GSM5573466_sample1", "GSM5573467_sample2"}
    assert all(matrix.orientation == MatrixOrientation.GENE_BY_CELL for matrix in matrices)
    assert all(matrix.matrix_type == MatrixType.RAW_COUNT for matrix in matrices)
    assert all(file.parse_status == ParseStatus.SUCCESS for file in uploaded_files)
