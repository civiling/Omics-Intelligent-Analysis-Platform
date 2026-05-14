from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from workflows import WorkflowRunner


router = APIRouter(prefix="/workflow-runs", tags=["workflow-runs"])


@router.get("")
def list_workflow_runs(runs_dir: str | None = Query(None)) -> list[dict]:
    root = resolve_runs_root(runs_dir)
    if not root.exists():
        return []
    runs: list[dict] = []
    for manifest_path in sorted(root.glob("run_*/manifest.json"), reverse=True):
        runs.append(load_json(manifest_path))
    return runs


@router.get("/{run_id}")
def get_workflow_run(run_id: str, runs_dir: str | None = Query(None)) -> dict:
    return load_json(resolve_run_dir(run_id, runs_dir) / "manifest.json")


@router.get("/{run_id}/outputs")
def list_workflow_outputs(run_id: str, runs_dir: str | None = Query(None)) -> dict:
    manifest = get_workflow_run(run_id, runs_dir)
    return manifest.get("output_files", {})


@router.get("/{run_id}/outputs/{output_path:path}")
def get_workflow_output_file(
    run_id: str,
    output_path: str,
    runs_dir: str | None = Query(None),
):
    run_dir = resolve_run_dir(run_id, runs_dir)
    outputs_dir = (run_dir / "outputs").resolve()
    path = (outputs_dir / output_path).resolve()
    if outputs_dir != path and outputs_dir not in path.parents:
        raise HTTPException(status_code=400, detail="Output path must stay inside the run outputs directory.")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Output file {output_path} was not found.")
    if path.suffix.lower() == ".json":
        return JSONResponse(load_json(path))
    return FileResponse(path)


def resolve_runs_root(runs_dir: str | None) -> Path:
    return Path(runs_dir).resolve() if runs_dir else WorkflowRunner().runs_dir


def resolve_run_dir(run_id: str, runs_dir: str | None) -> Path:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run id.")
    run_dir = (resolve_runs_root(runs_dir) / run_id).resolve()
    if not run_dir.exists() or not (run_dir / "manifest.json").exists():
        raise HTTPException(status_code=404, detail=f"Workflow run {run_id} was not found.")
    return run_dir


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Could not parse JSON file {path}: {exc}") from exc

