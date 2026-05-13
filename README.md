# Omics-Intelligent-Analysis-Platform

## Skill Registry

Skill Registry is the first-layer methodology and task specification base for the TDC/AIDD multi-omics analysis platform. It registers analysis skills, their inputs and outputs, recommended tools, key parameters, QC checks, interpretation limits, risk notes, review requirements, and allowed next skills.

This phase does not run real bioinformatics workflows, create multi-agent orchestration, perform molecular docking, generate a knowledge graph, or execute LLM-written analysis code. It only provides a structured contract for later workflow execution, agent routing, report generation, and audit tracing.

### Current skills

- `microbiome.read_qc`
- `microbiome.differential_abundance`
- `transcriptomics.differential_expression`
- `metabolomics.differential_metabolites`
- `multiomics.correlation_network`
- `reporting.evidence_report_generation`

### Directory contract

Each skill directory should contain:

- `SKILL.md`
- `input_schema.json`
- `output_schema.json`
- `parameters.yaml`
- `method_notes.md`
- `risk_notes.md`
- `executor.yaml`

`SKILL.md` must include these sections: Purpose, Use when, Inputs, Outputs, Primary tools, Default strategy, Parameters, QC checks, Interpretation limits, Risk notes, Next skills, and Review requirement.

### Add a skill

1. Create a directory under `skill_registry/skills/<domain>/<skill-name>/`.
2. Copy and adapt files from `skill_registry/templates/`.
3. Add the skill metadata to `skill_registry/registry.yaml`.
4. Use `next_skills` only for skill ids that already exist in the registry.
5. Keep `executor.yaml` as `type: placeholder` until a real workflow layer is introduced.

### Load and route skills

```python
from skill_registry import SkillLoader, SkillRouter

loader = SkillLoader()
skill = loader.get_by_id("microbiome.differential_abundance")

router = SkillRouter(loader)
recommendation = router.recommend(
    task_description="microbiome differential abundance with feature table and metadata",
    available_inputs=["feature_table", "metadata"],
)
print(recommendation.skill_id)
```

### Run Skill Registry validation

```bash
python -c "from skill_registry import SkillValidator; print(SkillValidator().validate())"
```

The expected result for a valid registry is an empty list: `[]`.

## Workflow Runtime

Workflow Runtime is the deterministic execution layer for registered analysis workflows. It connects workflow configs to Skill Registry metadata, creates isolated run directories, records inputs and parameters, writes logs, generates a manifest, and returns structured results for later visualization, evidence, report, and provenance modules.

The runtime deliberately does not let an LLM generate Python, R, or shell code and execute it directly. Future LLM or Agent layers may select a skill, recommend parameters, or explain results, but execution must go through a registered workflow config and a controlled executor.

### Relationship to Skill Registry

Each workflow config declares a `skill_id`. The workflow validator checks that:

- the `skill_id` exists in `skill_registry/registry.yaml`;
- workflow `input_types` and `output_types` are declared by the skill;
- `risk_level` and `requires_review` match the skill metadata.

### Current workflows

- `microbiome.read_qc`
- `microbiome.differential_abundance`
- `transcriptomics.differential_expression`
- `metabolomics.differential_metabolites`
- `multiomics.correlation_network`
- `reporting.evidence_report_generation`

### Add a workflow

1. Create a YAML config under `workflows/configs/`.
2. Set `id`, `skill_id`, `executor_type`, `script_path`, `input_types`, `output_types`, parameters, timeout, risk level, and review requirement.
3. Keep `executor_type: placeholder` until a real deterministic implementation is available.
4. If using `executor_type: local`, place the script under `workflows/scripts/`; `LocalExecutor` refuses scripts outside that registered scripts directory.
5. Run the workflow validator before using the config.

### Workflow config example

```yaml
id: microbiome.differential_abundance
name: Microbiome differential abundance workflow
domain: microbiome
version: 0.1.0
description: Placeholder workflow for microbiome differential abundance analysis.
skill_id: microbiome.differential_abundance
executor_type: placeholder
script_path: workflows/scripts/microbiome/differential_abundance_placeholder.py
input_types:
  - feature_table
  - taxonomy_table
  - metadata
output_types:
  - differential_taxa_table
  - volcano_plot_spec
  - method_note
  - risk_notes
default_parameters:
  method: ANCOM-BC2
  fdr_threshold: 0.05
required_parameters:
  - group_column
timeout_seconds: 3600
risk_level: medium
requires_review: true
```

### Run a placeholder workflow

```python
from workflows import WorkflowRunner

runner = WorkflowRunner()
result = runner.run(
    "microbiome.differential_abundance",
    input_files={
        "feature_table": "data/feature_table.tsv",
        "taxonomy_table": "data/taxonomy.tsv",
        "metadata": "data/metadata.tsv",
    },
    parameters={"group_column": "condition"},
)
print(result.status)
print(result.manifest_path)
```

### Run outputs

Each run creates a directory under `runs/`:

```text
runs/
└── run_YYYYMMDD_HHMMSS_xxxxxx/
    ├── inputs.json
    ├── parameters.yaml
    ├── manifest.json
    ├── logs/
    │   ├── stdout.log
    │   └── stderr.log
    └── outputs/
        ├── tables/
        ├── figures/
        └── notes/
```

`manifest.json` records the run id, workflow id, skill id, status, inputs, parameters, outputs, metrics, logs, timestamps, duration, error message, workflow config, and executor type.

### Future real tool integration

Real QIIME2, DADA2, DESeq2, MetaboAnalystR, or pyOpenMS workflows should be added as deterministic scripts or adapters referenced by workflow configs. They should write the same stable `outputs/tables`, `outputs/figures`, and `outputs/notes` structure, preserving manifest compatibility and auditability.

## Validation and Tests

```bash
python -c "from skill_registry import SkillValidator; print(SkillValidator().validate())"
python -c "from workflows import WorkflowValidator; print(WorkflowValidator().validate())"
python -m pytest tests
```

## Agent Orchestration

The controlled Agent Orchestration layer is documented in [docs/agent_orchestration.md](docs/agent_orchestration.md). It adds a rule-first `SupervisorAgent`, specialist agents, and tool wrappers for Skill Registry and Workflow Runtime without allowing agents to execute arbitrary user code.

### Lightweight CLI

Run the controlled agent CLI without installing a package:

```bash
python -m agents validate
python -m agents list-skills
python -m agents list-workflows
python -m agents plan --query "microbiome differential abundance" --domain microbiome --input feature_table=data/feature.tsv --input taxonomy_table=data/taxonomy.tsv --input metadata=data/metadata.tsv --param group_column=group
python -m agents run --query "microbiome differential abundance" --domain microbiome --input feature_table=data/feature.tsv --input taxonomy_table=data/taxonomy.tsv --input metadata=data/metadata.tsv --param group_column=group
```

Use `--json` on any command for machine-readable output.

## Visualization And Reporting

The visualization and reporting layer is documented in [docs/visualization_and_reporting.md](docs/visualization_and_reporting.md). It validates controlled chart specs, renders JSON/Plotly-compatible chart artifacts, reads workflow run outputs, and generates Markdown reports with risk notes and expert review status.
