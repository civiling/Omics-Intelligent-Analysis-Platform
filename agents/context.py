from __future__ import annotations

from pathlib import Path

from skill_registry import SkillLoader
from workflows import WorkflowRunner


class AgentContext:
    def __init__(
        self,
        skill_loader: SkillLoader | None = None,
        workflow_runner: WorkflowRunner | None = None,
        agent_logs_dir: str | Path | None = None,
    ) -> None:
        self.skill_loader = skill_loader or SkillLoader()
        self.workflow_runner = workflow_runner or WorkflowRunner()
        self.agent_logs_dir = Path(agent_logs_dir or Path(__file__).resolve().parent / "logs").resolve()
        self.agent_logs_dir.mkdir(parents=True, exist_ok=True)
