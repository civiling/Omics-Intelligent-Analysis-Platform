from __future__ import annotations

import json
from pathlib import Path

from .models import RunVisualizationData


class ResultReader:
    def read_run(self, run_dir: str | Path) -> RunVisualizationData:
        run_path = Path(run_dir).resolve()
        manifest_path = run_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        outputs_dir = run_path / "outputs"
        tables = self._collect(outputs_dir / "tables", ("*.tsv", "*.csv"))
        figure_specs = self._collect(outputs_dir / "figures", ("*.json",))
        notes_dir = outputs_dir / "notes"
        return RunVisualizationData(
            run_dir=run_path,
            manifest=manifest,
            tables=tables,
            figure_specs=figure_specs,
            method_note=self._read_optional(notes_dir / "method_note.md"),
            risk_notes=self._read_optional(notes_dir / "risk_notes.md"),
            evidence_notes=self._read_optional(notes_dir / "evidence_notes.md"),
            report_draft=self._read_optional(notes_dir / "report_draft.md"),
        )

    def _collect(self, directory: Path, patterns: tuple[str, ...]) -> dict[str, Path]:
        if not directory.exists():
            return {}
        found: dict[str, Path] = {}
        for pattern in patterns:
            for path in sorted(directory.glob(pattern)):
                found[str(path.relative_to(directory.parent.parent)).replace("\\", "/")] = path
        return found

    def _read_optional(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""
