from visualization import ChartSpec, ChartType, ChartValidator


def make_run(tmp_path):
    run_dir = tmp_path / "run_chart"
    table_dir = run_dir / "outputs" / "tables"
    figure_dir = run_dir / "outputs" / "figures"
    table_dir.mkdir(parents=True)
    figure_dir.mkdir(parents=True)
    (table_dir / "differential_taxa.tsv").write_text(
        "taxon\tlog2FoldChange\tpadj\tsignificance\nA\t1.2\t0.01\tyes\n",
        encoding="utf-8",
    )
    return run_dir


def valid_spec():
    return ChartSpec(
        chart_id="microbiome_volcano_001",
        chart_type=ChartType.VOLCANO,
        title="Differential abundance volcano plot",
        description="Volcano plot for differential taxa analysis.",
        data_source="outputs/tables/differential_taxa.tsv",
        x="log2FoldChange",
        y="padj",
        label="taxon",
        color_by="significance",
        thresholds={"padj": 0.05, "abs_log2fc": 1.0},
        filters={"padj_lt": 0.1},
        output_path="outputs/figures/microbiome_volcano.json",
    )


def test_valid_chart_spec_passes(tmp_path):
    result = ChartValidator().validate(valid_spec(), make_run(tmp_path))

    assert result.valid is True
    assert result.errors == []


def test_invalid_chart_type_reports_error(tmp_path):
    spec = valid_spec().to_dict()
    spec["chart_type"] = "unknown"

    result = ChartValidator().validate(spec, make_run(tmp_path))

    assert result.valid is False
    assert any("Invalid chart spec" in error for error in result.errors)


def test_missing_data_source_reports_error(tmp_path):
    spec = valid_spec()
    spec = ChartSpec(**{**spec.to_dict(), "chart_type": ChartType.VOLCANO, "data_source": "outputs/tables/missing.tsv"})

    result = ChartValidator().validate(spec, make_run(tmp_path))

    assert result.valid is False
    assert any("data_source does not exist" in error for error in result.errors)


def test_missing_xy_fields_report_error(tmp_path):
    spec = valid_spec()
    spec = ChartSpec(**{**spec.to_dict(), "chart_type": ChartType.VOLCANO, "x": "missing_x", "y": "missing_y"})

    result = ChartValidator().validate(spec, make_run(tmp_path))

    assert result.valid is False
    assert any("missing_x" in error for error in result.errors)
    assert any("missing_y" in error for error in result.errors)


def test_output_path_escape_reports_error(tmp_path):
    spec = valid_spec()
    spec = ChartSpec(**{**spec.to_dict(), "chart_type": ChartType.VOLCANO, "output_path": "../outside.json"})

    result = ChartValidator().validate(spec, make_run(tmp_path))

    assert result.valid is False
    assert any("output_path must stay inside outputs/figures" in error for error in result.errors)
