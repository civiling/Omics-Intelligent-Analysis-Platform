from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from agents import AgentContext, AgentStatus, AgentTask, SupervisorAgent
from reports import ReportGenerator
from skill_registry import SkillValidator
from workflows import WorkflowRunner, WorkflowValidator


PROJECT_ROOT = Path(__file__).resolve().parent
EXAMPLE_DATA_DIR = PROJECT_ROOT / "data" / "examples"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print_header("Omics Intelligent Analysis Platform Demo")

    if not validate_registries():
        return 1

    input_files = ensure_example_inputs()
    runner = WorkflowRunner(runs_dir=args.runs_dir) if args.runs_dir else WorkflowRunner()
    agent = SupervisorAgent(
        context=AgentContext(
            workflow_runner=runner,
            agent_logs_dir=args.agent_logs_dir,
        )
    )
    task = AgentTask(
        task_id=f"demo_{uuid4().hex[:10]}",
        user_query=args.query,
        domain=args.domain,
        available_inputs=input_files,
        constraints={"group_column": args.group_column},
    )

    print_header("Run Workflow")
    result = agent.run(task)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    if result.status != AgentStatus.SUCCESS or result.run_id is None:
        print("\nDemo failed before report generation.", file=sys.stderr)
        return 1

    run_dir = runner.runs_dir / result.run_id
    print_header("Generate Report")
    report = ReportGenerator().generate_markdown_report(run_dir)

    output_paths = collect_output_paths(
        run_dir=run_dir,
        result_payload=result.to_dict(),
        report_path=report.output_path,
    )
    print_header("Output Paths")
    for label, path in output_paths.items():
        print(f"{label}: {path}")

    print("\nDemo completed successfully.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a one-command placeholder demo: validate, run workflow, generate report, and list outputs."
    )
    parser.add_argument(
        "--query",
        default="microbiome differential abundance",
        help="Task query used by the controlled supervisor agent.",
    )
    parser.add_argument(
        "--domain",
        default="microbiome",
        help="Domain hint used by the controlled supervisor agent.",
    )
    parser.add_argument(
        "--group-column",
        default="group",
        help="Demo group column parameter for the microbiome differential abundance workflow.",
    )
    parser.add_argument(
        "--runs-dir",
        default=None,
        help="Optional runs directory override.",
    )
    parser.add_argument(
        "--agent-logs-dir",
        default=None,
        help="Optional agent logs directory override.",
    )
    return parser


def validate_registries() -> bool:
    print_header("Validate Registries")
    skill_errors = SkillValidator().validate()
    workflow_errors = WorkflowValidator().validate()
    payload = {
        "skill_registry_errors": skill_errors,
        "workflow_errors": workflow_errors,
        "ok": not skill_errors and not workflow_errors,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload["ok"]


def ensure_example_inputs() -> dict[str, str]:
    EXAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "feature_table": EXAMPLE_DATA_DIR / "feature_table.tsv",
        "taxonomy_table": EXAMPLE_DATA_DIR / "taxonomy.tsv",
        "metadata": EXAMPLE_DATA_DIR / "metadata.tsv",
    }
    contents = {
        "feature_table": "feature_id\tsample_1\tsample_2\nfeature_a\t10\t5\nfeature_b\t2\t8\n",
        "taxonomy_table": "feature_id\ttaxon\nfeature_a\tBacteria;Firmicutes\nfeature_b\tBacteria;Bacteroidota\n",
        "metadata": "sample_id\tgroup\nsample_1\tcontrol\nsample_2\ttreatment\n",
    }
    for input_type, path in files.items():
        if not path.exists():
            path.write_text(contents[input_type], encoding="utf-8")
    return {input_type: str(path) for input_type, path in files.items()}


def collect_output_paths(
    run_dir: Path,
    result_payload: dict[str, Any],
    report_path: Path,
) -> dict[str, str]:
    output_paths = {
        "run_dir": str(run_dir),
        "manifest": str(run_dir / "manifest.json"),
        "report": str(report_path),
        "report_metadata": str(report_path.with_suffix(".metadata.json")),
        "stdout_log": str(run_dir / "logs" / "stdout.log"),
        "stderr_log": str(run_dir / "logs" / "stderr.log"),
    }
    for relative_path, absolute_path in result_payload.get("output_files", {}).items():
        output_paths[f"output:{relative_path}"] = str(absolute_path)
    return output_paths


def print_header(title: str) -> None:
    print(f"\n== {title} ==")


if __name__ == "__main__":
    raise SystemExit(main())
