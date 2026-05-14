from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services import DataIngestionService, MetadataDesignService, PlatformObjectService
from backend.storage import Organism, PlatformRepository
from skill_registry.loader import _load_yaml_file


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    outputs_dir = Path(args.outputs_dir).resolve()
    inputs = json.loads(Path(args.inputs_json).read_text(encoding="utf-8"))
    parameters = _load_yaml_file(Path(args.parameters_yaml))

    matrix_directory = Path(inputs["matrix_directory"]).resolve()
    store_dir = outputs_dir / "platform_store"
    platform_service = PlatformObjectService(PlatformRepository(store_dir))
    result = DataIngestionService(platform_service).ingest_directory(
        directory=matrix_directory,
        project_name=str(parameters["project_name"]),
        dataset_name=parameters.get("dataset_name"),
        organism=Organism(str(parameters.get("organism") or "unknown")),
        disease_context=str(parameters.get("disease_context") or ""),
    )

    design_service = MetadataDesignService(platform_service)
    template_path = design_service.write_metadata_template(
        result.dataset.dataset_id,
        outputs_dir / "tables" / "sample_metadata_template.csv",
    )

    expression_manifest = [
        item.expression_matrix.to_dict()
        for item in result.ingested_matrices
    ]
    sample_metadata = [
        item.sample_metadata.to_dict()
        for item in result.ingested_matrices
    ]
    readiness_report = {
        "project": result.project.to_dict(),
        "dataset": result.dataset.to_dict(),
        "matrix_directory": str(matrix_directory),
        "matrix_count": len(result.ingested_matrices),
        "total_genes": result.total_genes,
        "total_cells": result.total_cells,
        "warnings": result.warnings,
        "platform_store": str(store_dir),
        "sample_metadata_template": str(template_path),
    }

    write_json(outputs_dir / "tables" / "expression_matrix_manifest.json", expression_manifest)
    write_json(outputs_dir / "tables" / "sample_metadata_draft.json", sample_metadata)
    write_json(outputs_dir / "reports" / "data_readiness_report.json", readiness_report)
    write_text(
        outputs_dir / "notes" / "method_note.md",
        "# Method Note\n\nThe workflow inspected delimited scRNA-seq matrices and registered platform objects for uploaded files, expression matrices, and draft sample metadata.\n",
    )
    write_text(
        outputs_dir / "notes" / "risk_notes.md",
        "# Risk Notes\n\nInferred sample metadata is provisional. condition, patient_id, and batch must be confirmed before formal pseudobulk analysis.\n",
    )
    write_json(
        outputs_dir / "metrics.json",
        {
            "workflow_id": "scrna.data_ingestion",
            "project_id": result.project.project_id,
            "dataset_id": result.dataset.dataset_id,
            "matrix_count": len(result.ingested_matrices),
            "total_genes": result.total_genes,
            "total_cells": result.total_cells,
            "warning_count": len(result.warnings),
            "platform_store": str(store_dir),
        },
    )
    print(f"scrna.data_ingestion completed for dataset {result.dataset.dataset_id}")
    print(json.dumps({"dataset_id": result.dataset.dataset_id, "platform_store": str(store_dir)}, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scRNA data ingestion workflow.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--inputs-json", required=True)
    parser.add_argument("--parameters-yaml", required=True)
    parser.add_argument("--outputs-dir", required=True)
    return parser.parse_args()


def write_json(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
