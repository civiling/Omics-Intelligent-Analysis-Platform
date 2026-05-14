import json
from pathlib import Path

import pytest

from skill_registry.loader import _load_yaml_file
from workflows import (
    ExecutorType,
    WorkflowConfig,
    WorkflowNotFoundError,
    WorkflowRegistry,
    WorkflowRunner,
    WorkflowStatus,
    WorkflowValidationError,
    WorkflowValidator,
)
from workflows.executors import LocalExecutor, PlaceholderExecutor


EXPECTED_WORKFLOWS = {
    "scrna.data_ingestion",
    "scrna.metadata_design",
    "scrna.qc_clustering",
    "microbiome.read_qc",
    "microbiome.differential_abundance",
    "transcriptomics.differential_expression",
    "metabolomics.differential_metabolites",
    "multiomics.correlation_network",
    "reporting.evidence_report_generation",
}


def input_files_for(workflow_id):
    workflow = WorkflowRegistry().get(workflow_id)
    return {input_type: f"/tmp/{input_type}.tsv" for input_type in workflow.input_types}


def required_parameters_for(workflow_id):
    workflow = WorkflowRegistry().get(workflow_id)
    return {parameter: f"test_{parameter}" for parameter in workflow.required_parameters}


def test_all_workflow_configs_can_be_loaded():
    workflows = WorkflowRegistry().load_all()

    assert set(workflows) == EXPECTED_WORKFLOWS


def test_six_workflows_exist():
    runner = WorkflowRunner()

    assert {workflow.id for workflow in runner.list_workflows()} == EXPECTED_WORKFLOWS


@pytest.mark.parametrize("workflow_id", sorted(EXPECTED_WORKFLOWS))
def test_each_workflow_can_create_run_directory(tmp_path, workflow_id):
    runner = WorkflowRunner(runs_dir=tmp_path)
    run_dir = runner.create_run_directory(workflow_id)

    assert run_dir.exists()
    assert (run_dir / "logs").exists()
    assert (run_dir / "outputs" / "tables").exists()
    assert (run_dir / "outputs" / "figures").exists()
    assert (run_dir / "outputs" / "notes").exists()


def test_placeholder_executor_generates_standard_outputs(tmp_path):
    config = WorkflowRegistry().get("microbiome.differential_abundance")
    run_dir = tmp_path / "run_placeholder"
    (run_dir / "outputs" / "tables").mkdir(parents=True)
    (run_dir / "outputs" / "figures").mkdir(parents=True)
    (run_dir / "outputs" / "notes").mkdir(parents=True)

    result = PlaceholderExecutor().execute(
        config,
        run_dir,
        input_files_for(config.id),
        {"group_column": "condition"},
    )

    assert result.status == WorkflowStatus.SUCCESS
    assert (run_dir / "outputs" / "tables" / "differential_taxa.tsv").exists()
    assert (run_dir / "outputs" / "figures" / "volcano_plot_spec.json").exists()
    assert (run_dir / "outputs" / "notes" / "method_note.md").exists()
    assert (run_dir / "outputs" / "notes" / "risk_notes.md").exists()


def test_workflow_runner_run_returns_success_result(tmp_path):
    result = WorkflowRunner(runs_dir=tmp_path).run(
        "microbiome.differential_abundance",
        input_files_for("microbiome.differential_abundance"),
        {"group_column": "condition"},
    )

    assert result.status == WorkflowStatus.SUCCESS
    assert result.manifest_path is not None
    assert result.manifest_path.exists()


def test_manifest_json_is_written(tmp_path):
    result = WorkflowRunner(runs_dir=tmp_path).run(
        "transcriptomics.differential_expression",
        input_files_for("transcriptomics.differential_expression"),
        {"design_formula": "~ condition", "contrast": "case_vs_control"},
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == result.run_id
    assert manifest["workflow_id"] == "transcriptomics.differential_expression"
    assert manifest["skill_id"] == "transcriptomics.differential_expression"
    assert manifest["status"] == "success"
    assert manifest["executor_type"] == "placeholder"
    assert "workflow_config" in manifest


def test_parameters_yaml_is_written(tmp_path):
    result = WorkflowRunner(runs_dir=tmp_path).run(
        "metabolomics.differential_metabolites",
        input_files_for("metabolomics.differential_metabolites"),
        {"group_column": "condition"},
    )

    parameters_path = result.manifest_path.parent / "parameters.yaml"
    parameters = _load_yaml_file(parameters_path)
    assert parameters["group_column"] == "condition"
    assert parameters["fdr_threshold"] == 0.05


def test_missing_required_parameter_has_clear_error(tmp_path):
    with pytest.raises(WorkflowValidationError, match="missing required parameters: group_column"):
        WorkflowRunner(runs_dir=tmp_path).run(
            "microbiome.differential_abundance",
            input_files_for("microbiome.differential_abundance"),
            {},
        )


def test_non_registered_workflow_cannot_run(tmp_path):
    with pytest.raises(WorkflowNotFoundError, match="not registered"):
        WorkflowRunner(runs_dir=tmp_path).run("unknown.workflow", {}, {})


def test_validator_identifies_illegal_executor_type(tmp_path):
    config_path = tmp_path / "bad_executor.yaml"
    config_path.write_text(
        """
id: bad.executor
name: Bad executor workflow
domain: microbiome
version: 0.1.0
description: Invalid executor test.
skill_id: microbiome.read_qc
executor_type: shell
script_path: workflows/scripts/microbiome/read_qc_placeholder.py
input_types:
  - reads
output_types:
  - qc_summary
default_parameters: {}
required_parameters: []
timeout_seconds: 10
risk_level: low
requires_review: false
""".strip(),
        encoding="utf-8",
    )

    errors = WorkflowValidator(configs_dir=tmp_path).validate()

    assert any("executor_type must be one of placeholder, local" in error for error in errors)


def test_local_executor_rejects_script_outside_registered_scripts(tmp_path):
    outside_script = tmp_path / "outside.py"
    outside_script.write_text("print('should not run')\n", encoding="utf-8")
    run_dir = tmp_path / "run_local"
    (run_dir / "outputs").mkdir(parents=True)
    (run_dir / "inputs.json").write_text("{}", encoding="utf-8")
    (run_dir / "parameters.yaml").write_text("{}", encoding="utf-8")
    config = WorkflowConfig(
        id="test.local",
        name="Test local",
        domain="test",
        version="0.1.0",
        description="Test local executor guard.",
        skill_id="microbiome.read_qc",
        executor_type=ExecutorType.LOCAL,
        script_path=outside_script,
        input_types=[],
        output_types=[],
        default_parameters={},
        required_parameters=[],
        timeout_seconds=10,
        risk_level="low",
        requires_review=False,
    )

    result = LocalExecutor().execute(config, run_dir, {}, {})

    assert result.status == WorkflowStatus.FAILED
    assert "Refusing to execute unregistered script outside" in result.error_message


def test_local_executor_can_run_registered_placeholder_script(tmp_path):
    base_config = WorkflowRegistry().get("microbiome.read_qc")
    run_dir = tmp_path / "run_local_success"
    (run_dir / "outputs").mkdir(parents=True)
    (run_dir / "inputs.json").write_text("{}", encoding="utf-8")
    (run_dir / "parameters.yaml").write_text("{}", encoding="utf-8")
    config = WorkflowConfig(
        id=base_config.id,
        name=base_config.name,
        domain=base_config.domain,
        version=base_config.version,
        description=base_config.description,
        skill_id=base_config.skill_id,
        executor_type=ExecutorType.LOCAL,
        script_path=base_config.script_path,
        input_types=base_config.input_types,
        output_types=base_config.output_types,
        default_parameters=base_config.default_parameters,
        required_parameters=base_config.required_parameters,
        timeout_seconds=base_config.timeout_seconds,
        risk_level=base_config.risk_level,
        requires_review=base_config.requires_review,
    )

    result = LocalExecutor().execute(config, run_dir, {}, {})

    assert result.status == WorkflowStatus.SUCCESS
    assert (run_dir / "outputs" / "tables" / "qc_summary.tsv").exists()
    assert "tables/qc_summary.tsv" in result.output_files
