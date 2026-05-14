from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services import MetadataDesignService, PlatformObjectService
from backend.storage import PlatformRepository
from skill_registry.loader import _load_yaml_file


def main() -> int:
    args = parse_args()
    outputs_dir = Path(args.outputs_dir).resolve()
    inputs = json.loads(Path(args.inputs_json).read_text(encoding="utf-8"))
    parameters = _load_yaml_file(Path(args.parameters_yaml))

    source_store = Path(inputs["platform_store"]).resolve()
    metadata_table = Path(inputs["metadata_table"]).resolve()
    store_dir = outputs_dir / "platform_store"
    copy_store(source_store, store_dir)

    dataset_id = str(parameters["dataset_id"])
    platform_service = PlatformObjectService(PlatformRepository(store_dir))
    design_service = MetadataDesignService(
        platform_service,
        min_replicates_per_condition=int(parameters.get("min_replicates_per_condition") or 2),
    )
    import_result = design_service.import_metadata_file(
        dataset_id,
        metadata_table,
        confirm=bool(parameters.get("confirm", True)),
    )
    design_result = design_service.evaluate_design(dataset_id)
    template_path = design_service.write_metadata_template(
        dataset_id,
        outputs_dir / "tables" / "sample_metadata_template.csv",
    )

    import_report = {
        "dataset_id": dataset_id,
        "metadata_table": str(metadata_table),
        "updated_count": len(import_result.updated_rows),
        "matched_sample_ids": import_result.matched_sample_ids,
        "missing_samples": import_result.missing_samples,
        "unmatched_rows": import_result.unmatched_rows,
    }
    design_payload = {
        "summary": serialize(design_result.summary),
        "recommendation": design_result.recommendation.to_dict(),
        "confidence_gate": design_result.confidence_gate.to_dict(),
        "platform_store": str(store_dir),
        "sample_metadata_template": str(template_path),
    }

    write_json(outputs_dir / "reports" / "metadata_import_report.json", import_report)
    write_json(outputs_dir / "reports" / "experiment_design_summary.json", serialize(design_result.summary))
    write_json(outputs_dir / "reports" / "analysis_mode_recommendation.json", design_result.recommendation.to_dict())
    write_json(outputs_dir / "reports" / "confidence_gate_result.json", design_result.confidence_gate.to_dict())
    write_json(outputs_dir / "reports" / "metadata_design_result.json", design_payload)
    write_text(
        outputs_dir / "notes" / "method_note.md",
        "# Method Note\n\nThe workflow imported sample metadata, matched rows to registered samples, and evaluated condition counts, patient pairing, batch availability, raw count readiness, and analysis mode eligibility.\n",
    )
    write_text(
        outputs_dir / "notes" / "risk_notes.md",
        "# Risk Notes\n\nMetadata-derived recommendations depend on correct condition, patient_id, and batch fields. Review metadata before formal pseudobulk analysis.\n",
    )
    write_json(
        outputs_dir / "metrics.json",
        {
            "workflow_id": "scrna.metadata_design",
            "dataset_id": dataset_id,
            "updated_count": len(import_result.updated_rows),
            "matched_count": len(import_result.matched_sample_ids),
            "missing_sample_count": len(import_result.missing_samples),
            "unmatched_row_count": len(import_result.unmatched_rows),
            "recommended_mode": design_result.recommendation.recommended_mode.value,
            "result_confidence": design_result.recommendation.result_confidence.value,
            "platform_store": str(store_dir),
        },
    )
    print(f"scrna.metadata_design completed for dataset {dataset_id}")
    print(json.dumps({"dataset_id": dataset_id, "recommended_mode": design_result.recommendation.recommended_mode.value}, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scRNA metadata design workflow.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--inputs-json", required=True)
    parser.add_argument("--parameters-yaml", required=True)
    parser.add_argument("--outputs-dir", required=True)
    return parser.parse_args()


def copy_store(source_store: Path, destination_store: Path) -> None:
    if destination_store.exists():
        shutil.rmtree(destination_store)
    shutil.copytree(source_store, destination_store)


def write_json(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return serialize(asdict(value))
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())
