from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowRunResponse(BaseModel):
    run_id: str
    status: str
    output_files: dict[str, str] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    logs: dict[str, str] = Field(default_factory=dict)
    manifest_path: str | None = None
    error_message: str | None = None


class ScrnaIngestDirectoryRequest(BaseModel):
    matrix_directory: str
    project_name: str
    dataset_name: str | None = None
    organism: str = "unknown"
    disease_context: str = ""
    runs_dir: str | None = None
    upload_dir: str | None = None


class ScrnaMetadataDesignRequest(BaseModel):
    platform_store: str
    metadata_table: str
    dataset_id: str
    confirm: bool = True
    min_replicates_per_condition: int = 2
    runs_dir: str | None = None


class ScrnaEvaluateDesignRequest(BaseModel):
    platform_store: str
    dataset_id: str
    min_replicates_per_condition: int = 2
    persist: bool = True


class ScrnaQcClusteringRequest(BaseModel):
    platform_store: str
    dataset_id: str
    min_genes: int = 200
    max_genes: int | None = None
    min_counts: int = 0
    max_counts: int | None = None
    max_mito_pct: float = 20.0
    max_cells_per_sample: int = 2000
    cluster_count: int = 4
    runs_dir: str | None = None


class ScrnaEvaluateDesignResponse(BaseModel):
    summary: dict[str, Any]
    recommendation: dict[str, Any]
    confidence_gate: dict[str, Any]
