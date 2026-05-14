import gzip
import json
from pathlib import Path

from workflows import WorkflowRunner, WorkflowStatus


def write_gzip(path: Path, text: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write(text)


def create_scrna_matrix_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "GSE183904_RAW"
    data_dir.mkdir()
    for sample_index in range(1, 5):
        gsm = f"GSM557346{5 + sample_index}"
        write_gzip(
            data_dir / f"{gsm}_sample{sample_index}.csv.gz",
            "\n".join(
                [
                    f",AAACCTGAGGCTACGA_{sample_index},AAACCTGAGGTTCCTA_{sample_index}",
                    "AL627309.1,0,0",
                    "MT-ND1,1,0",
                ]
            ),
        )
    return data_dir


def test_scrna_data_ingestion_workflow_runs_as_local_runtime(tmp_path):
    data_dir = create_scrna_matrix_dir(tmp_path)
    result = WorkflowRunner(runs_dir=tmp_path / "runs").run(
        "scrna.data_ingestion",
        {"matrix_directory": str(data_dir)},
        {
            "project_name": "GSE183904 demo",
            "organism": "human",
            "disease_context": "gastric cancer",
        },
    )

    assert result.status == WorkflowStatus.SUCCESS
    assert result.metrics["workflow_id"] == "scrna.data_ingestion"
    assert result.metrics["matrix_count"] == 4
    assert result.metrics["total_cells"] == 8
    assert "tables/expression_matrix_manifest.json" in result.output_files
    assert "tables/sample_metadata_template.csv" in result.output_files
    assert "reports/data_readiness_report.json" in result.output_files
    assert "platform_store/datasets.json" in result.output_files

    report_path = Path(result.output_files["reports/data_readiness_report.json"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["dataset"]["sample_count"] == 4
    assert report["dataset"]["metadata_status"] == "partial"


def test_scrna_metadata_design_workflow_imports_metadata_and_recommends_pairing(tmp_path):
    data_dir = create_scrna_matrix_dir(tmp_path)
    runner = WorkflowRunner(runs_dir=tmp_path / "runs")
    ingestion = runner.run(
        "scrna.data_ingestion",
        {"matrix_directory": str(data_dir)},
        {
            "project_name": "GSE183904 demo",
            "organism": "human",
        },
    )
    metadata_path = tmp_path / "metadata.csv"
    metadata_path.write_text(
        "\n".join(
            [
                "gsm,group,patient,batch",
                "GSM5573466,Normal,p1,b1",
                "GSM5573467,Tumor,p1,b1",
                "GSM5573468,Normal,p2,b2",
                "GSM5573469,Tumor,p2,b2",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.run(
        "scrna.metadata_design",
        {
            "platform_store": ingestion.metrics["platform_store"],
            "metadata_table": str(metadata_path),
        },
        {"dataset_id": ingestion.metrics["dataset_id"]},
    )

    assert result.status == WorkflowStatus.SUCCESS
    assert result.metrics["workflow_id"] == "scrna.metadata_design"
    assert result.metrics["matched_count"] == 4
    assert result.metrics["recommended_mode"] == "paired_pseudobulk_de"
    assert result.metrics["result_confidence"] == "formal_statistical"
    assert "reports/analysis_mode_recommendation.json" in result.output_files
    assert "reports/confidence_gate_result.json" in result.output_files
    assert "platform_store/sample_metadata.json" in result.output_files

    recommendation = json.loads(Path(result.output_files["reports/analysis_mode_recommendation.json"]).read_text(encoding="utf-8"))
    assert recommendation["recommended_mode"] == "paired_pseudobulk_de"


def test_scrna_qc_clustering_workflow_emits_qc_and_embedding_outputs(tmp_path):
    data_dir = create_scrna_matrix_dir(tmp_path)
    runner = WorkflowRunner(runs_dir=tmp_path / "runs")
    ingestion = runner.run(
        "scrna.data_ingestion",
        {"matrix_directory": str(data_dir)},
        {
            "project_name": "GSE183904 QC demo",
            "organism": "human",
        },
    )

    result = runner.run(
        "scrna.qc_clustering",
        {"platform_store": ingestion.metrics["platform_store"]},
        {
            "dataset_id": ingestion.metrics["dataset_id"],
            "min_genes": 1,
            "max_mito_pct": 100,
            "cluster_count": 2,
        },
    )

    assert result.status == WorkflowStatus.SUCCESS
    assert result.metrics["workflow_id"] == "scrna.qc_clustering"
    assert result.metrics["evaluated_cell_count"] == 8
    assert "tables/cell_qc_metrics.csv" in result.output_files
    assert "tables/umap_embedding.json" in result.output_files
    assert "figures/umap_plot_data.json" in result.output_files
    assert "reports/qc_clustering_report.json" in result.output_files

    report = json.loads(Path(result.output_files["reports/qc_clustering_report.json"]).read_text(encoding="utf-8"))
    assert report["filtering_summary"]["evaluated_cell_count"] == 8
    assert report["embedding"]["method"] == "qc_preview_embedding"
