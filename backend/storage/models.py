from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints
from uuid import uuid4


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DataType(str, Enum):
    SCRNA_SEQ = "scRNA-seq"
    BULK_RNA_SEQ = "bulk RNA-seq"
    SPATIAL = "spatial"
    UNKNOWN = "unknown"


class DataSource(str, Enum):
    USER_UPLOAD = "user_upload"
    GEO = "GEO"
    LOCAL = "local"


class Organism(str, Enum):
    HUMAN = "human"
    MOUSE = "mouse"
    UNKNOWN = "unknown"


class MetadataStatus(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"
    COMPLETE = "complete"


class UploadStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    FAILED = "failed"


class ParseStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class FileRole(str, Enum):
    EXPRESSION_MATRIX = "expression_matrix"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class MatrixType(str, Enum):
    RAW_COUNT = "raw_count"
    NORMALIZED = "normalized"
    SCALED = "scaled"
    UNKNOWN = "unknown"


class MatrixOrientation(str, Enum):
    GENE_BY_CELL = "gene_by_cell"
    CELL_BY_GENE = "cell_by_gene"
    UNKNOWN = "unknown"


class GeneIdType(str, Enum):
    SYMBOL = "symbol"
    ENSEMBL = "ensembl"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class SparseFormat(str, Enum):
    CSR = "csr"
    CSC = "csc"
    DENSE = "dense"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"


class PairedStatus(str, Enum):
    PAIRED = "paired"
    UNPAIRED = "unpaired"
    UNKNOWN = "unknown"


class MetadataSource(str, Enum):
    USER = "user"
    INFERRED = "inferred"
    GEO = "GEO"


class ConfirmationStatus(str, Enum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"


class WorkflowTaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class WorkflowRunStatus(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    PARTIALLY_FAILED = "partially_failed"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AnalysisMode(str, Enum):
    SINGLE_SAMPLE_CELL_COMPOSITION = "single_sample_cell_composition"
    MULTI_SAMPLE_INTEGRATION = "multi_sample_integration"
    SAME_GROUP_INTEGRATION = "same_group_integration"
    EXPLORATORY_PSEUDOBULK_DE = "exploratory_pseudobulk_de"
    FORMAL_PSEUDOBULK_DE = "formal_pseudobulk_de"
    PAIRED_PSEUDOBULK_DE = "paired_pseudobulk_de"
    MULTI_GROUP_COMPARISON = "multi_group_comparison"
    TIME_SERIES = "time_series"
    DOSE_RESPONSE = "dose_response"


class ResultConfidenceLevel(str, Enum):
    DESCRIPTIVE = "descriptive"
    EXPLORATORY = "exploratory"
    FORMAL_STATISTICAL = "formal_statistical"
    INFERENTIAL = "inferential"


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class SerializableModel:
    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        hints = get_type_hints(cls)
        values: dict[str, Any] = {}
        for model_field in fields(cls):
            if model_field.name not in data:
                continue
            values[model_field.name] = _coerce_value(hints.get(model_field.name), data[model_field.name])
        return cls(**values)


@dataclass
class Project(SerializableModel):
    project_id: str = field(default_factory=lambda: new_id("proj"))
    name: str = ""
    description: str = ""
    organism: Organism = Organism.UNKNOWN
    disease_context: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: ProjectStatus = ProjectStatus.ACTIVE
    default_analysis_mode: str | None = None


@dataclass
class Dataset(SerializableModel):
    dataset_id: str = field(default_factory=lambda: new_id("ds"))
    project_id: str = ""
    dataset_name: str = ""
    data_type: DataType = DataType.SCRNA_SEQ
    source: DataSource = DataSource.USER_UPLOAD
    organism: Organism = Organism.UNKNOWN
    file_count: int = 0
    sample_count: int = 0
    matrix_count: int = 0
    metadata_status: MetadataStatus = MetadataStatus.MISSING
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class UploadedFile(SerializableModel):
    file_id: str = field(default_factory=lambda: new_id("file"))
    dataset_id: str = ""
    original_name: str = ""
    storage_path: str = ""
    file_type: str = ""
    file_size: int = 0
    md5: str | None = None
    upload_status: UploadStatus = UploadStatus.UPLOADED
    parse_status: ParseStatus = ParseStatus.PENDING
    detected_role: FileRole = FileRole.UNKNOWN
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExpressionMatrix(SerializableModel):
    matrix_id: str = field(default_factory=lambda: new_id("matrix"))
    dataset_id: str = ""
    file_id: str = ""
    matrix_type: MatrixType = MatrixType.UNKNOWN
    orientation: MatrixOrientation = MatrixOrientation.UNKNOWN
    organism: Organism = Organism.UNKNOWN
    gene_id_type: GeneIdType = GeneIdType.UNKNOWN
    n_genes: int = 0
    n_cells: int = 0
    sparse_format: SparseFormat = SparseFormat.UNKNOWN
    storage_path: str = ""
    is_raw_count: bool = False
    validation_status: ValidationStatus = ValidationStatus.WARNING
    warnings: list[str] = field(default_factory=list)


@dataclass
class SampleMetadata(SerializableModel):
    sample_metadata_id: str = field(default_factory=lambda: new_id("smeta"))
    dataset_id: str = ""
    sample_id: str = ""
    file_name: str = ""
    condition: str | None = None
    patient_id: str | None = None
    batch: str | None = None
    tissue: str | None = None
    disease: str | None = None
    species: Organism = Organism.UNKNOWN
    time_point: str | None = None
    dose: str | None = None
    paired_status: PairedStatus = PairedStatus.UNKNOWN
    metadata_source: MetadataSource = MetadataSource.INFERRED
    confirmation_status: ConfirmationStatus = ConfirmationStatus.UNCONFIRMED


@dataclass
class WorkflowTask(SerializableModel):
    task_id: str = field(default_factory=lambda: new_id("task"))
    workflow_run_id: str = ""
    task_name: str = ""
    task_type: str = ""
    status: WorkflowTaskStatus = WorkflowTaskStatus.PENDING
    input_objects: list[str] = field(default_factory=list)
    output_objects: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    log_path: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass
class WorkflowRun(SerializableModel):
    workflow_run_id: str = field(default_factory=lambda: new_id("wrun"))
    project_id: str = ""
    dataset_id: str = ""
    workflow_name: str = ""
    analysis_mode: AnalysisMode | None = None
    status: WorkflowRunStatus = WorkflowRunStatus.INITIALIZED
    input_summary: dict[str, Any] = field(default_factory=dict)
    task_list: list[str] = field(default_factory=list)
    result_summary: dict[str, Any] = field(default_factory=dict)
    software_versions: dict[str, str] = field(default_factory=dict)
    database_versions: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None


@dataclass
class AnalysisModeRecommendation(SerializableModel):
    recommendation_id: str = field(default_factory=lambda: new_id("arec"))
    dataset_id: str = ""
    recommended_mode: AnalysisMode = AnalysisMode.SINGLE_SAMPLE_CELL_COMPOSITION
    result_confidence: ResultConfidenceLevel = ResultConfidenceLevel.DESCRIPTIVE
    executable_modes: list[AnalysisMode] = field(default_factory=list)
    blocked_modes: list[AnalysisMode] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConfidenceGateResult(SerializableModel):
    gate_result_id: str = field(default_factory=lambda: new_id("gate"))
    dataset_id: str = ""
    analysis_mode: AnalysisMode = AnalysisMode.SINGLE_SAMPLE_CELL_COMPOSITION
    confidence_level: ResultConfidenceLevel = ResultConfidenceLevel.DESCRIPTIVE
    passed: bool = True
    downgrade_from: ResultConfidenceLevel | None = None
    downgrade_reason: str | None = None
    checks: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _coerce_value(type_hint: Any, value: Any) -> Any:
    if value is None or type_hint is None:
        return value

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    if origin in (list,):
        item_type = args[0] if args else Any
        return [_coerce_value(item_type, item) for item in value]
    if origin in (dict,):
        return dict(value)
    if origin in (type(None),):
        return value
    if origin is not None and type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        return _coerce_value(non_none[0] if non_none else Any, value)

    if isinstance(type_hint, type) and issubclass(type_hint, Enum):
        return type_hint(value)
    if type_hint is datetime:
        return datetime.fromisoformat(value)
    if type_hint is Path:
        return Path(value)
    return value
