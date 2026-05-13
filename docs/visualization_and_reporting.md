# Visualization And Reporting

The visualization and reporting layer turns deterministic Workflow Runtime outputs into controlled chart JSON and Markdown reports.

It reads existing run directories. It does not run bioinformatics workflows, execute arbitrary code, or ask an LLM to write plotting scripts.

## Responsibilities

- Validate controlled `chart_spec` JSON.
- Render fixed JSON or Plotly-compatible chart artifacts.
- Read `manifest.json`, `parameters.yaml`, tables, figure specs, notes, and agent trace files.
- Generate Markdown reports with source references, risk notes, and expert review status.

## Why LLMs Cannot Execute Chart Code

Scientific reports must be auditable and reproducible. Letting an LLM generate and execute Python, R, or JavaScript plotting code would bypass validators, source tracking, and workflow provenance. A future LLM may draft chart specs or interpretation text, but rendering must still use registered chart templates and backend renderers.

## Chart Spec Format

```json
{
  "chart_id": "microbiome_volcano_001",
  "chart_type": "volcano",
  "title": "Differential abundance volcano plot",
  "description": "Volcano plot for differential taxa analysis.",
  "data_source": "outputs/tables/differential_taxa.tsv",
  "x": "log_fold_change",
  "y": "adjusted_p_value",
  "label": "taxon",
  "color_by": "significance",
  "thresholds": {
    "padj": 0.05,
    "abs_log2fc": 1.0
  },
  "filters": {
    "padj_lt": 0.1
  },
  "annotations": [],
  "output_path": "outputs/figures/microbiome_volcano.json"
}
```

Allowed chart types are `volcano`, `heatmap`, `barplot`, `boxplot`, `pca`, `network`, `table`, and `evidence_table`.

## Add A Chart Template

1. Add a YAML file under `visualization/templates/`.
2. Declare the chart type and required fields.
3. Add validator rules only if the chart needs stricter checks.
4. Add renderer support without introducing arbitrary code execution.

## Render Chart JSON

```python
from visualization import ChartSpec, ChartType
from visualization.renderers.json_renderer import JsonRenderer

spec = ChartSpec(
    chart_id="demo_chart",
    chart_type=ChartType.BARPLOT,
    title="Demo chart",
    description="Controlled chart JSON.",
    data_source="outputs/tables/result.tsv",
    x="feature",
    y="value",
    output_path="outputs/figures/demo_chart.json",
)

chart = JsonRenderer().render(spec, "runs/run_demo_001")
print(chart.rendered_path)
```

`PlotlyRenderer` writes Plotly-compatible JSON when Plotly is available and gracefully falls back to `JsonRenderer` otherwise.

## Generate A Report From run_dir

```python
from reports.generator import ReportGenerator

report = ReportGenerator().generate_markdown_report(
    run_dir="runs/run_demo_001",
    report_type="expert_report",
)
print(report.output_path)
```

## Report Structure

The generated Markdown report contains:

1. 数据与任务概况
2. 方法学说明
3. 主要结果
4. 可视化结果
5. 文献证据与解释
6. 风险提示与解释限制
7. 专家复核状态
8. 附录

Missing evidence or notes are explicitly marked as missing or pending. The report does not invent missing findings.

## Risk And Expert Review

Risk level and review flags are read from `manifest.json`, workflow config metadata, and `agent_trace.json` when present. If `requires_review=true`, the report states that expert review is required.

## Future Exports

The current exporter supports Markdown and JSON metadata. DOCX, PDF, and HTML can be added later as optional exporters without changing the report data model.

## Relationship To Other Layers

- Skill Registry defines method rules, risks, and review expectations.
- Workflow Runtime produces the run directory, manifest, outputs, and notes.
- Agent Orchestration may produce `agent_trace.json` with selected skill, workflow, risk, and next steps.
- Visualization and Reporting read these artifacts and produce controlled display/report outputs.
