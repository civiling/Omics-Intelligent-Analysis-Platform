# Agent Orchestration

Agent Orchestration is the controlled scheduling layer for the TDC/AIDD multi-omics analysis platform. It lets an agent understand a user task, select a registered skill, choose a specialist, call a registered workflow, summarize outputs, and suggest next steps.

This layer is deliberately not a fully autonomous multi-agent system. The first version is rule-first, deterministic, and constrained by the Skill Registry and Workflow Runtime.

## Relationship To Skill Registry

Agents use `skill_registry` to validate that a selected skill exists. Risk level, review requirement, input types, output types, and next-step suggestions come from skill metadata.

If a selected skill is missing required workflow inputs, the agent returns `needs_input` instead of trying to run anything.

## Relationship To Workflow Runtime

Agents call workflows through `WorkflowTool`, which wraps `WorkflowRunner`. The selected workflow id is resolved from the selected skill id. Agents never call scripts directly and never build shell commands from user input.

Workflow Runtime remains responsible for run directories, manifests, logs, parameters, and deterministic placeholder outputs.

## Why Agents Cannot Execute Arbitrary Code

The platform must be reproducible, auditable, and safe for scientific analysis. Allowing an LLM or agent to generate and execute arbitrary Python, R, or shell code would bypass registered methods, risk notes, review requirements, and provenance records.

Agents may later use LLMs to help explain tasks or recommend parameters, but execution must still go through registered tools and workflows.

## SupervisorAgent

`SupervisorAgent` performs this sequence:

1. Route the task with `AgentRouter`.
2. Select a specialist agent.
3. Build an `AgentPlan`.
4. Check missing inputs.
5. Resolve workflow by skill id.
6. Run the workflow through `WorkflowTool`.
7. Summarize outputs.
8. Write `agent_trace.json` in the run directory, or `agents/logs/agent_trace.jsonl` if no workflow was run.

## Specialist Agents

- `MicrobiomeAgent`: `microbiome.read_qc`, `microbiome.differential_abundance`
- `TranscriptomicsAgent`: `transcriptomics.differential_expression`
- `MetabolomicsAgent`: `metabolomics.differential_metabolites`
- `MultiomicsAgent`: `multiomics.correlation_network`
- `EvidenceAgent`: `reporting.evidence_report_generation`
- `ReportAgent`: `reporting.evidence_report_generation`

Specialists query Skill Registry before returning a skill id. They prepare parameters from workflow defaults and task constraints.

## Add A Specialist Agent

1. Add a class under `agents/specialists/`.
2. Set `agent_type` and `supported_skill_ids`.
3. Implement `select_skill(task)`.
4. Register the class in `agents/planner.py`.
5. Add router rules in `agents/router.py`.
6. Add tests for routing, planning, and workflow integration.

## Example Task

```python
from agents.models import AgentTask
from agents.supervisor import SupervisorAgent

task = AgentTask(
    task_id="demo_microbiome_001",
    user_query="Please run microbiome differential abundance analysis",
    available_inputs={
        "feature_table": "examples/demo/feature_table.tsv",
        "taxonomy_table": "examples/demo/taxonomy.tsv",
        "metadata": "examples/demo/metadata.tsv",
    },
    domain="microbiome",
    requested_outputs=["differential_taxa_table", "volcano_plot_spec"],
    constraints={"group_column": "group"},
)

agent = SupervisorAgent()
result = agent.run(task)
print(result)
```

## Lightweight CLI

The repository provides a small CLI through `python -m agents`.

```bash
python -m agents validate --json
python -m agents list-skills
python -m agents list-workflows
```

Plan without running:

```bash
python -m agents plan \
  --query "microbiome differential abundance" \
  --domain microbiome \
  --input feature_table=examples/demo/feature_table.tsv \
  --input taxonomy_table=examples/demo/taxonomy.tsv \
  --input metadata=examples/demo/metadata.tsv \
  --param group_column=group \
  --json
```

Run through the controlled Agent and Workflow Runtime:

```bash
python -m agents run \
  --query "microbiome differential abundance" \
  --domain microbiome \
  --input feature_table=examples/demo/feature_table.tsv \
  --input taxonomy_table=examples/demo/taxonomy.tsv \
  --input metadata=examples/demo/metadata.tsv \
  --param group_column=group \
  --json
```

The CLI never accepts a shell command or script to execute. It only passes task text, registered input types, requested outputs, and parameters into `SupervisorAgent`.

## AgentPlan Fields

- `task_id`: user task id
- `selected_skill_id`: selected registry skill
- `selected_workflow_id`: workflow resolved from skill
- `specialist_agent`: selected specialist
- `reasoning`: explainable routing and selection reason
- `missing_inputs`: required workflow inputs not available
- `parameters`: merged workflow defaults and task constraints
- `risk_level`: skill risk level
- `requires_review`: skill review requirement
- `next_steps`: skill-derived next suggestions

## AgentResult Fields

- `task_id`
- `status`
- `selected_skill_id`
- `selected_workflow_id`
- `run_id`
- `summary`
- `output_files`
- `risk_notes`
- `requires_review`
- `next_steps`
- `error_message`

## Future LLM Or Framework Integration

LangGraph, OpenAI Agents SDK, or other frameworks can wrap this module later. The invariant should remain: LLMs can help with task understanding, parameter suggestions, and narrative summaries, but registered tools and workflow configs remain the only execution path.
