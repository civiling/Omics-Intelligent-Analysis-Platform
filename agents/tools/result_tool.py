from __future__ import annotations

import json
from pathlib import Path


class ResultTool:
    def __init__(self, runs_dir: str | Path | None = None) -> None:
        self.runs_dir = Path(runs_dir or Path(__file__).resolve().parents[2] / "runs").resolve()

    def read_manifest(self, run_id_or_path: str | Path) -> dict:
        path = Path(run_id_or_path)
        if not path.exists():
            path = self.runs_dir / str(run_id_or_path) / "manifest.json"
        if path.is_dir():
            path = path / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def list_output_files(self, run_dir: str | Path) -> dict[str, str]:
        outputs_dir = Path(run_dir) / "outputs"
        if not outputs_dir.exists():
            return {}
        return {
            str(path.relative_to(outputs_dir)).replace("\\", "/"): str(path)
            for path in outputs_dir.rglob("*")
            if path.is_file()
        }

    def summarize_outputs(self, run_dir: str | Path) -> str:
        files = self.list_output_files(run_dir)
        if not files:
            return "No output files were produced."
        grouped = {
            "tables": sorted(path for path in files if path.startswith("tables/")),
            "figures": sorted(path for path in files if path.startswith("figures/")),
            "notes": sorted(path for path in files if path.startswith("notes/")),
        }
        parts = []
        for label, values in grouped.items():
            if values:
                parts.append(f"{label}: {len(values)}")
        return "Generated " + ", ".join(parts) + "."

    def read_method_note(self, run_dir: str | Path) -> str:
        notes_dir = Path(run_dir) / "outputs" / "notes"
        method_path = notes_dir / "method_note.md"
        if method_path.exists():
            return method_path.read_text(encoding="utf-8")
        report_path = notes_dir / "report_draft.md"
        return report_path.read_text(encoding="utf-8") if report_path.exists() else ""

    def read_risk_notes(self, run_dir: str | Path) -> str:
        path = Path(run_dir) / "outputs" / "notes" / "risk_notes.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""
