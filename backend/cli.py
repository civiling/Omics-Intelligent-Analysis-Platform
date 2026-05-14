from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from backend.services import DataIngestionService, MetadataDesignService, PlatformObjectService
from backend.storage import Organism, PlatformRepository


DEFAULT_STORE_DIR = Path("data/processed/platform_store")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend",
        description="Platform CLI for data ingestion, metadata import, and experiment design recommendation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest-directory", help="Ingest a directory of expression matrices.")
    add_store_argument(ingest_parser)
    ingest_parser.add_argument("--data-dir", required=True, help="Directory containing matrix files.")
    ingest_parser.add_argument("--project-name", required=True, help="Project name to create.")
    ingest_parser.add_argument("--dataset-name", default=None, help="Dataset name. Defaults to data directory name.")
    ingest_parser.add_argument("--organism", default="unknown", choices=[item.value for item in Organism])
    ingest_parser.add_argument("--disease-context", default="", help="Optional disease context.")
    ingest_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    ingest_parser.set_defaults(func=cmd_ingest_directory)

    template_parser = subparsers.add_parser("export-metadata-template", help="Export a metadata CSV/TSV template.")
    add_store_argument(template_parser)
    template_parser.add_argument("--dataset-id", required=True, help="Dataset id.")
    template_parser.add_argument("--output", required=True, help="Output CSV/TSV path.")
    template_parser.add_argument("--tsv", action="store_true", help="Write tab-delimited output instead of CSV.")
    template_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    template_parser.set_defaults(func=cmd_export_metadata_template)

    import_parser = subparsers.add_parser("import-metadata", help="Import sample metadata CSV/TSV.")
    add_store_argument(import_parser)
    import_parser.add_argument("--dataset-id", required=True, help="Dataset id.")
    import_parser.add_argument("--metadata", required=True, help="Metadata CSV/TSV path.")
    import_parser.add_argument("--delimiter", default=None, help="Optional delimiter override.")
    import_parser.add_argument("--no-confirm", action="store_true", help="Do not mark imported rows as confirmed.")
    import_parser.add_argument("--evaluate", action="store_true", help="Evaluate design after import.")
    import_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    import_parser.set_defaults(func=cmd_import_metadata)

    evaluate_parser = subparsers.add_parser("evaluate-design", help="Evaluate metadata and recommend analysis mode.")
    add_store_argument(evaluate_parser)
    evaluate_parser.add_argument("--dataset-id", required=True, help="Dataset id.")
    evaluate_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    evaluate_parser.set_defaults(func=cmd_evaluate_design)
    return parser


def add_store_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--store-dir",
        default=str(DEFAULT_STORE_DIR),
        help=f"Platform JSON store directory. Defaults to {DEFAULT_STORE_DIR}.",
    )


def cmd_ingest_directory(args: argparse.Namespace) -> int:
    platform_service = build_platform_service(args.store_dir)
    result = DataIngestionService(platform_service).ingest_directory(
        directory=args.data_dir,
        project_name=args.project_name,
        dataset_name=args.dataset_name,
        organism=Organism(args.organism),
        disease_context=args.disease_context,
    )
    payload = {
        "project": result.project.to_dict(),
        "dataset": result.dataset.to_dict(),
        "matrix_count": len(result.ingested_matrices),
        "total_genes": result.total_genes,
        "total_cells": result.total_cells,
        "warnings": result.warnings,
        "store_dir": str(Path(args.store_dir).resolve()),
    }
    print_payload(payload, args.json)
    return 0


def cmd_export_metadata_template(args: argparse.Namespace) -> int:
    platform_service = build_platform_service(args.store_dir)
    delimiter = "\t" if args.tsv else ","
    output_path = MetadataDesignService(platform_service).write_metadata_template(
        args.dataset_id,
        args.output,
        delimiter=delimiter,
    )
    payload = {
        "dataset_id": args.dataset_id,
        "output_path": str(output_path.resolve()),
    }
    print_payload(payload, args.json)
    return 0


def cmd_import_metadata(args: argparse.Namespace) -> int:
    platform_service = build_platform_service(args.store_dir)
    design_service = MetadataDesignService(platform_service)
    import_result = design_service.import_metadata_file(
        args.dataset_id,
        args.metadata,
        confirm=not args.no_confirm,
        delimiter=args.delimiter,
    )
    payload: dict[str, Any] = {
        "dataset_id": args.dataset_id,
        "updated_count": len(import_result.updated_rows),
        "matched_sample_ids": import_result.matched_sample_ids,
        "missing_samples": import_result.missing_samples,
        "unmatched_rows": import_result.unmatched_rows,
    }
    if args.evaluate:
        payload["design"] = design_result_payload(design_service.evaluate_design(args.dataset_id))
    print_payload(payload, args.json)
    return 0 if not import_result.unmatched_rows else 2


def cmd_evaluate_design(args: argparse.Namespace) -> int:
    platform_service = build_platform_service(args.store_dir)
    result = MetadataDesignService(platform_service).evaluate_design(args.dataset_id)
    payload = design_result_payload(result)
    print_payload(payload, args.json)
    return 0


def build_platform_service(store_dir: str | Path) -> PlatformObjectService:
    return PlatformObjectService(PlatformRepository(store_dir))


def design_result_payload(result) -> dict[str, Any]:
    return {
        "summary": serialize(result.summary),
        "recommendation": result.recommendation.to_dict(),
        "confidence_gate": result.confidence_gate.to_dict(),
    }


def print_payload(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(serialize(payload), indent=2, ensure_ascii=False))
        return
    for key, value in serialize(payload).items():
        print(f"{key}: {value}")


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


if __name__ == "__main__":
    sys.exit(main())
