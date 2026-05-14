from __future__ import annotations

import json
from pathlib import Path

from .models import Report


class ReportExporter:
    def export_markdown(self, report: Report, output_path: str | Path | None = None) -> Path:
        path = Path(output_path or report.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._to_markdown(report), encoding="utf-8")
        return path

    def export_metadata_json(self, report: Report, output_path: str | Path | None = None) -> Path:
        path = Path(output_path or Path(report.output_path).with_suffix(".metadata.json"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _to_markdown(self, report: Report) -> str:
        lines = [
            f"# {report.title}",
            "",
            f"- report_id: {report.metadata.report_id}",
            f"- run_id: {report.metadata.run_id}",
            f"- workflow_id: {report.metadata.workflow_id}",
            f"- skill_id: {report.metadata.skill_id}",
            f"- status: {report.metadata.status}",
            f"- requires_review: {report.metadata.requires_review}",
            "",
        ]
        for section in report.sections:
            lines.extend([f"## {section.title}", "", section.content, ""])
            if section.source_files:
                lines.append("来源文件：")
                lines.extend([f"- {source}" for source in section.source_files if source])
                lines.append("")
        if report.warnings:
            lines.extend(["## 报告生成警告", ""])
            lines.extend([f"- {warning}" for warning in report.warnings])
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"
