from __future__ import annotations

import json
from pathlib import Path

from visualization.models import ChartSpec, ChartType, RenderedChart, RenderStatus

from .json_renderer import JsonRenderer


class PlotlyRenderer(JsonRenderer):
    SUPPORTED = {ChartType.VOLCANO, ChartType.BARPLOT, ChartType.BOXPLOT, ChartType.PCA, ChartType.TABLE}

    def render(self, spec: ChartSpec, run_dir: str | Path) -> RenderedChart:
        try:
            import plotly  # noqa: F401
        except ImportError:
            return JsonRenderer().render(spec, run_dir)

        if spec.chart_type not in self.SUPPORTED:
            return JsonRenderer().render(spec, run_dir)

        base = JsonRenderer().render(spec, run_dir)
        if base.status != RenderStatus.SUCCESS or base.rendered_path is None:
            return base

        payload = json.loads(base.rendered_path.read_text(encoding="utf-8"))
        rows = payload["data"]
        plotly_payload = {
            "chart_id": spec.chart_id,
            "chart_type": spec.chart_type.value,
            "title": spec.title,
            "data": [
                {
                    "type": self._plotly_trace_type(spec.chart_type),
                    "x": [row.get(spec.x) for row in rows] if spec.x else [],
                    "y": [row.get(spec.y) for row in rows] if spec.y else [],
                    "text": [row.get(spec.label) for row in rows] if spec.label else [],
                    "mode": "markers" if spec.chart_type in {ChartType.VOLCANO, ChartType.PCA} else None,
                }
            ],
            "layout": {
                "title": spec.title,
                "xaxis": {"title": spec.x},
                "yaxis": {"title": spec.y},
            },
            "thresholds": spec.thresholds,
            "annotations": spec.annotations,
        }
        base.rendered_path.write_text(json.dumps(plotly_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return base

    def _plotly_trace_type(self, chart_type: ChartType) -> str:
        if chart_type == ChartType.BARPLOT:
            return "bar"
        if chart_type == ChartType.BOXPLOT:
            return "box"
        if chart_type == ChartType.TABLE:
            return "table"
        return "scatter"
