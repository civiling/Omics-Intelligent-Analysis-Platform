from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from skill_registry import SkillLoader, SkillValidator
from workflows import WorkflowRunner, WorkflowValidator

from .context import AgentContext
from .models import AgentTask
from .supervisor import SupervisorAgent


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agents",
        description="Controlled CLI for Skill Registry, Workflow Runtime, and Agent Orchestration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate skill and workflow registries.")
    validate_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    validate_parser.set_defaults(func=cmd_validate)

    skills_parser = subparsers.add_parser("list-skills", help="List registered skill ids.")
    skills_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    skills_parser.set_defaults(func=cmd_list_skills)

    workflows_parser = subparsers.add_parser("list-workflows", help="List registered workflow ids.")
    workflows_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    workflows_parser.set_defaults(func=cmd_list_workflows)

    plan_parser = subparsers.add_parser("plan", help="Plan an agent task without running a workflow.")
    add_task_arguments(plan_parser)
    plan_parser.set_defaults(func=cmd_plan)

    run_parser = subparsers.add_parser("run", help="Run an agent task through registered workflows.")
    add_task_arguments(run_parser)
    run_parser.set_defaults(func=cmd_run)
    return parser


def add_task_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-id", default=None, help="Stable task id. Defaults to a generated id.")
    parser.add_argument("--query", required=True, help="User task description.")
    parser.add_argument("--domain", default=None, help="Optional domain hint.")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        type=parse_key_value,
        metavar="TYPE=PATH",
        help="Available input artifact, repeatable. Example: --input metadata=data/metadata.tsv",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        type=parse_key_value,
        metavar="KEY=VALUE",
        help="Task constraint or workflow parameter, repeatable. Example: --param group_column=group",
    )
    parser.add_argument(
        "--requested-output",
        action="append",
        default=[],
        help="Requested output type, repeatable.",
    )
    parser.add_argument("--runs-dir", default=None, help="Override runs directory.")
    parser.add_argument("--agent-logs-dir", default=None, help="Override agent log directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")


def cmd_validate(args: argparse.Namespace) -> int:
    skill_errors = SkillValidator().validate()
    workflow_errors = WorkflowValidator().validate()
    payload = {
        "skill_registry_errors": skill_errors,
        "workflow_errors": workflow_errors,
        "ok": not skill_errors and not workflow_errors,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if payload["ok"]:
            print("OK: skill registry and workflow configs are valid.")
        else:
            for label, errors in (
                ("Skill Registry", skill_errors),
                ("Workflow Runtime", workflow_errors),
            ):
                if errors:
                    print(f"{label} errors:")
                    for error in errors:
                        print(f"- {error}")
    return 0 if payload["ok"] else 1


def cmd_list_skills(args: argparse.Namespace) -> int:
    skills = SkillLoader().load_all()
    payload = [
        {
            "id": skill.id,
            "domain": skill.domain,
            "risk_level": skill.metadata.risk_level.value,
            "requires_review": skill.metadata.requires_review,
        }
        for skill in skills.values()
    ]
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for item in payload:
            print(item["id"])
    return 0


def cmd_list_workflows(args: argparse.Namespace) -> int:
    workflows = WorkflowRunner().list_workflows()
    payload = [
        {
            "id": workflow.id,
            "skill_id": workflow.skill_id,
            "executor_type": workflow.executor_type.value,
            "requires_review": workflow.requires_review,
        }
        for workflow in workflows
    ]
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for item in payload:
            print(item["id"])
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    agent = build_agent(args)
    task = build_task(args)
    plan = agent.plan(task)
    payload = plan.to_dict()
    print_payload(payload, args.json)
    return 0 if plan.selected_skill_id else 2


def cmd_run(args: argparse.Namespace) -> int:
    agent = build_agent(args)
    task = build_task(args)
    result = agent.run(task)
    payload = result.to_dict()
    print_payload(payload, args.json)
    if result.status.value == "success":
        return 0
    if result.status.value == "needs_input":
        return 2
    return 1


def build_agent(args: argparse.Namespace) -> SupervisorAgent:
    runner = WorkflowRunner(runs_dir=args.runs_dir) if args.runs_dir else WorkflowRunner()
    context = AgentContext(
        workflow_runner=runner,
        agent_logs_dir=Path(args.agent_logs_dir) if args.agent_logs_dir else None,
    )
    return SupervisorAgent(context=context)


def build_task(args: argparse.Namespace) -> AgentTask:
    return AgentTask(
        task_id=args.task_id or f"cli_{uuid4().hex[:10]}",
        user_query=args.query,
        available_inputs=dict(args.input),
        domain=args.domain,
        requested_outputs=list(args.requested_output),
        constraints={key: parse_scalar(value) for key, value in args.param},
    )


def parse_key_value(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"Expected KEY=VALUE, got {value!r}.")
    key, parsed_value = value.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError("KEY must not be empty.")
    return key, parsed_value.strip()


def parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def print_payload(payload: dict[str, Any] | list[dict[str, Any]], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    if isinstance(payload, list):
        for item in payload:
            print(item)
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    sys.exit(main())
