from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ReportType(str, Enum):
    EXPERT_REPORT = "expert_report"
    TECHNICAL_REPORT = "technical_report"
    SUMMARY_REPORT = "summary_report"


@dataclass(frozen=True)
class ReportSection:
    section_id: str
    title: str
    content: str
    source_files: list[str] = field(default_factory=list)
    risk_level: str | None = None
    requires_review: bool = False


@dataclass(frozen=True)
class ReportMetadata:
    report_id: str
    run_id: str
    workflow_id: str | None
    skill_id: str | None
    generated_at: datetime
    report_type: ReportType
    status: str
    requires_review: bool
    source_manifest: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["generated_at"] = self.generated_at.isoformat()
        data["report_type"] = self.report_type.value
        return data


@dataclass(frozen=True)
class Report:
    metadata: ReportMetadata
    title: str
    sections: list[ReportSection]
    output_path: Path
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "title": self.title,
            "sections": [asdict(section) for section in self.sections],
            "output_path": str(self.output_path),
            "warnings": self.warnings,
        }
