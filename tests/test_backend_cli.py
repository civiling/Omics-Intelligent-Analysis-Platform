import gzip
import json
from pathlib import Path

from backend.cli import main


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


def test_backend_cli_ingest_directory_outputs_dataset_payload(tmp_path, capsys):
    data_dir = create_matrix_dir(tmp_path)
    store_dir = tmp_path / "store"

    exit_code = main(
        [
            "ingest-directory",
            "--json",
            "--store-dir",
            str(store_dir),
            "--data-dir",
            str(data_dir),
            "--project-name",
            "GSE183904 demo",
            "--organism",
            "human",
            "--disease-context",
            "gastric cancer",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["dataset"]["file_count"] == 4
    assert payload["matrix_count"] == 4
    assert payload["total_genes"] == 2
    assert payload["total_cells"] == 8
    assert payload["dataset"]["metadata_status"] == "partial"


def test_backend_cli_metadata_template_import_and_evaluate_design(tmp_path, capsys):
    data_dir = create_matrix_dir(tmp_path)
    store_dir = tmp_path / "store"
    main(
        [
            "ingest-directory",
            "--json",
            "--store-dir",
            str(store_dir),
            "--data-dir",
            str(data_dir),
            "--project-name",
            "GSE183904 demo",
            "--organism",
            "human",
        ]
    )
    ingest_payload = json.loads(capsys.readouterr().out)
    dataset_id = ingest_payload["dataset"]["dataset_id"]
    template_path = tmp_path / "metadata_template.csv"

    template_exit_code = main(
        [
            "export-metadata-template",
            "--json",
            "--store-dir",
            str(store_dir),
            "--dataset-id",
            dataset_id,
            "--output",
            str(template_path),
        ]
    )
    template_payload = json.loads(capsys.readouterr().out)
    assert template_exit_code == 0
    assert Path(template_payload["output_path"]).exists()

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

    import_exit_code = main(
        [
            "import-metadata",
            "--json",
            "--store-dir",
            str(store_dir),
            "--dataset-id",
            dataset_id,
            "--metadata",
            str(metadata_path),
            "--evaluate",
        ]
    )
    import_payload = json.loads(capsys.readouterr().out)

    assert import_exit_code == 0
    assert import_payload["updated_count"] == 4
    assert import_payload["missing_samples"] == []
    assert import_payload["design"]["recommendation"]["recommended_mode"] == "paired_pseudobulk_de"
    assert import_payload["design"]["recommendation"]["result_confidence"] == "formal_statistical"


def test_backend_cli_evaluate_design_without_metadata_reports_missing_condition(tmp_path, capsys):
    data_dir = create_matrix_dir(tmp_path)
    store_dir = tmp_path / "store"
    main(
        [
            "ingest-directory",
            "--json",
            "--store-dir",
            str(store_dir),
            "--data-dir",
            str(data_dir),
            "--project-name",
            "GSE183904 demo",
            "--organism",
            "human",
        ]
    )
    dataset_id = json.loads(capsys.readouterr().out)["dataset"]["dataset_id"]

    exit_code = main(
        [
            "evaluate-design",
            "--json",
            "--store-dir",
            str(store_dir),
            "--dataset-id",
            dataset_id,
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["recommendation"]["recommended_mode"] == "multi_sample_integration"
    assert "condition" in payload["recommendation"]["missing_information"]
