from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class AgentStatus(str, Enum):
    PENDING = "pending"
    PLANNED = "planned"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"
    NEEDS_REVIEW = "needs_review"


class SpecialistAgentType(str, Enum):
    MICROBIOME = "microbiome"
    TRANSCRIPTOMICS = "transcriptomics"
    METABOLOMICS = "metabolomics"
    MULTIOMICS = "multiomics"
    EVIDENCE = "evidence"
    REPORTING = "reporting"


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    user_query: str
    available_inputs: dict[str, str]
    domain: str | None = None
    requested_outputs: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class AgentPlan:
    task_id: str
    selected_skill_id: str | None
    selected_workflow_id: str | None
    specialist_agent: SpecialistAgentType | None
    reasoning: str
    missing_inputs: list[str]
    parameters: dict[str, Any]
    risk_level: str | None
    requires_review: bool
    next_steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["specialist_agent"] = self.specialist_agent.value if self.specialist_agent else None
        return data


@dataclass(frozen=True)
class AgentAction:
    action_id: str
    task_id: str
    action_type: str
    tool_name: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    status: AgentStatus
    error_message: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        task_id: str,
        action_type: str,
        tool_name: str,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
        status: AgentStatus,
        error_message: str | None = None,
    ) -> "AgentAction":
        return cls(
            action_id=f"action_{uuid4().hex[:10]}",
            task_id=task_id,
            action_type=action_type,
            tool_name=tool_name,
            input_payload=input_payload,
            output_payload=output_payload,
            status=status,
            error_message=error_message,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass(frozen=True)
class AgentResult:
    task_id: str
    status: AgentStatus
    selected_skill_id: str | None
    selected_workflow_id: str | None
    run_id: str | None
    summary: str
    output_files: dict[str, str]
    risk_notes: str
    requires_review: bool
    next_steps: list[str]
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class AgentRoute:
    domain: str | None
    specialist_agent: SpecialistAgentType | None
    candidate_skill_ids: list[str]
    reasoning: str
    confidence: float
