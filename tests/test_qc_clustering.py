import gzip
from pathlib import Path

from backend.services import DataIngestionService, PlatformObjectService, QcClusteringService, QcParameters
from backend.storage import Organism, PlatformRepository


def write_gzip(path: Path, text: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write(text)


def test_qc_clustering_service_computes_cell_metrics_and_embedding(tmp_path):
    data_dir = tmp_path / "matrix"
    data_dir.mkdir()
    write_gzip(
        data_dir / "GSM1_sample1.csv.gz",
        "\n".join(
            [
                ",cell_a,cell_b,cell_c",
                "GeneA,10,0,2",
                "GeneB,2,0,0",
                "MT-ND1,1,5,30",
            ]
        ),
    )
    repository = PlatformRepository(tmp_path / "store")
    platform_service = PlatformObjectService(repository)
    ingestion = DataIngestionService(platform_service).ingest_directory(
        data_dir,
        project_name="QC demo",
        organism=Organism.HUMAN,
    )

    result = QcClusteringService(repository).run(
        ingestion.dataset.dataset_id,
        QcParameters(min_genes=2, min_counts=1, max_mito_pct=50, cluster_count=3),
    )

    assert result.filtering_summary["evaluated_cell_count"] == 3
    assert result.filtering_summary["passed_cell_count"] == 1
    assert result.filtering_summary["failure_reasons"]["high_mitochondrial_pct"] == 2
    assert len(result.embedding) == 3
    assert {point.cluster_id for point in result.embedding}
    assert result.sample_summary[0]["sample_id"] == "GSM1_sample1"
