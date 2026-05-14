import gzip
import json
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api import create_app


def write_gzip(path: Path, text: str) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write(text)


def create_matrix_dir(tmp_path: Path) -> Path:
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


def test_health_endpoint():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ai_chat_requires_server_side_key(monkeypatch):
    monkeypatch.delenv("OMICS_LLM_API_KEY", raising=False)
    client = TestClient(create_app())

    response = client.post("/ai/chat", json={"question": "当前数据是否可靠？", "context": {}})

    assert response.status_code == 503
    assert "OMICS_LLM_API_KEY" in response.json()["detail"]


def test_scrna_fastapi_ingest_metadata_and_evaluate_design(tmp_path):
    client = TestClient(create_app())
    data_dir = create_matrix_dir(tmp_path)
    runs_dir = tmp_path / "runs"

    ingest_response = client.post(
        "/scrna/ingest-directory",
        json={
            "matrix_directory": str(data_dir),
            "project_name": "GSE183904 API demo",
            "organism": "human",
            "disease_context": "gastric cancer",
            "runs_dir": str(runs_dir),
        },
    )

    assert ingest_response.status_code == 200
    ingest_payload = ingest_response.json()
    assert ingest_payload["status"] == "success"
    assert ingest_payload["metrics"]["matrix_count"] == 4
    assert ingest_payload["metrics"]["total_cells"] == 8

    platform_store = ingest_payload["metrics"]["platform_store"]
    dataset_id = ingest_payload["metrics"]["dataset_id"]
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

    metadata_response = client.post(
        "/scrna/metadata-design",
        json={
            "platform_store": platform_store,
            "metadata_table": str(metadata_path),
            "dataset_id": dataset_id,
            "runs_dir": str(runs_dir),
        },
    )

    assert metadata_response.status_code == 200
    metadata_payload = metadata_response.json()
    assert metadata_payload["status"] == "success"
    assert metadata_payload["metrics"]["recommended_mode"] == "paired_pseudobulk_de"
    assert metadata_payload["metrics"]["result_confidence"] == "formal_statistical"

    recommendation_path = Path(metadata_payload["output_files"]["reports/analysis_mode_recommendation.json"])
    recommendation = json.loads(recommendation_path.read_text(encoding="utf-8"))
    assert recommendation["recommended_mode"] == "paired_pseudobulk_de"

    evaluate_response = client.post(
        "/scrna/evaluate-design",
        json={
            "platform_store": metadata_payload["metrics"]["platform_store"],
            "dataset_id": dataset_id,
            "persist": False,
        },
    )

    assert evaluate_response.status_code == 200
    evaluate_payload = evaluate_response.json()
    assert evaluate_payload["summary"]["condition_counts"] == {"Normal": 2, "Tumor": 2}
    assert evaluate_payload["recommendation"]["recommended_mode"] == "paired_pseudobulk_de"


def test_fastapi_platform_and_workflow_run_query_endpoints(tmp_path):
    client = TestClient(create_app())
    data_dir = create_matrix_dir(tmp_path)
    runs_dir = tmp_path / "runs"

    ingest_payload = client.post(
        "/scrna/ingest-directory",
        json={
            "matrix_directory": str(data_dir),
            "project_name": "GSE183904 query demo",
            "organism": "human",
            "runs_dir": str(runs_dir),
        },
    ).json()
    store_dir = ingest_payload["metrics"]["platform_store"]
    dataset_id = ingest_payload["metrics"]["dataset_id"]
    run_id = ingest_payload["run_id"]

    projects = client.get("/platform/projects", params={"store_dir": store_dir})
    datasets = client.get("/platform/datasets", params={"store_dir": store_dir})
    dataset = client.get(f"/platform/datasets/{dataset_id}", params={"store_dir": store_dir})
    matrices = client.get(f"/platform/datasets/{dataset_id}/matrices", params={"store_dir": store_dir})
    sample_metadata = client.get(f"/platform/datasets/{dataset_id}/sample-metadata", params={"store_dir": store_dir})

    assert projects.status_code == 200
    assert datasets.status_code == 200
    assert dataset.json()["dataset_id"] == dataset_id
    assert len(matrices.json()) == 4
    assert len(sample_metadata.json()) == 4

    runs = client.get("/workflow-runs", params={"runs_dir": str(runs_dir)})
    run = client.get(f"/workflow-runs/{run_id}", params={"runs_dir": str(runs_dir)})
    outputs = client.get(f"/workflow-runs/{run_id}/outputs", params={"runs_dir": str(runs_dir)})
    readiness = client.get(
        f"/workflow-runs/{run_id}/outputs/reports/data_readiness_report.json",
        params={"runs_dir": str(runs_dir)},
    )

    assert runs.status_code == 200
    assert any(item["run_id"] == run_id for item in runs.json())
    assert run.json()["run_id"] == run_id
    assert "reports/data_readiness_report.json" in outputs.json()
    assert readiness.json()["dataset"]["dataset_id"] == dataset_id


def test_fastapi_sample_metadata_online_update_recomputes_design(tmp_path):
    client = TestClient(create_app())
    data_dir = create_matrix_dir(tmp_path)
    ingest_payload = client.post(
        "/scrna/ingest-directory",
        json={
            "matrix_directory": str(data_dir),
            "project_name": "GSE183904 edit demo",
            "organism": "human",
            "runs_dir": str(tmp_path / "runs"),
        },
    ).json()
    store_dir = ingest_payload["metrics"]["platform_store"]
    dataset_id = ingest_payload["metrics"]["dataset_id"]

    response = client.patch(
        f"/platform/datasets/{dataset_id}/sample-metadata",
        params={"store_dir": store_dir},
        json={
            "updates_by_sample_id": {
                "GSM5573466_sample1": {"condition": "Normal", "patient_id": "p1", "batch": "b1"},
                "GSM5573467_sample2": {"condition": "Tumor", "patient_id": "p1", "batch": "b1"},
                "GSM5573468_sample3": {"condition": "Normal", "patient_id": "p2", "batch": "b2"},
                "GSM5573469_sample4": {"condition": "Tumor", "patient_id": "p2", "batch": "b2"},
            },
            "evaluate": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["updated_rows"]) == 4
    assert payload["design"]["recommendation"]["recommended_mode"] == "paired_pseudobulk_de"

    metadata = client.get(f"/platform/datasets/{dataset_id}/sample-metadata", params={"store_dir": store_dir}).json()
    assert all(row["confirmation_status"] == "confirmed" for row in metadata)


def test_fastapi_qc_clustering_endpoint_runs_workflow(tmp_path):
    client = TestClient(create_app())
    data_dir = create_matrix_dir(tmp_path)
    runs_dir = tmp_path / "runs"
    ingest_payload = client.post(
        "/scrna/ingest-directory",
        json={
            "matrix_directory": str(data_dir),
            "project_name": "GSE183904 QC API demo",
            "organism": "human",
            "runs_dir": str(runs_dir),
        },
    ).json()

    response = client.post(
        "/scrna/qc-clustering",
        json={
            "platform_store": ingest_payload["metrics"]["platform_store"],
            "dataset_id": ingest_payload["metrics"]["dataset_id"],
            "min_genes": 1,
            "max_mito_pct": 100,
            "cluster_count": 2,
            "runs_dir": str(runs_dir),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["metrics"]["workflow_id"] == "scrna.qc_clustering"
    assert payload["metrics"]["evaluated_cell_count"] == 8
    assert "figures/umap_plot_data.json" in payload["output_files"]


def test_fastapi_upload_and_ingest_endpoint(tmp_path):
    client = TestClient(create_app())
    upload_dir = tmp_path / "uploads"
    runs_dir = tmp_path / "runs"

    files = []
    for index in range(1, 3):
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as handle:
            handle.write(
                "\n".join(
                    [
                        f",AAACCTGAGGCTACGA_{index},AAACCTGAGGTTCCTA_{index}",
                        "AL627309.1,0,0",
                        "MT-ND1,1,0",
                    ]
                ).encode("utf-8")
            )
        files.append(
            (
                "files",
                (
                    f"GSM557346{5 + index}_sample{index}.csv.gz",
                    buffer.getvalue(),
                    "application/gzip",
                ),
            )
        )

    response = client.post(
        "/scrna/upload-and-ingest",
        data={
            "project_name": "Uploaded GSE183904 demo",
            "organism": "human",
            "upload_dir": str(upload_dir),
            "runs_dir": str(runs_dir),
        },
        files=files,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["metrics"]["matrix_count"] == 2
    assert payload["metrics"]["total_cells"] == 4
    assert len(list(upload_dir.glob("*.csv.gz"))) == 2
