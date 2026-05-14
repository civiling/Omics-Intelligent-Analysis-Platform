from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .collector import ReportDataCollector
from .exporter import ReportExporter
from .models import Report, ReportMetadata, ReportType
from .reviewer import ReportReviewer
from .section_builder import ReportSectionBuilder


class ReportGenerator:
    def __init__(
        self,
        collector: ReportDataCollector | None = None,
        section_builder: ReportSectionBuilder | None = None,
        exporter: ReportExporter | None = None,
        reviewer: ReportReviewer | None = None,
    ) -> None:
        self.collector = collector or ReportDataCollector()
        self.section_builder = section_builder or ReportSectionBuilder()
        self.exporter = exporter or ReportExporter()
        self.reviewer = reviewer or ReportReviewer()

    def generate_markdown_report(
        self,
        run_dir: str | Path,
        report_type: str | ReportType = ReportType.EXPERT_REPORT,
    ) -> Report:
        run_path = Path(run_dir).resolve()
        collected = self.collector.collect(run_path)
        sections = self.build_sections(collected)
        manifest = collected.get("manifest", {})
        workflow_config = manifest.get("workflow_config") or {}
        report_type_enum = self._report_type(report_type)
        metadata = ReportMetadata(
            report_id=f"report_{uuid4().hex[:10]}",
            run_id=manifest.get("run_id", run_path.name),
            workflow_id=manifest.get("workflow_id"),
            skill_id=manifest.get("skill_id"),
            generated_at=datetime.now(),
            report_type=report_type_enum,
            status=manifest.get("status", "unknown"),
            requires_review=bool(workflow_config.get("requires_review", False)),
            source_manifest=str(collected.get("manifest_path")) if collected.get("manifest_path") else None,
        )
        report = Report(
            metadata=metadata,
            title="多组学智能分析报告",
            sections=sections,
            output_path=run_path / "outputs" / "report.md",
            warnings=list(collected.get("warnings", [])),
        )
        reviewer_warnings = self.reviewer.review(report)
        report = Report(
            metadata=report.metadata,
            title=report.title,
            sections=report.sections,
            output_path=report.output_path,
            warnings=[*report.warnings, *reviewer_warnings],
        )
        self.write_report(report, report.output_path)
        self.exporter.export_metadata_json(report)
        return report

    def build_sections(self, collected_data: dict) -> list:
        return self.section_builder.build_sections(collected_data)

    def write_report(self, report: Report, output_path: str | Path) -> Path:
        return self.exporter.export_markdown(report, output_path)

    def _report_type(self, report_type: str | ReportType) -> ReportType:
        if isinstance(report_type, ReportType):
            return report_type
        return ReportType(str(report_type))
