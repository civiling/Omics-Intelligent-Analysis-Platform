from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write deterministic placeholder workflow outputs.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--inputs-json", required=True)
    parser.add_argument("--parameters-yaml", required=True)
    parser.add_argument("--outputs-dir", required=True)
    return parser.parse_args()


def write_text(outputs_dir: Path, relative_path: str, content: str) -> None:
    path = outputs_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(outputs_dir: Path, relative_path: str, content: dict) -> None:
    path = outputs_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")


def write_metrics(outputs_dir: Path, workflow_id: str) -> None:
    write_json(
        outputs_dir,
        "metrics.json",
        {"placeholder_script": True, "workflow_id": workflow_id},
    )
