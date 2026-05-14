from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.services.platform_service import PlatformObjectService
from backend.storage.models import (
    AnalysisMode,
    AnalysisModeRecommendation,
    ConfidenceGateResult,
    ConfirmationStatus,
    MetadataSource,
    PairedStatus,
    ResultConfidenceLevel,
    SampleMetadata,
    ValidationStatus,
)


FIELD_ALIASES = {
    "sample_id": {"sample_id", "sample", "sample_name", "gsm", "geo_accession", "accession"},
    "file_name": {"file_name", "filename", "file", "matrix_file", "raw_file"},
    "condition": {"condition", "group", "groups", "phenotype", "status", "case_control"},
    "patient_id": {"patient_id", "patient", "subject_id", "subject", "donor_id", "donor"},
    "batch": {"batch", "batch_id", "lane", "run", "library_batch"},
    "tissue": {"tissue", "tissue_type", "source_tissue"},
    "disease": {"disease", "disease_context", "diagnosis"},
    "time_point": {"time_point", "timepoint", "time"},
    "dose": {"dose", "dosage"},
}


@dataclass(frozen=True)
class ExperimentDesignSummary:
    dataset_id: str
    sample_count: int
    condition_counts: dict[str, int]
    missing_fields: list[str]
    has_condition: bool
    has_two_or_more_conditions: bool
    has_batch: bool
    has_patient_id: bool
    paired_status: PairedStatus
    paired_patient_count: int
    min_replicates_per_condition: int
    raw_count_matrix_count: int
    invalid_matrix_count: int
    can_run_formal_pseudobulk: bool
    can_run_paired_pseudobulk: bool
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MetadataDesignResult:
    summary: ExperimentDesignSummary
    recommendation: AnalysisModeRecommendation
    confidence_gate: ConfidenceGateResult


@dataclass(frozen=True)
class MetadataImportResult:
    updated_rows: list[SampleMetadata]
    unmatched_rows: list[dict[str, Any]]
    missing_samples: list[str]
    matched_sample_ids: list[str]


class MetadataDesignService:
    """Build sample metadata and infer experiment design for Phase 1 scRNA workflows."""

    def __init__(
        self,
        platform_service: PlatformObjectService,
        min_replicates_per_condition: int = 2,
    ) -> None:
        self.platform_service = platform_service
        self.repository = platform_service.repository
        self.min_replicates_per_condition = min_replicates_per_condition

    def build_metadata_template(self, dataset_id: str) -> list[dict[str, Any]]:
        rows = sorted(self.repository.list_dataset_sample_metadata(dataset_id), key=lambda row: row.sample_id)
        return [
            {
                "sample_id": row.sample_id,
                "file_name": row.file_name,
                "condition": row.condition,
                "patient_id": row.patient_id,
                "batch": row.batch,
                "tissue": row.tissue,
                "disease": row.disease,
                "species": row.species.value,
                "time_point": row.time_point,
                "dose": row.dose,
                "paired_status": row.paired_status.value,
                "metadata_source": row.metadata_source.value,
                "confirmation_status": row.confirmation_status.value,
            }
            for row in rows
        ]

    def write_metadata_template(self, dataset_id: str, output_path: str | Path, delimiter: str = ",") -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = self.build_metadata_template(dataset_id)
        fieldnames = [
            "sample_id",
            "file_name",
            "condition",
            "patient_id",
            "batch",
            "tissue",
            "disease",
            "species",
            "time_point",
            "dose",
            "paired_status",
            "metadata_source",
            "confirmation_status",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def import_metadata_file(
        self,
        dataset_id: str,
        metadata_path: str | Path,
        confirm: bool = True,
        delimiter: str | None = None,
    ) -> MetadataImportResult:
        table_rows = read_metadata_table(metadata_path, delimiter)
        existing_rows = self.repository.list_dataset_sample_metadata(dataset_id)
        sample_lookup = build_sample_lookup(existing_rows)
        updates_by_sample_id: dict[str, dict[str, Any]] = {}
        unmatched_rows: list[dict[str, Any]] = []

        for table_row in table_rows:
            normalized_row = normalize_metadata_row(table_row)
            sample_id = resolve_sample_id(normalized_row, sample_lookup)
            if sample_id is None:
                unmatched_rows.append(table_row)
                continue
            updates = {
                key: value
                for key, value in normalized_row.items()
                if key
                in {
                    "condition",
                    "patient_id",
                    "batch",
                    "tissue",
                    "disease",
                    "time_point",
                    "dose",
                }
                and normalize_text(value)
            }
            if updates:
                updates_by_sample_id[sample_id] = updates

        updated_rows = self.update_sample_metadata(dataset_id, updates_by_sample_id, confirm=confirm) if updates_by_sample_id else []
        matched_sample_ids = sorted(updates_by_sample_id)
        all_sample_ids = sorted(row.sample_id for row in existing_rows if row.sample_id)
        missing_samples = [sample_id for sample_id in all_sample_ids if sample_id not in set(matched_sample_ids)]
        return MetadataImportResult(
            updated_rows=updated_rows,
            unmatched_rows=unmatched_rows,
            missing_samples=missing_samples,
            matched_sample_ids=matched_sample_ids,
        )

    def update_sample_metadata(
        self,
        dataset_id: str,
        updates_by_sample_id: dict[str, dict[str, Any]],
        confirm: bool = True,
    ) -> list[SampleMetadata]:
        rows = {row.sample_id: row for row in self.repository.list_dataset_sample_metadata(dataset_id)}
        updated_rows: list[SampleMetadata] = []
        for sample_id, updates in updates_by_sample_id.items():
            if sample_id not in rows:
                raise ValueError(f"Sample {sample_id} does not exist in dataset {dataset_id}.")
            row = rows[sample_id]
            self._apply_updates(row, updates)
            row.metadata_source = MetadataSource.USER
            if confirm:
                row.confirmation_status = ConfirmationStatus.CONFIRMED
            updated_rows.append(self.platform_service.save_sample_metadata(row))
        self._refresh_pairing_status(dataset_id)
        return updated_rows

    def infer_conditions_from_filenames(self, dataset_id: str, confirm: bool = False) -> list[SampleMetadata]:
        rows = self.repository.list_dataset_sample_metadata(dataset_id)
        updates: dict[str, dict[str, Any]] = {}
        for row in rows:
            condition = infer_condition(row.file_name)
            if condition:
                updates[row.sample_id] = {"condition": condition}
        if not updates:
            return []
        return self.update_sample_metadata(dataset_id, updates, confirm=confirm)

    def evaluate_design(self, dataset_id: str, persist: bool = True) -> MetadataDesignResult:
        summary = self.summarize_design(dataset_id)
        recommendation = self._build_recommendation(summary)
        gate = self._build_confidence_gate(summary, recommendation)
        if persist:
            recommendation = self.platform_service.save_analysis_mode_recommendation(recommendation)
            gate = self.platform_service.save_confidence_gate_result(gate)
        return MetadataDesignResult(summary=summary, recommendation=recommendation, confidence_gate=gate)

    def summarize_design(self, dataset_id: str) -> ExperimentDesignSummary:
        self.repository.datasets.require(dataset_id)
        rows = self.repository.list_dataset_sample_metadata(dataset_id)
        matrices = self.repository.list_dataset_matrices(dataset_id)
        condition_counts = Counter(normalize_text(row.condition) for row in rows if normalize_text(row.condition))
        patient_ids = [normalize_text(row.patient_id) for row in rows if normalize_text(row.patient_id)]
        batch_values = [normalize_text(row.batch) for row in rows if normalize_text(row.batch)]
        min_replicates = min(condition_counts.values()) if condition_counts else 0
        raw_count_matrix_count = sum(1 for matrix in matrices if matrix.is_raw_count)
        invalid_matrix_count = sum(1 for matrix in matrices if matrix.validation_status == ValidationStatus.INVALID)

        missing_fields = required_metadata_missing_fields(rows)
        paired_status, paired_patient_count = detect_paired_status(rows)
        has_two_or_more_conditions = len(condition_counts) >= 2
        has_complete_raw_matrices = bool(matrices) and raw_count_matrix_count == len(matrices) and invalid_matrix_count == 0
        can_run_formal = (
            has_two_or_more_conditions
            and min_replicates >= self.min_replicates_per_condition
            and has_complete_raw_matrices
        )
        can_run_paired = can_run_formal and paired_status == PairedStatus.PAIRED

        warnings: list[str] = []
        if not rows:
            warnings.append("No sample metadata rows are available.")
        if not condition_counts:
            warnings.append("condition is missing; group comparison is not available.")
        elif len(condition_counts) == 1:
            warnings.append("Only one condition is present; group comparison is not available.")
        elif min_replicates < self.min_replicates_per_condition:
            warnings.append("At least one condition has insufficient biological replicates.")
        if not has_complete_raw_matrices:
            warnings.append("Not all expression matrices are valid raw count matrices.")
        if not patient_ids:
            warnings.append("patient_id is missing; paired design cannot be evaluated.")

        return ExperimentDesignSummary(
            dataset_id=dataset_id,
            sample_count=len(rows),
            condition_counts=dict(condition_counts),
            missing_fields=missing_fields,
            has_condition=bool(condition_counts),
            has_two_or_more_conditions=has_two_or_more_conditions,
            has_batch=bool(batch_values),
            has_patient_id=bool(patient_ids),
            paired_status=paired_status,
            paired_patient_count=paired_patient_count,
            min_replicates_per_condition=min_replicates,
            raw_count_matrix_count=raw_count_matrix_count,
            invalid_matrix_count=invalid_matrix_count,
            can_run_formal_pseudobulk=can_run_formal,
            can_run_paired_pseudobulk=can_run_paired,
            warnings=warnings,
        )

    def _build_recommendation(self, summary: ExperimentDesignSummary) -> AnalysisModeRecommendation:
        executable_modes: list[AnalysisMode] = []
        blocked_modes: list[AnalysisMode] = []
        missing_information: list[str] = list(summary.missing_fields)
        reasons: list[str] = []

        if summary.sample_count <= 1:
            recommended = AnalysisMode.SINGLE_SAMPLE_CELL_COMPOSITION
            confidence = ResultConfidenceLevel.DESCRIPTIVE
            executable_modes.append(recommended)
            blocked_modes.extend([AnalysisMode.EXPLORATORY_PSEUDOBULK_DE, AnalysisMode.FORMAL_PSEUDOBULK_DE])
            reasons.append("Only one sample is available.")
        elif not summary.has_condition:
            recommended = AnalysisMode.MULTI_SAMPLE_INTEGRATION
            confidence = ResultConfidenceLevel.DESCRIPTIVE
            executable_modes.append(recommended)
            blocked_modes.extend([AnalysisMode.EXPLORATORY_PSEUDOBULK_DE, AnalysisMode.FORMAL_PSEUDOBULK_DE])
            if "condition" not in missing_information:
                missing_information.append("condition")
            reasons.append("Multiple samples are available but condition is missing.")
        elif not summary.has_two_or_more_conditions:
            recommended = AnalysisMode.SAME_GROUP_INTEGRATION
            confidence = ResultConfidenceLevel.DESCRIPTIVE
            executable_modes.append(recommended)
            blocked_modes.extend([AnalysisMode.EXPLORATORY_PSEUDOBULK_DE, AnalysisMode.FORMAL_PSEUDOBULK_DE])
            reasons.append("Metadata contains only one condition.")
        elif summary.can_run_paired_pseudobulk:
            recommended = AnalysisMode.PAIRED_PSEUDOBULK_DE
            confidence = ResultConfidenceLevel.FORMAL_STATISTICAL
            executable_modes.extend(
                [
                    AnalysisMode.MULTI_SAMPLE_INTEGRATION,
                    AnalysisMode.FORMAL_PSEUDOBULK_DE,
                    AnalysisMode.PAIRED_PSEUDOBULK_DE,
                ]
            )
            reasons.append("condition and patient_id support a paired pseudobulk design.")
        elif summary.can_run_formal_pseudobulk:
            recommended = (
                AnalysisMode.MULTI_GROUP_COMPARISON
                if len(summary.condition_counts) >= 3
                else AnalysisMode.FORMAL_PSEUDOBULK_DE
            )
            confidence = ResultConfidenceLevel.FORMAL_STATISTICAL
            executable_modes.extend([AnalysisMode.MULTI_SAMPLE_INTEGRATION, recommended])
            blocked_modes.append(AnalysisMode.PAIRED_PSEUDOBULK_DE)
            if "patient_id" not in missing_information:
                missing_information.append("patient_id")
            reasons.append("Each condition has sufficient biological replicates for formal pseudobulk analysis.")
        else:
            recommended = AnalysisMode.EXPLORATORY_PSEUDOBULK_DE
            confidence = ResultConfidenceLevel.EXPLORATORY
            executable_modes.extend([AnalysisMode.MULTI_SAMPLE_INTEGRATION, recommended])
            blocked_modes.extend([AnalysisMode.FORMAL_PSEUDOBULK_DE, AnalysisMode.PAIRED_PSEUDOBULK_DE])
            reasons.append("Group labels exist, but formal pseudobulk requirements are not fully satisfied.")

        return AnalysisModeRecommendation(
            dataset_id=summary.dataset_id,
            recommended_mode=recommended,
            result_confidence=confidence,
            executable_modes=dedupe_modes(executable_modes),
            blocked_modes=dedupe_modes(blocked_modes),
            reasons=reasons,
            missing_information=sorted(set(missing_information)),
            warnings=summary.warnings,
        )

    def _build_confidence_gate(
        self,
        summary: ExperimentDesignSummary,
        recommendation: AnalysisModeRecommendation,
    ) -> ConfidenceGateResult:
        formal_requested = recommendation.recommended_mode in {
            AnalysisMode.FORMAL_PSEUDOBULK_DE,
            AnalysisMode.PAIRED_PSEUDOBULK_DE,
            AnalysisMode.MULTI_GROUP_COMPARISON,
        }
        passed = not formal_requested or summary.can_run_formal_pseudobulk
        downgrade_reason = None
        downgrade_from = None
        if recommendation.result_confidence == ResultConfidenceLevel.EXPLORATORY:
            downgrade_from = ResultConfidenceLevel.FORMAL_STATISTICAL
            downgrade_reason = "Formal pseudobulk requirements are incomplete."

        return ConfidenceGateResult(
            dataset_id=summary.dataset_id,
            analysis_mode=recommendation.recommended_mode,
            confidence_level=recommendation.result_confidence,
            passed=passed,
            downgrade_from=downgrade_from,
            downgrade_reason=downgrade_reason,
            checks={
                "has_condition": summary.has_condition,
                "has_two_or_more_conditions": summary.has_two_or_more_conditions,
                "has_min_replicates": summary.min_replicates_per_condition >= self.min_replicates_per_condition,
                "has_raw_count_matrices": summary.raw_count_matrix_count > 0 and summary.invalid_matrix_count == 0,
                "has_patient_id": summary.has_patient_id,
                "is_paired": summary.paired_status == PairedStatus.PAIRED,
            },
            warnings=summary.warnings,
        )

    def _refresh_pairing_status(self, dataset_id: str) -> None:
        rows = self.repository.list_dataset_sample_metadata(dataset_id)
        paired_status, _ = detect_paired_status(rows)
        for row in rows:
            if normalize_text(row.patient_id):
                row.paired_status = paired_status
                self.platform_service.save_sample_metadata(row)

    def _apply_updates(self, row: SampleMetadata, updates: dict[str, Any]) -> None:
        allowed_fields = {
            "condition",
            "patient_id",
            "batch",
            "tissue",
            "disease",
            "time_point",
            "dose",
        }
        unknown_fields = set(updates) - allowed_fields
        if unknown_fields:
            raise ValueError(f"Unknown metadata field(s): {', '.join(sorted(unknown_fields))}.")
        for key, value in updates.items():
            setattr(row, key, normalize_optional_text(value))


def infer_condition(file_name: str) -> str | None:
    lowered = file_name.lower()
    if any(token in lowered for token in ("normal", "control", "ctrl", "healthy")):
        return "Normal" if "normal" in lowered or "healthy" in lowered else "Control"
    if any(token in lowered for token in ("tumor", "tumour", "case", "treated", "treatment")):
        return "Tumor" if "tumor" in lowered or "tumour" in lowered or "case" in lowered else "Treatment"
    return None


def read_metadata_table(metadata_path: str | Path, delimiter: str | None = None) -> list[dict[str, str]]:
    path = Path(metadata_path)
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    effective_delimiter = delimiter or infer_delimiter(path, text)
    reader = csv.DictReader(text.splitlines(), delimiter=effective_delimiter)
    return [dict(row) for row in reader]


def infer_delimiter(path: Path, text: str) -> str:
    if path.name.lower().endswith(".tsv"):
        return "\t"
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if "\t" in first_line and first_line.count("\t") >= first_line.count(","):
        return "\t"
    return ","


def normalize_metadata_row(row: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in row.items():
        canonical = canonical_metadata_field(key)
        if canonical:
            output[canonical] = normalize_optional_text(value)
    return output


def canonical_metadata_field(field_name: str | None) -> str | None:
    normalized = normalize_column_name(field_name)
    for canonical, aliases in FIELD_ALIASES.items():
        if normalized in aliases:
            return canonical
    return None


def normalize_column_name(field_name: str | None) -> str:
    if field_name is None:
        return ""
    return str(field_name).strip().lower().replace(" ", "_").replace("-", "_")


def build_sample_lookup(rows: list[SampleMetadata]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in rows:
        if row.sample_id:
            lookup[normalize_match_key(row.sample_id)] = row.sample_id
            gsm_key = normalize_match_key(row.sample_id.split("_")[0])
            lookup.setdefault(gsm_key, row.sample_id)
        if row.file_name:
            lookup[normalize_match_key(row.file_name)] = row.sample_id
            lookup[normalize_match_key(Path(row.file_name).name.split(".")[0])] = row.sample_id
    return lookup


def resolve_sample_id(row: dict[str, Any], lookup: dict[str, str]) -> str | None:
    for field in ("sample_id", "file_name"):
        value = row.get(field)
        if not value:
            continue
        key = normalize_match_key(str(value))
        if key in lookup:
            return lookup[key]
        stem_key = normalize_match_key(Path(str(value)).name.split(".")[0])
        if stem_key in lookup:
            return lookup[stem_key]
    return None


def normalize_match_key(value: str) -> str:
    return value.strip().lower()


def required_metadata_missing_fields(rows: list[SampleMetadata]) -> list[str]:
    if not rows:
        return ["sample_id", "condition"]
    missing: list[str] = []
    if any(not normalize_text(row.sample_id) for row in rows):
        missing.append("sample_id")
    if any(not normalize_text(row.condition) for row in rows):
        missing.append("condition")
    if any(not normalize_text(row.patient_id) for row in rows):
        missing.append("patient_id")
    if any(not normalize_text(row.batch) for row in rows):
        missing.append("batch")
    return missing


def detect_paired_status(rows: list[SampleMetadata]) -> tuple[PairedStatus, int]:
    condition_values = sorted({normalize_text(row.condition) for row in rows if normalize_text(row.condition)})
    if len(condition_values) != 2:
        return PairedStatus.UNKNOWN, 0

    patient_to_conditions: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        patient_id = normalize_text(row.patient_id)
        condition = normalize_text(row.condition)
        if patient_id and condition:
            patient_to_conditions[patient_id].append(condition)

    if not patient_to_conditions:
        return PairedStatus.UNKNOWN, 0

    paired_patients = 0
    expected = set(condition_values)
    for conditions in patient_to_conditions.values():
        if set(conditions) == expected and len(conditions) == len(expected):
            paired_patients += 1

    if paired_patients and paired_patients == len(patient_to_conditions):
        return PairedStatus.PAIRED, paired_patients
    return PairedStatus.UNPAIRED, paired_patients


def dedupe_modes(modes: list[AnalysisMode]) -> list[AnalysisMode]:
    output: list[AnalysisMode] = []
    for mode in modes:
        if mode not in output:
            output.append(mode)
    return output


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_optional_text(value: Any) -> str | None:
    normalized = normalize_text(value)
    return normalized or None
