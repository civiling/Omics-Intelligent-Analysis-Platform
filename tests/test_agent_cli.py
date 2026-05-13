import json

from agents.cli import main


def test_cli_validate_reports_ok(capsys):
    exit_code = main(["validate", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["skill_registry_errors"] == []
    assert payload["workflow_errors"] == []


def test_cli_list_skills(capsys):
    exit_code = main(["list-skills"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "microbiome.differential_abundance" in captured.out


def test_cli_plan_outputs_agent_plan(capsys):
    exit_code = main(
        [
            "plan",
            "--json",
            "--task-id",
            "cli_plan_test",
            "--query",
            "microbiome differential abundance",
            "--domain",
            "microbiome",
            "--input",
            "feature_table=feature.tsv",
            "--input",
            "taxonomy_table=taxonomy.tsv",
            "--input",
            "metadata=metadata.tsv",
            "--param",
            "group_column=group",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["selected_skill_id"] == "microbiome.differential_abundance"
    assert payload["selected_workflow_id"] == "microbiome.differential_abundance"
    assert payload["parameters"]["group_column"] == "group"


def test_cli_run_executes_registered_workflow(tmp_path, capsys):
    exit_code = main(
        [
            "run",
            "--json",
            "--task-id",
            "cli_run_test",
            "--query",
            "microbiome differential abundance",
            "--domain",
            "microbiome",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--agent-logs-dir",
            str(tmp_path / "logs"),
            "--input",
            "feature_table=feature.tsv",
            "--input",
            "taxonomy_table=taxonomy.tsv",
            "--input",
            "metadata=metadata.tsv",
            "--param",
            "group_column=group",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["status"] == "success"
    assert payload["run_id"]
    assert (tmp_path / "runs" / payload["run_id"] / "agent_trace.json").exists()


def test_cli_run_missing_inputs_returns_needs_input(tmp_path, capsys):
    exit_code = main(
        [
            "run",
            "--json",
            "--task-id",
            "cli_needs_input_test",
            "--query",
            "microbiome differential abundance",
            "--domain",
            "microbiome",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--agent-logs-dir",
            str(tmp_path / "logs"),
            "--input",
            "feature_table=feature.tsv",
            "--param",
            "group_column=group",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 2
    assert payload["status"] == "needs_input"
    assert "taxonomy_table" in payload["error_message"]
    assert (tmp_path / "logs" / "agent_trace.jsonl").exists()
