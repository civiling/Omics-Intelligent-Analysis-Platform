from __future__ import annotations

import csv
import json
from pathlib import Path

from visualization.chart_validator import ChartValidator
from visualization.models import ChartSpec, RenderedChart, RenderStatus

from .base import BaseChartRenderer


class JsonRenderer(BaseChartRenderer):
    def render(self, spec: ChartSpec, run_dir: str | Path) -> RenderedChart:
        run_path = Path(run_dir).resolve()
        validation = ChartValidator().validate(spec, run_path)
        output_path = self._output_path(spec, run_path)
        if not validation.valid:
            return RenderedChart(
                chart_id=spec.chart_id,
                chart_type=spec.chart_type,
                title=spec.title,
                spec_path=None,
                rendered_path=None,
                data_source=spec.data_source,
                status=RenderStatus.FAILED,
                error_message="; ".join(validation.errors),
            )

        data = self._read_rows(run_path / spec.data_source)
        payload = {
            "chart_id": spec.chart_id,
            "chart_type": spec.chart_type.value,
            "title": spec.title,
            "description": spec.description,
            "data": data,
            "encoding": {
                "x": spec.x,
                "y": spec.y,
                "label": spec.label,
                "color_by": spec.color_by,
                "size_by": spec.size_by,
            },
            "filters": spec.filters,
            "thresholds": spec.thresholds,
            "annotations": spec.annotations,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return RenderedChart(
            chart_id=spec.chart_id,
            chart_type=spec.chart_type,
            title=spec.title,
            spec_path=None,
            rendered_path=output_path,
            data_source=spec.data_source,
            status=RenderStatus.SUCCESS,
        )

    def render_from_run(self, run_dir: str | Path) -> list[RenderedChart]:
        run_path = Path(run_dir).resolve()
        charts: list[RenderedChart] = []
        for spec_path in sorted((run_path / "outputs" / "figures").glob("*_spec.json")):
            try:
                spec = ChartSpec.from_mapping(json.loads(spec_path.read_text(encoding="utf-8")))
            except Exception:
                continue
            charts.append(self.render(spec, run_path))
        return charts

    def _output_path(self, spec: ChartSpec, run_path: Path) -> Path:
        if spec.output_path:
            return (run_path / spec.output_path).resolve()
        return run_path / "outputs" / "figures" / f"{spec.chart_id}.json"

    def _read_rows(self, path: Path) -> list[dict[str, str]]:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle, delimiter=delimiter))
