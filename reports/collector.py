from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill_registry.loader import _load_yaml_file


class ReportDataCollector:
    def collect(self, run_dir: str | Path) -> dict[str, Any]:
        run_path = Path(run_dir).resolve()
        warnings: list[str] = []
        outputs_dir = run_path / "outputs"
        notes_dir = outputs_dir / "notes"
        data = {
            "run_dir": run_path,
            "manifest_path": run_path / "manifest.json",
            "manifest": self._read_json(run_path / "manifest.json", warnings, required=True),
            "parameters_path": run_path / "parameters.yaml",
            "parameters": self._read_yaml(run_path / "parameters.yaml", warnings),
            "tables": self._collect_files(outputs_dir / "tables", ("*.tsv", "*.csv")),
            "figures": self._collect_files(outputs_dir / "figures", ("*.json",)),
            "method_note": self._read_text(notes_dir / "method_note.md", warnings),
            "risk_notes": self._read_text(notes_dir / "risk_notes.md", warnings),
            "evidence_notes": self._read_text(notes_dir / "evidence_notes.md", warnings),
            "report_draft": self._read_text(notes_dir / "report_draft.md", warnings),
            "agent_trace": self._read_json(run_path / "agent_trace.json", warnings),
            "provenance": self._read_json(run_path / "provenance.json", warnings),
            "warnings": warnings,
        }
        return data

    def _collect_files(self, directory: Path, patterns: tuple[str, ...]) -> dict[str, Path]:
        if not directory.exists():
            return {}
        found: dict[str, Path] = {}
        for pattern in patterns:
            for path in sorted(directory.glob(pattern)):
                found[str(path.relative_to(directory.parent.parent)).replace("\\", "/")] = path
        return found

    def _read_json(self, path: Path, warnings: list[str], required: bool = False) -> dict[str, Any]:
        if not path.exists():
            if required:
                warnings.append(f"Missing required file: {path.name}")
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            warnings.append(f"Could not read JSON {path}: {exc}")
            return {}

    def _read_yaml(self, path: Path, warnings: list[str]) -> dict[str, Any]:
        if not path.exists():
            warnings.append(f"Missing parameters file: {path.name}")
            return {}
        try:
            return _load_yaml_file(path)
        except Exception as exc:
            warnings.append(f"Could not read YAML {path}: {exc}")
            return {}

    def _read_text(self, path: Path, warnings: list[str]) -> str:
        if not path.exists():
            warnings.append(f"Missing optional note: {path.name}")
            return ""
        return path.read_text(encoding="utf-8")
