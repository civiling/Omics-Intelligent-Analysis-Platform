from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ChartType(str, Enum):
    VOLCANO = "volcano"
    HEATMAP = "heatmap"
    BARPLOT = "barplot"
    BOXPLOT = "boxplot"
    PCA = "pca"
    NETWORK = "network"
    TABLE = "table"
    EVIDENCE_TABLE = "evidence_table"


class RenderStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class ChartSpec:
    chart_id: str
    chart_type: ChartType
    title: str
    description: str
    data_source: str
    x: str | None = None
    y: str | None = None
    label: str | None = None
    color_by: str | None = None
    size_by: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    thresholds: dict[str, Any] = field(default_factory=dict)
    annotations: list[dict[str, Any]] = field(default_factory=list)
    output_path: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ChartSpec":
        return cls(
            chart_id=str(data["chart_id"]),
            chart_type=ChartType(str(data["chart_type"])),
            title=str(data.get("title", data["chart_id"])),
            description=str(data.get("description", "")),
            data_source=str(data["data_source"]),
            x=data.get("x"),
            y=data.get("y"),
            label=data.get("label"),
            color_by=data.get("color_by"),
            size_by=data.get("size_by"),
            filters=dict(data.get("filters", {})),
            thresholds=dict(data.get("thresholds", {})),
            annotations=list(data.get("annotations", [])),
            output_path=data.get("output_path"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["chart_type"] = self.chart_type.value
        return data


@dataclass(frozen=True)
class ChartValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RenderedChart:
    chart_id: str
    chart_type: ChartType
    title: str
    spec_path: Path | None
    rendered_path: Path | None
    data_source: str
    status: RenderStatus
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_id": self.chart_id,
            "chart_type": self.chart_type.value,
            "title": self.title,
            "spec_path": str(self.spec_path) if self.spec_path else None,
            "rendered_path": str(self.rendered_path) if self.rendered_path else None,
            "data_source": self.data_source,
            "status": self.status.value,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class RunVisualizationData:
    run_dir: Path
    manifest: dict[str, Any]
    tables: dict[str, Path]
    figure_specs: dict[str, Path]
    method_note: str
    risk_notes: str
    evidence_notes: str = ""
    report_draft: str = ""
