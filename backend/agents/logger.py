from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import AgentPlan, AgentResult, AgentTask


class AgentLogger:
    def __init__(self, logs_dir: str | Path | None = None) -> None:
        self.logs_dir = Path(logs_dir or Path(__file__).resolve().parent / "logs").resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def write_trace(
        self,
        task: AgentTask,
        plan: AgentPlan | None,
        result: AgentResult,
        run_dir: Path | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> Path:
        payload = self._trace_payload(task, plan, result, actions or [])
        if run_dir is not None:
            path = run_dir / "agent_trace.json"
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            return path

        path = self.logs_dir / "agent_trace.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return path

    def _trace_payload(
        self,
        task: AgentTask,
        plan: AgentPlan | None,
        result: AgentResult,
        actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "user_query": task.user_query,
            "selected_domain": self._selected_domain(plan),
            "selected_specialist_agent": plan.specialist_agent.value if plan and plan.specialist_agent else None,
            "selected_skill_id": result.selected_skill_id,
            "selected_workflow_id": result.selected_workflow_id,
            "parameters": plan.parameters if plan else {},
            "missing_inputs": plan.missing_inputs if plan else [],
            "risk_level": plan.risk_level if plan else None,
            "requires_review": result.requires_review,
            "run_id": result.run_id,
            "status": result.status.value,
            "error_message": result.error_message,
            "created_at": datetime.now().isoformat(),
            "actions": actions,
            "result": result.to_dict(),
        }

    def _selected_domain(self, plan: AgentPlan | None) -> str | None:
        if plan is None or plan.selected_skill_id is None:
            return None
        return plan.selected_skill_id.split(".", 1)[0]
