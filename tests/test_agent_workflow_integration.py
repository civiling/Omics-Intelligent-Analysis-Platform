import json

from agents.context import AgentContext
from agents.models import AgentStatus, AgentTask
from agents.supervisor import SupervisorAgent
from agents.tools import WorkflowTool
from workflows import WorkflowRunner


def make_agent(tmp_path):
    return SupervisorAgent(
        context=AgentContext(
            workflow_runner=WorkflowRunner(runs_dir=tmp_path / "runs"),
            agent_logs_dir=tmp_path / "agent_logs",
        )
    )


def test_agent_result_contains_workflow_run_identifiers(tmp_path):
    task = AgentTask(
        task_id="rna_agent_run",
        user_query="RNA-seq count matrix 差异基因分析",
        available_inputs={"count_matrix": "counts.tsv", "gene_annotation": "genes.tsv", "metadata": "metadata.tsv"},
        domain="transcriptomics",
        constraints={"design_formula": "~ condition", "contrast": "case_vs_control"},
    )

    result = make_agent(tmp_path).run(task)

    assert result.status == AgentStatus.SUCCESS
    assert result.selected_skill_id == "transcriptomics.differential_expression"
    assert result.selected_workflow_id == "transcriptomics.differential_expression"
    assert result.run_id is not None


def test_missing_required_workflow_parameter_returns_needs_input(tmp_path):
    task = AgentTask(
        task_id="missing_parameter",
        user_query="请做差异菌群分析",
        available_inputs={"feature_table": "feature.tsv", "taxonomy_table": "taxonomy.tsv", "metadata": "metadata.tsv"},
        domain="microbiome",
        constraints={},
    )

    result = make_agent(tmp_path).run(task)

    assert result.status == AgentStatus.NEEDS_INPUT
    assert "group_column" in result.error_message


def test_agent_does_not_allow_arbitrary_script_execution_from_constraints(tmp_path):
    outside_script = tmp_path / "outside.py"
    outside_script.write_text("raise SystemExit('should not run')\n", encoding="utf-8")
    task = AgentTask(
        task_id="no_arbitrary_script",
        user_query="请做差异菌群分析",
        available_inputs={"feature_table": "feature.tsv", "taxonomy_table": "taxonomy.tsv", "metadata": "metadata.tsv"},
        domain="microbiome",
        constraints={"group_column": "group", "script_path": str(outside_script)},
    )

    result = make_agent(tmp_path).run(task)

    assert result.status == AgentStatus.SUCCESS
    assert result.selected_workflow_id == "microbiome.differential_abundance"
    assert result.run_id is not None
    manifest = json.loads((tmp_path / "runs" / result.run_id / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["workflow_config"]["script_path"] != str(outside_script)


def test_workflow_tool_does_not_expose_arbitrary_command_runner():
    tool = WorkflowTool()

    assert not hasattr(tool, "run_command")
    assert not hasattr(tool, "run_script")


def test_agent_trace_json_is_written_for_successful_workflow(tmp_path):
    task = AgentTask(
        task_id="evidence_agent_run",
        user_query="生成文献证据和报告段落",
        available_inputs={
            "analysis_result_table": "results.tsv",
            "method_note": "method.md",
            "risk_notes": "risk.md",
        },
        domain="reporting",
    )

    result = make_agent(tmp_path).run(task)

    trace_path = tmp_path / "runs" / result.run_id / "agent_trace.json"
    assert trace_path.exists()
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["run_id"] == result.run_id
    assert trace["status"] == "success"
