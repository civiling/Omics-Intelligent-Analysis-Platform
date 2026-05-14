from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.api.schemas import (
    ScrnaEvaluateDesignRequest,
    ScrnaEvaluateDesignResponse,
    ScrnaIngestDirectoryRequest,
    ScrnaMetadataDesignRequest,
    ScrnaQcClusteringRequest,
    WorkflowRunResponse,
)
from backend.services import MetadataDesignService, PlatformObjectService
from backend.storage import PlatformRepository
from workflows import WorkflowRunner, WorkflowStatus
from workflows.exceptions import WorkflowRuntimeError


router = APIRouter(prefix="/scrna", tags=["scrna"])


@router.post("/ingest-directory", response_model=WorkflowRunResponse)
def ingest_directory(request: ScrnaIngestDirectoryRequest) -> WorkflowRunResponse:
    result = run_workflow(
        "scrna.data_ingestion",
        {"matrix_directory": request.matrix_directory},
        {
            "project_name": request.project_name,
            "dataset_name": request.dataset_name,
            "organism": request.organism,
            "disease_context": request.disease_context,
        },
        runs_dir=request.runs_dir,
    )
    return workflow_response(result)


@router.post("/upload-and-ingest", response_model=WorkflowRunResponse)
async def upload_and_ingest(
    files: list[UploadFile] = File(...),
    project_name: str = Form(...),
    dataset_name: str | None = Form(None),
    organism: str = Form("unknown"),
    disease_context: str = Form(""),
    runs_dir: str | None = Form(None),
    upload_dir: str | None = Form(None),
) -> WorkflowRunResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one matrix file is required.")

    target_dir = Path(upload_dir or Path("data") / "raw" / "uploads" / f"upload_{uuid4().hex[:10]}").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        filename = Path(upload.filename or "").name
        if not filename:
            raise HTTPException(status_code=400, detail="Uploaded file is missing a filename.")
        destination = target_dir / filename
        destination.write_bytes(await upload.read())

    result = run_workflow(
        "scrna.data_ingestion",
        {"matrix_directory": str(target_dir)},
        {
            "project_name": project_name,
            "dataset_name": dataset_name,
            "organism": organism,
            "disease_context": disease_context,
        },
        runs_dir=runs_dir,
    )
    return workflow_response(result)


@router.post("/metadata-design", response_model=WorkflowRunResponse)
def metadata_design(request: ScrnaMetadataDesignRequest) -> WorkflowRunResponse:
    result = run_workflow(
        "scrna.metadata_design",
        {
            "platform_store": request.platform_store,
            "metadata_table": request.metadata_table,
        },
        {
            "dataset_id": request.dataset_id,
            "confirm": request.confirm,
            "min_replicates_per_condition": request.min_replicates_per_condition,
        },
        runs_dir=request.runs_dir,
    )
    return workflow_response(result)


@router.post("/qc-clustering", response_model=WorkflowRunResponse)
def qc_clustering(request: ScrnaQcClusteringRequest) -> WorkflowRunResponse:
    result = run_workflow(
        "scrna.qc_clustering",
        {"platform_store": request.platform_store},
        {
            "dataset_id": request.dataset_id,
            "min_genes": request.min_genes,
            "max_genes": request.max_genes,
            "min_counts": request.min_counts,
            "max_counts": request.max_counts,
            "max_mito_pct": request.max_mito_pct,
            "max_cells_per_sample": request.max_cells_per_sample,
            "cluster_count": request.cluster_count,
        },
        runs_dir=request.runs_dir,
    )
    return workflow_response(result)


@router.post("/evaluate-design", response_model=ScrnaEvaluateDesignResponse)
def evaluate_design(request: ScrnaEvaluateDesignRequest) -> ScrnaEvaluateDesignResponse:
    try:
        platform_service = PlatformObjectService(PlatformRepository(request.platform_store))
        result = MetadataDesignService(
            platform_service,
            min_replicates_per_condition=request.min_replicates_per_condition,
        ).evaluate_design(request.dataset_id, persist=request.persist)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ScrnaEvaluateDesignResponse(
        summary=serialize(result.summary),
        recommendation=result.recommendation.to_dict(),
        confidence_gate=result.confidence_gate.to_dict(),
    )


def run_workflow(
    workflow_id: str,
    input_files: dict[str, str],
    parameters: dict[str, Any],
    runs_dir: str | None = None,
):
    try:
        runner = WorkflowRunner(runs_dir=runs_dir) if runs_dir else WorkflowRunner()
        result = runner.run(workflow_id, input_files, parameters)
    except WorkflowRuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if result.status == WorkflowStatus.FAILED:
        raise HTTPException(status_code=500, detail=result.error_message or "Workflow failed.")
    return result


def workflow_response(result) -> WorkflowRunResponse:
    return WorkflowRunResponse(**result.to_dict())


def serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return serialize(asdict(value))
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value
