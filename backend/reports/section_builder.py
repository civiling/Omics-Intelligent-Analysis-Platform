from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import ReportSection


class ReportSectionBuilder:
    def build_sections(self, data: dict[str, Any]) -> list[ReportSection]:
        manifest = data.get("manifest", {})
        risk_level = self._risk_level(manifest, data.get("agent_trace", {}))
        requires_review = self._requires_review(manifest, data.get("agent_trace", {}))
        return [
            self._overview(data, risk_level, requires_review),
            self._method(data, risk_level, requires_review),
            self._main_results(data, risk_level, requires_review),
            self._visualization(data, risk_level, requires_review),
            self._evidence(data, risk_level, requires_review),
            self._risk(data, risk_level, requires_review),
            self._review(data, risk_level, requires_review),
            self._appendix(data, risk_level, requires_review),
        ]

    def _overview(self, data, risk_level, requires_review) -> ReportSection:
        manifest = data.get("manifest", {})
        content = "\n".join(
            [
                f"- run_id: {manifest.get('run_id', '未提供')}",
                f"- workflow_id: {manifest.get('workflow_id', '未提供')}",
                f"- skill_id: {manifest.get('skill_id', '未提供')}",
                f"- status: {manifest.get('status', '未提供')}",
                "- input_files:",
                *[f"  - {key}: {value}" for key, value in (manifest.get("input_files") or {}).items()],
                "- parameters:",
                *[f"  - {key}: {value}" for key, value in (data.get("parameters") or {}).items()],
            ]
        )
        return ReportSection("data_overview", "1. 数据与任务概况", content, [self._source(data, "manifest_path"), self._source(data, "parameters_path")], risk_level, requires_review)

    def _method(self, data, risk_level, requires_review) -> ReportSection:
        content = data.get("method_note") or "本次运行未提供方法学说明。"
        return ReportSection("methodology", "2. 方法学说明", content, ["outputs/notes/method_note.md"], risk_level, requires_review)

    def _main_results(self, data, risk_level, requires_review) -> ReportSection:
        tables = data.get("tables") or {}
        figures = data.get("figures") or {}
        lines = ["主要结果文件："]
        lines.extend([f"- {name}: {path}" for name, path in tables.items()] or ["- 未提供结果表。"])
        lines.append("图表配置文件：")
        lines.extend([f"- {name}: {path}" for name, path in figures.items()] or ["- 未提供图表配置。"])
        return ReportSection("main_results", "3. 主要结果", "\n".join(lines), list(tables) + list(figures), risk_level, requires_review)

    def _visualization(self, data, risk_level, requires_review) -> ReportSection:
        figures = data.get("figures") or {}
        lines = [f"- {name}: {path}" for name, path in figures.items()] or ["本次运行未提供可视化 JSON。"]
        return ReportSection("visualization", "4. 可视化结果", "\n".join(lines), list(figures), risk_level, requires_review)

    def _evidence(self, data, risk_level, requires_review) -> ReportSection:
        content = data.get("evidence_notes") or data.get("report_draft") or "本次运行未提供文献证据结果。"
        return ReportSection("evidence", "5. 文献证据与解释", content, ["outputs/notes/evidence_notes.md", "outputs/notes/report_draft.md"], risk_level, requires_review)

    def _risk(self, data, risk_level, requires_review) -> ReportSection:
        content = data.get("risk_notes") or "本次运行未提供风险提示。"
        content += f"\n\n- requires_review: {requires_review}"
        return ReportSection("risk_warnings", "6. 风险提示与解释限制", content, ["outputs/notes/risk_notes.md"], risk_level, requires_review)

    def _review(self, data, risk_level, requires_review) -> ReportSection:
        status = "需要专家复核" if requires_review else "当前未标记为必须专家复核"
        agent_trace = data.get("agent_trace") or {}
        next_steps = agent_trace.get("result", {}).get("next_steps") or agent_trace.get("next_steps") or []
        lines = [f"- 专家复核状态: {status}", f"- risk_level: {risk_level or '未提供'}"]
        if next_steps:
            lines.append("- 建议后续任务:")
            lines.extend([f"  - {step}" for step in next_steps])
        return ReportSection("review_status", "7. 专家复核状态", "\n".join(lines), ["manifest.json", "agent_trace.json"], risk_level, requires_review)

    def _appendix(self, data, risk_level, requires_review) -> ReportSection:
        manifest = data.get("manifest", {})
        output_files = manifest.get("output_files") or {}
        lines = [
            "- parameters.yaml",
            "- manifest.json",
            "- output files:",
            *[f"  - {name}: {path}" for name, path in output_files.items()],
            "- tool versions: 未提供",
        ]
        return ReportSection("appendix", "8. 附录", "\n".join(lines), ["parameters.yaml", "manifest.json"], risk_level, requires_review)

    def _risk_level(self, manifest: dict[str, Any], agent_trace: dict[str, Any]) -> str | None:
        return (
            agent_trace.get("risk_level")
            or (manifest.get("workflow_config") or {}).get("risk_level")
        )

    def _requires_review(self, manifest: dict[str, Any], agent_trace: dict[str, Any]) -> bool:
        if "requires_review" in agent_trace:
            return bool(agent_trace["requires_review"])
        return bool((manifest.get("workflow_config") or {}).get("requires_review", False))

    def _source(self, data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        return str(value) if isinstance(value, Path) else str(value or "")
