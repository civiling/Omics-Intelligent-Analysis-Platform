import json

from visualization import ChartSpec, ChartType, RenderStatus, ResultReader
from visualization.renderers import JsonRenderer, PlotlyRenderer


def make_run(tmp_path):
    run_dir = tmp_path / "run_viz"
    (run_dir / "outputs" / "tables").mkdir(parents=True)
    (run_dir / "outputs" / "figures").mkdir(parents=True)
    (run_dir / "outputs" / "notes").mkdir(parents=True)
    (run_dir / "manifest.json").write_text('{"run_id": "run_viz", "workflow_id": "demo", "skill_id": "demo"}', encoding="utf-8")
    (run_dir / "outputs" / "tables" / "result.tsv").write_text("feature\tvalue\tpadj\nA\t1.0\t0.01\n", encoding="utf-8")
    (run_dir / "outputs" / "figures" / "existing_spec.json").write_text('{"chart": "placeholder"}', encoding="utf-8")
    (run_dir / "outputs" / "notes" / "method_note.md").write_text("method note", encoding="utf-8")
    (run_dir / "outputs" / "notes" / "risk_notes.md").write_text("risk note", encoding="utf-8")
    return run_dir


def spec():
    return ChartSpec(
        chart_id="bar_001",
        chart_type=ChartType.BARPLOT,
        title="Result barplot",
        description="A deterministic JSON chart.",
        data_source="outputs/tables/result.tsv",
        x="feature",
        y="value",
        label="feature",
        output_path="outputs/figures/bar_001.json",
    )


def test_json_renderer_generates_chart_json(tmp_path):
    run_dir = make_run(tmp_path)
    result = JsonRenderer().render(spec(), run_dir)

    assert result.status == RenderStatus.SUCCESS
    payload = json.loads(result.rendered_path.read_text(encoding="utf-8"))
    assert payload["chart_id"] == "bar_001"
    assert payload["data"][0]["feature"] == "A"


def test_plotly_renderer_gracefully_renders_or_degrades(tmp_path):
    run_dir = make_run(tmp_path)
    result = PlotlyRenderer().render(spec(), run_dir)

    assert result.status == RenderStatus.SUCCESS
    assert result.rendered_path.exists()


def test_result_reader_reads_run_outputs(tmp_path):
    run_dir = make_run(tmp_path)
    data = ResultReader().read_run(run_dir)

    assert data.manifest["run_id"] == "run_viz"
    assert "outputs/tables/result.tsv" in data.tables
    assert "outputs/figures/existing_spec.json" in data.figure_specs
    assert data.method_note == "method note"
    assert data.risk_notes == "risk note"
