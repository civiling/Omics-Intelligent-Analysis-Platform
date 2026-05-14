from __future__ import annotations

import csv
import gzip
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from backend.services.platform_service import PlatformObjectService
from backend.storage.models import (
    ConfirmationStatus,
    DataSource,
    DataType,
    Dataset,
    ExpressionMatrix,
    FileRole,
    GeneIdType,
    MatrixOrientation,
    MatrixType,
    MetadataSource,
    Organism,
    ParseStatus,
    Project,
    SampleMetadata,
    SparseFormat,
    UploadedFile,
    UploadStatus,
    ValidationStatus,
)


GSM_SAMPLE_PATTERN = re.compile(r"(?P<gsm>GSM\d+)[_-]?(?P<label>sample\d+)?", re.IGNORECASE)
TENX_BARCODE_PATTERN = re.compile(r"^[ACGTN]{8,}[-_]\d+$", re.IGNORECASE)
ENSEMBL_PATTERN = re.compile(r"^ENS[A-Z]*G\d+", re.IGNORECASE)


@dataclass(frozen=True)
class MatrixInspectionResult:
    path: Path
    file_type: str
    sample_id: str
    matrix_type: MatrixType
    orientation: MatrixOrientation
    organism: Organism
    gene_id_type: GeneIdType
    n_genes: int
    n_cells: int
    sparse_format: SparseFormat
    is_raw_count: bool
    validation_status: ValidationStatus
    warnings: list[str] = field(default_factory=list)
    gene_preview: list[str] = field(default_factory=list)
    cell_preview: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IngestedMatrix:
    uploaded_file: UploadedFile
    expression_matrix: ExpressionMatrix
    sample_metadata: SampleMetadata
    inspection: MatrixInspectionResult


@dataclass(frozen=True)
class DataIngestionResult:
    project: Project
    dataset: Dataset
    ingested_matrices: list[IngestedMatrix]

    @property
    def total_cells(self) -> int:
        return sum(item.expression_matrix.n_cells for item in self.ingested_matrices)

    @property
    def total_genes(self) -> int:
        gene_counts = [item.expression_matrix.n_genes for item in self.ingested_matrices]
        return max(gene_counts) if gene_counts else 0

    @property
    def warnings(self) -> list[str]:
        output: list[str] = []
        for item in self.ingested_matrices:
            output.extend(f"{item.uploaded_file.original_name}: {warning}" for warning in item.inspection.warnings)
        return output


class MatrixFormatInspector:
    """Inspect supported matrix files without loading the full expression matrix into memory."""

    def __init__(
        self,
        max_rows_for_value_checks: int = 200,
        max_values_for_value_checks: int = 10_000,
    ) -> None:
        self.max_rows_for_value_checks = max_rows_for_value_checks
        self.max_values_for_value_checks = max_values_for_value_checks

    def inspect(self, path: str | Path) -> MatrixInspectionResult:
        matrix_path = Path(path).resolve()
        file_type = detect_file_type(matrix_path)
        sample_id = infer_sample_id(matrix_path.name)
        warnings: list[str] = []

        if file_type not in {"csv", "csv.gz", "tsv", "tsv.gz"}:
            return MatrixInspectionResult(
                path=matrix_path,
                file_type=file_type,
                sample_id=sample_id,
                matrix_type=MatrixType.UNKNOWN,
                orientation=MatrixOrientation.UNKNOWN,
                organism=Organism.UNKNOWN,
                gene_id_type=GeneIdType.UNKNOWN,
                n_genes=0,
                n_cells=0,
                sparse_format=SparseFormat.UNKNOWN,
                is_raw_count=False,
                validation_status=ValidationStatus.INVALID,
                warnings=[f"Unsupported matrix file type: {file_type}."],
            )

        delimiter = "\t" if file_type.startswith("tsv") else ","
        with open_text_matrix(matrix_path) as handle:
            header_line = handle.readline()
            if not header_line:
                return self._invalid_empty_file(matrix_path, file_type, sample_id)

            header = next(csv.reader([header_line], delimiter=delimiter))
            header = [cell.strip() for cell in header]
            column_names = header[1:] if header else []
            gene_names: list[str] = []
            row_name_preview: list[str] = []
            row_count = 0
            duplicate_gene_count = 0
            seen_gene_names: set[str] = set()
            empty_row_count = 0
            inconsistent_row_count = 0
            sampled_values: list[str] = []

            for line in handle:
                row_count += 1
                stripped_line = line.strip()
                if not stripped_line:
                    empty_row_count += 1
                    continue
                row_name, value_text = split_row_name_and_values(stripped_line, delimiter)
                if row_name:
                    if row_name in seen_gene_names:
                        duplicate_gene_count += 1
                    seen_gene_names.add(row_name)
                    if len(row_name_preview) < 20:
                        row_name_preview.append(row_name)
                    gene_names.append(row_name)
                if row_count <= self.max_rows_for_value_checks and len(sampled_values) < self.max_values_for_value_checks:
                    remaining = self.max_values_for_value_checks - len(sampled_values)
                    sampled_row_values = split_value_prefix(value_text, delimiter, remaining)
                    if remaining >= len(column_names) and len(sampled_row_values) + 1 != len(header) and row_count <= 20:
                        inconsistent_row_count += 1
                    sampled_values.extend(sampled_row_values)

        if not header or len(header) < 2 or row_count == 0:
            warnings.append("Matrix has no usable row or column dimension.")
            validation_status = ValidationStatus.INVALID
        else:
            validation_status = ValidationStatus.VALID

        if empty_row_count:
            warnings.append(f"Detected {empty_row_count} empty row(s).")
        if inconsistent_row_count:
            warnings.append(f"Detected {inconsistent_row_count} row(s) with inconsistent column counts.")
        if duplicate_gene_count:
            warnings.append(f"Detected {duplicate_gene_count} duplicated row identifiers.")
        if any(not name for name in column_names):
            warnings.append("Detected empty cell/sample column name(s).")

        orientation = detect_orientation(column_names, row_name_preview)
        if orientation == MatrixOrientation.UNKNOWN:
            warnings.append("Matrix orientation could not be confidently inferred.")

        value_profile = classify_values(sampled_values)
        matrix_type = value_profile.matrix_type
        is_raw_count = matrix_type == MatrixType.RAW_COUNT
        warnings.extend(value_profile.warnings)
        if not is_raw_count:
            warnings.append("Matrix does not look like raw integer counts; formal count-based DE should be disabled.")

        organism = detect_organism(gene_names[:500])
        if organism == Organism.UNKNOWN:
            warnings.append("Organism could not be inferred from sampled gene identifiers.")

        gene_id_type = detect_gene_id_type(gene_names[:500])
        n_genes, n_cells = dimensions_for_orientation(row_count, len(column_names), orientation)
        sparse_format = SparseFormat.DENSE

        if validation_status == ValidationStatus.VALID and warnings:
            validation_status = ValidationStatus.WARNING

        return MatrixInspectionResult(
            path=matrix_path,
            file_type=file_type,
            sample_id=sample_id,
            matrix_type=matrix_type,
            orientation=orientation,
            organism=organism,
            gene_id_type=gene_id_type,
            n_genes=n_genes,
            n_cells=n_cells,
            sparse_format=sparse_format,
            is_raw_count=is_raw_count,
            validation_status=validation_status,
            warnings=warnings,
            gene_preview=row_name_preview[:10],
            cell_preview=column_names[:10],
        )

    def _invalid_empty_file(self, path: Path, file_type: str, sample_id: str) -> MatrixInspectionResult:
        return MatrixInspectionResult(
            path=path,
            file_type=file_type,
            sample_id=sample_id,
            matrix_type=MatrixType.UNKNOWN,
            orientation=MatrixOrientation.UNKNOWN,
            organism=Organism.UNKNOWN,
            gene_id_type=GeneIdType.UNKNOWN,
            n_genes=0,
            n_cells=0,
            sparse_format=SparseFormat.UNKNOWN,
            is_raw_count=False,
            validation_status=ValidationStatus.INVALID,
            warnings=["Matrix file is empty."],
        )


@dataclass(frozen=True)
class ValueProfile:
    matrix_type: MatrixType
    warnings: list[str] = field(default_factory=list)


class DataIngestionService:
    def __init__(
        self,
        platform_service: PlatformObjectService,
        inspector: MatrixFormatInspector | None = None,
    ) -> None:
        self.platform_service = platform_service
        self.inspector = inspector or MatrixFormatInspector()

    def ingest_directory(
        self,
        directory: str | Path,
        project_name: str,
        dataset_name: str | None = None,
        organism: Organism = Organism.UNKNOWN,
        disease_context: str = "",
    ) -> DataIngestionResult:
        data_dir = Path(directory).resolve()
        project = self.platform_service.create_project(
            name=project_name,
            organism=organism,
            disease_context=disease_context,
        )
        dataset = self.platform_service.create_dataset(
            project_id=project.project_id,
            dataset_name=dataset_name or data_dir.name,
            data_type=DataType.SCRNA_SEQ,
            source=DataSource.LOCAL,
            organism=organism,
        )
        ingested = [
            self.ingest_matrix_file(dataset.dataset_id, path)
            for path in sorted(iter_supported_matrix_files(data_dir))
        ]
        return DataIngestionResult(
            project=project,
            dataset=self.platform_service.repository.datasets.require(dataset.dataset_id),
            ingested_matrices=ingested,
        )

    def ingest_matrix_file(self, dataset_id: str, path: str | Path) -> IngestedMatrix:
        inspection = self.inspector.inspect(path)
        uploaded_file = self.platform_service.register_uploaded_file(
            dataset_id=dataset_id,
            original_name=inspection.path.name,
            storage_path=inspection.path,
            file_type=inspection.file_type,
            detected_role=FileRole.EXPRESSION_MATRIX,
        )
        uploaded_file.parse_status = (
            ParseStatus.SUCCESS if inspection.validation_status != ValidationStatus.INVALID else ParseStatus.FAILED
        )
        uploaded_file.upload_status = (
            UploadStatus.PARSED if uploaded_file.parse_status == ParseStatus.SUCCESS else UploadStatus.FAILED
        )
        uploaded_file = self.platform_service.repository.uploaded_files.save(uploaded_file)

        matrix = self.platform_service.register_expression_matrix(
            ExpressionMatrix(
                dataset_id=dataset_id,
                file_id=uploaded_file.file_id,
                matrix_type=inspection.matrix_type,
                orientation=inspection.orientation,
                organism=inspection.organism,
                gene_id_type=inspection.gene_id_type,
                n_genes=inspection.n_genes,
                n_cells=inspection.n_cells,
                sparse_format=inspection.sparse_format,
                storage_path=str(inspection.path),
                is_raw_count=inspection.is_raw_count,
                validation_status=inspection.validation_status,
                warnings=inspection.warnings,
            )
        )
        metadata = self.platform_service.save_sample_metadata(
            SampleMetadata(
                dataset_id=dataset_id,
                sample_id=inspection.sample_id,
                file_name=inspection.path.name,
                species=inspection.organism,
                metadata_source=MetadataSource.INFERRED,
                confirmation_status=ConfirmationStatus.UNCONFIRMED,
            )
        )
        return IngestedMatrix(
            uploaded_file=uploaded_file,
            expression_matrix=matrix,
            sample_metadata=metadata,
            inspection=inspection,
        )


def detect_file_type(path: Path) -> str:
    lower_name = path.name.lower()
    if lower_name.endswith(".csv.gz"):
        return "csv.gz"
    if lower_name.endswith(".tsv.gz"):
        return "tsv.gz"
    if lower_name.endswith(".csv"):
        return "csv"
    if lower_name.endswith(".tsv"):
        return "tsv"
    if lower_name.endswith(".h5ad"):
        return "h5ad"
    if lower_name.endswith(".h5"):
        return "h5"
    if lower_name.endswith(".rds"):
        return "rds"
    if lower_name.endswith(".loom"):
        return "loom"
    return path.suffix.lower().lstrip(".") or "unknown"


def infer_sample_id(file_name: str) -> str:
    match = GSM_SAMPLE_PATTERN.search(file_name)
    if match:
        label = match.group("label")
        return f"{match.group('gsm')}_{label}" if label else match.group("gsm")
    return Path(file_name).name.split(".")[0]


def open_text_matrix(path: Path):
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def clean_delimited_cell(value: str) -> str:
    return value.strip().strip('"').strip("'")


def split_row_name_and_values(line: str, delimiter: str) -> tuple[str, str]:
    if delimiter not in line:
        return clean_delimited_cell(line), ""
    row_name, values = line.split(delimiter, 1)
    return clean_delimited_cell(row_name), values


def split_value_prefix(value_text: str, delimiter: str, limit: int) -> list[str]:
    if limit <= 0 or not value_text:
        return []
    return [clean_delimited_cell(value) for value in value_text.split(delimiter, limit)[:limit]]


def iter_supported_matrix_files(directory: Path) -> Iterable[Path]:
    supported_suffixes = (".csv", ".csv.gz", ".tsv", ".tsv.gz")
    for path in directory.rglob("*"):
        if path.is_file() and path.name.lower().endswith(supported_suffixes):
            yield path


def detect_orientation(column_names: list[str], row_names: list[str]) -> MatrixOrientation:
    column_barcode_score = score_cell_barcodes(column_names[:200])
    row_barcode_score = score_cell_barcodes(row_names[:200])
    column_gene_score = score_gene_names(column_names[:200])
    row_gene_score = score_gene_names(row_names[:200])

    if column_barcode_score >= 0.6 and row_gene_score >= 0.4:
        return MatrixOrientation.GENE_BY_CELL
    if row_barcode_score >= 0.6 and column_gene_score >= 0.4:
        return MatrixOrientation.CELL_BY_GENE
    if len(column_names) > len(row_names) and row_gene_score >= 0.4:
        return MatrixOrientation.GENE_BY_CELL
    return MatrixOrientation.UNKNOWN


def score_cell_barcodes(values: list[str]) -> float:
    non_empty = [value for value in values if value]
    if not non_empty:
        return 0.0
    hits = sum(1 for value in non_empty if TENX_BARCODE_PATTERN.match(value))
    return hits / len(non_empty)


def score_gene_names(values: list[str]) -> float:
    non_empty = [value for value in values if value]
    if not non_empty:
        return 0.0
    hits = 0
    for value in non_empty:
        if ENSEMBL_PATTERN.match(value) or re.match(r"^[A-Za-z][A-Za-z0-9_.-]*$", value):
            hits += 1
    return hits / len(non_empty)


def classify_values(values: list[str]) -> ValueProfile:
    warnings: list[str] = []
    numeric_count = 0
    integer_count = 0
    negative_count = 0
    decimal_count = 0
    missing_count = 0

    for value in values:
        if value == "":
            missing_count += 1
            continue
        try:
            number = float(value)
        except ValueError:
            continue
        numeric_count += 1
        if number < 0:
            negative_count += 1
        if number.is_integer():
            integer_count += 1
        else:
            decimal_count += 1

    if missing_count:
        warnings.append(f"Detected {missing_count} missing sampled expression value(s).")
    if numeric_count == 0:
        return ValueProfile(MatrixType.UNKNOWN, [*warnings, "No numeric expression values were detected in sample."])
    if negative_count:
        return ValueProfile(MatrixType.SCALED, warnings)
    if decimal_count:
        return ValueProfile(MatrixType.NORMALIZED, warnings)
    if integer_count == numeric_count:
        return ValueProfile(MatrixType.RAW_COUNT, warnings)
    return ValueProfile(MatrixType.UNKNOWN, warnings)


def detect_organism(gene_names: list[str]) -> Organism:
    human_mt = sum(1 for gene in gene_names if gene.startswith("MT-"))
    mouse_mt = sum(1 for gene in gene_names if gene.startswith("mt-") or gene.startswith("Mt-"))
    if human_mt > mouse_mt and human_mt > 0:
        return Organism.HUMAN
    if mouse_mt > human_mt and mouse_mt > 0:
        return Organism.MOUSE
    if any(gene.startswith(("AL", "LINC", "FAM")) for gene in gene_names):
        return Organism.HUMAN
    return Organism.UNKNOWN


def detect_gene_id_type(gene_names: list[str]) -> GeneIdType:
    non_empty = [gene for gene in gene_names if gene]
    if not non_empty:
        return GeneIdType.UNKNOWN
    ensembl_hits = sum(1 for gene in non_empty if ENSEMBL_PATTERN.match(gene))
    symbol_hits = sum(1 for gene in non_empty if re.match(r"^[A-Za-z][A-Za-z0-9_.-]*$", gene))
    if ensembl_hits / len(non_empty) >= 0.6:
        return GeneIdType.ENSEMBL
    if symbol_hits / len(non_empty) >= 0.6:
        return GeneIdType.SYMBOL
    if ensembl_hits and symbol_hits:
        return GeneIdType.MIXED
    return GeneIdType.UNKNOWN


def dimensions_for_orientation(
    row_count: int,
    data_column_count: int,
    orientation: MatrixOrientation,
) -> tuple[int, int]:
    if orientation == MatrixOrientation.CELL_BY_GENE:
        return data_column_count, row_count
    return row_count, data_column_count
