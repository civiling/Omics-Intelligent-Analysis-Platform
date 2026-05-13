import json

from agents.context import AgentContext
from agents.models import AgentStatus, AgentTask
from agents.supervisor import SupervisorAgent
from workflows import WorkflowRunner


def make_agent(tmp_path):
    return SupervisorAgent(
        context=AgentContext(
            workflow_runner=WorkflowRunner(runs_dir=tmp_path / "runs"),
            agent_logs_dir=tmp_path / "agent_logs",
        )
    )


def test_supervisor_plan_generates_agent_plan(tmp_path):
    task = AgentTask(
        task_id="plan_microbiome",
        user_query="请对菌群 feature table 做差异菌群分析",
        available_inputs={"feature_table": "feature.tsv", "taxonomy_table": "taxonomy.tsv", "metadata": "metadata.tsv"},
        domain="microbiome",
        constraints={"group_column": "group"},
    )

    plan = make_agent(tmp_path).plan(task)

    assert plan.selected_skill_id == "microbiome.differential_abundance"
    assert plan.selected_workflow_id == "microbiome.differential_abundance"
    assert plan.risk_level == "medium"
    assert plan.requires_review is True


def test_supervisor_returns_needs_input_when_inputs_missing(tmp_path):
    task = AgentTask(
        task_id="missing_inputs",
        user_query="请做差异菌群分析",
        available_inputs={"feature_table": "feature.tsv"},
        domain="microbiome",
        constraints={"group_column": "group"},
    )

    result = make_agent(tmp_path).run(task)

    assert result.status == AgentStatus.NEEDS_INPUT
    assert result.run_id is None
    assert "taxonomy_table" in result.error_message
    assert (tmp_path / "agent_logs" / "agent_trace.jsonl").exists()


def test_supervisor_runs_workflow_when_inputs_complete(tmp_path):
    task = AgentTask(
        task_id="run_microbiome",
        user_query="请对这个菌群 feature table 做差异菌群分析",
        available_inputs={"feature_table": "feature.tsv", "taxonomy_table": "taxonomy.tsv", "metadata": "metadata.tsv"},
        domain="microbiome",
        requested_outputs=["differential_taxa_table", "volcano_plot_spec"],
        constraints={"group_column": "group"},
    )

    result = make_agent(tmp_path).run(task)

    assert result.status == AgentStatus.SUCCESS
    assert result.selected_skill_id == "microbiome.differential_abundance"
    assert result.selected_workflow_id == "microbiome.differential_abundance"
    assert result.run_id is not None
    assert "tables/differential_taxa.tsv" in result.output_files
    assert result.requires_review is True
    trace_path = tmp_path / "runs" / result.run_id / "agent_trace.json"
    assert trace_path.exists()
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["selected_skill_id"] == result.selected_skill_id


def test_high_risk_skill_is_marked_for_review(tmp_path):
    task = AgentTask(
        task_id="run_multiomics",
        user_query="构建多组学 correlation network",
        available_inputs={
            "feature_table": "feature.tsv",
            "expression_matrix": "expr.tsv",
            "metabolite_matrix": "met.tsv",
            "metadata": "metadata.tsv",
        },
        domain="multiomics",
        constraints={"sample_id_column": "sample_id"},
    )

    plan = make_agent(tmp_path).plan(task)

    assert plan.risk_level == "high"
    assert plan.requires_review is True
