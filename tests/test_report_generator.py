import json

from reports import ReportGenerator


def make_report_run(tmp_path, requires_review=True, include_evidence=False):
    run_dir = tmp_path / "run_report"
    (run_dir / "outputs" / "tables").mkdir(parents=True)
    (run_dir / "outputs" / "figures").mkdir(parents=True)
    (run_dir / "outputs" / "notes").mkdir(parents=True)
    manifest = {
        "run_id": "run_report",
        "workflow_id": "multiomics.correlation_network",
        "skill_id": "multiomics.correlation_network",
        "status": "success",
        "input_files": {"metadata": "metadata.tsv"},
        "parameters": {"sample_id_column": "sample_id"},
        "output_files": {"tables/feature_associations.tsv": "path"},
        "workflow_config": {"risk_level": "high", "requires_review": requires_review},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run_dir / "parameters.yaml").write_text("sample_id_column: sample_id\n", encoding="utf-8")
    (run_dir / "outputs" / "tables" / "feature_associations.tsv").write_text("a\tb\nx\ty\n", encoding="utf-8")
    (run_dir / "outputs" / "figures" / "network_plot_spec.json").write_text('{"chart": "network"}', encoding="utf-8")
    (run_dir / "outputs" / "notes" / "method_note.md").write_text("method note text", encoding="utf-8")
    (run_dir / "outputs" / "notes" / "risk_notes.md").write_text("risk note text", encoding="utf-8")
    if include_evidence:
        (run_dir / "outputs" / "notes" / "evidence_notes.md").write_text("evidence note text", encoding="utf-8")
    return run_dir


def test_report_generator_writes_markdown(tmp_path):
    run_dir = make_report_run(tmp_path, include_evidence=True)
    report = ReportGenerator().generate_markdown_report(run_dir)

    assert report.output_path.exists()
    text = report.output_path.read_text(encoding="utf-8")
    assert "# 多组学智能分析报告" in text
    assert "method note text" in text


def test_missing_evidence_generates_warning_and_placeholder_text(tmp_path):
    run_dir = make_report_run(tmp_path, include_evidence=False)
    report = ReportGenerator().generate_markdown_report(run_dir)

    text = report.output_path.read_text(encoding="utf-8")
    assert "本次运行未提供文献证据结果" in text
    assert any("evidence_notes.md" in warning for warning in report.warnings)


def test_high_risk_task_marks_requires_review(tmp_path):
    run_dir = make_report_run(tmp_path, requires_review=True)
    report = ReportGenerator().generate_markdown_report(run_dir)

    assert report.metadata.requires_review is True
    assert "需要专家复核" in report.output_path.read_text(encoding="utf-8")


def test_report_contains_eight_basic_sections(tmp_path):
    run_dir = make_report_run(tmp_path, include_evidence=True)
    report = ReportGenerator().generate_markdown_report(run_dir)

    assert len(report.sections) == 8
    text = report.output_path.read_text(encoding="utf-8")
    for heading in ("1. 数据与任务概况", "2. 方法学说明", "3. 主要结果", "4. 可视化结果", "5. 文献证据与解释", "6. 风险提示与解释限制", "7. 专家复核状态", "8. 附录"):
        assert heading in text
