from reports import ReportGenerator
from visualization import ChartSpec, ChartType, RenderStatus
from visualization.renderers import JsonRenderer
from workflows import WorkflowRunner


def test_visualization_and_report_from_placeholder_workflow(tmp_path):
    result = WorkflowRunner(runs_dir=tmp_path / "runs").run(
        "microbiome.differential_abundance",
        {
            "feature_table": "feature.tsv",
            "taxonomy_table": "taxonomy.tsv",
            "metadata": "metadata.tsv",
        },
        {"group_column": "group"},
    )
    run_dir = result.manifest_path.parent
    spec = ChartSpec(
        chart_id="microbiome_volcano_rendered",
        chart_type=ChartType.VOLCANO,
        title="Differential taxa volcano",
        description="Rendered from placeholder differential taxa output.",
        data_source="outputs/tables/differential_taxa.tsv",
        x="log_fold_change",
        y="adjusted_p_value",
        label="taxon",
        output_path="outputs/figures/microbiome_volcano_rendered.json",
    )

    chart = JsonRenderer().render(spec, run_dir)
    report = ReportGenerator().generate_markdown_report(run_dir)
    text = report.output_path.read_text(encoding="utf-8")

    assert chart.status == RenderStatus.SUCCESS
    assert chart.rendered_path.exists()
    assert report.output_path.exists()
    assert "tables/differential_taxa.tsv" in text
    assert "Placeholder differential abundance result" in text
    assert "Relative abundance changes" in text
