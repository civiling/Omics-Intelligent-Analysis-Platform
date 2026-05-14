from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.api.schemas import SampleMetadataUpdateRequest, SampleMetadataUpdateResponse
from backend.services import MetadataDesignService, PlatformObjectService
from backend.storage import PlatformRepository


router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/projects")
def list_projects(store_dir: str = Query(...)) -> list[dict]:
    repository = PlatformRepository(store_dir)
    return [project.to_dict() for project in repository.projects.list()]


@router.get("/datasets")
def list_datasets(
    store_dir: str = Query(...),
    project_id: str | None = None,
) -> list[dict]:
    repository = PlatformRepository(store_dir)
    datasets = repository.datasets.list()
    if project_id:
        datasets = [dataset for dataset in datasets if dataset.project_id == project_id]
    return [dataset.to_dict() for dataset in datasets]


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, store_dir: str = Query(...)) -> dict:
    dataset = PlatformRepository(store_dir).datasets.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} was not found.")
    return dataset.to_dict()


@router.get("/datasets/{dataset_id}/files")
def list_dataset_files(dataset_id: str, store_dir: str = Query(...)) -> list[dict]:
    repository = PlatformRepository(store_dir)
    repository.datasets.require(dataset_id)
    return [item.to_dict() for item in repository.list_dataset_files(dataset_id)]


@router.get("/datasets/{dataset_id}/matrices")
def list_dataset_matrices(dataset_id: str, store_dir: str = Query(...)) -> list[dict]:
    repository = PlatformRepository(store_dir)
    repository.datasets.require(dataset_id)
    return [item.to_dict() for item in repository.list_dataset_matrices(dataset_id)]


@router.get("/datasets/{dataset_id}/sample-metadata")
def list_dataset_sample_metadata(dataset_id: str, store_dir: str = Query(...)) -> list[dict]:
    repository = PlatformRepository(store_dir)
    repository.datasets.require(dataset_id)
    return [item.to_dict() for item in repository.list_dataset_sample_metadata(dataset_id)]


@router.patch("/datasets/{dataset_id}/sample-metadata", response_model=SampleMetadataUpdateResponse)
def update_dataset_sample_metadata(
    dataset_id: str,
    request: SampleMetadataUpdateRequest,
    store_dir: str = Query(...),
) -> SampleMetadataUpdateResponse:
    repository = PlatformRepository(store_dir)
    repository.datasets.require(dataset_id)
    service = MetadataDesignService(
        PlatformObjectService(repository),
        min_replicates_per_condition=request.min_replicates_per_condition,
    )
    try:
        updated_rows = service.update_sample_metadata(
            dataset_id,
            request.updates_by_sample_id,
            confirm=request.confirm,
        )
        design_payload = None
        if request.evaluate:
            design = service.evaluate_design(dataset_id)
            design_payload = {
                "summary": serialize(design.summary),
                "recommendation": design.recommendation.to_dict(),
                "confidence_gate": design.confidence_gate.to_dict(),
            }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SampleMetadataUpdateResponse(
        updated_rows=[row.to_dict() for row in updated_rows],
        design=design_payload,
    )


@router.get("/datasets/{dataset_id}/analysis-recommendations")
def list_dataset_analysis_recommendations(dataset_id: str, store_dir: str = Query(...)) -> list[dict]:
    repository = PlatformRepository(store_dir)
    repository.datasets.require(dataset_id)
    recommendations = repository.analysis_mode_recommendations.filter_by(dataset_id=dataset_id)
    return [item.to_dict() for item in recommendations]


@router.get("/datasets/{dataset_id}/confidence-gates")
def list_dataset_confidence_gates(dataset_id: str, store_dir: str = Query(...)) -> list[dict]:
    repository = PlatformRepository(store_dir)
    repository.datasets.require(dataset_id)
    gates = repository.confidence_gate_results.filter_by(dataset_id=dataset_id)
    return [item.to_dict() for item in gates]


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
