from __future__ import annotations

from .models import Report


REQUIRED_SECTION_IDS = {
    "data_overview",
    "methodology",
    "main_results",
    "visualization",
    "evidence",
    "risk_warnings",
    "review_status",
    "appendix",
}

OVERSTRONG_TERMS = ("证明", "完全确认", "因果证明", "causal proof", "fully confirmed")


class ReportReviewer:
    def review(self, report: Report) -> list[str]:
        warnings: list[str] = []
        section_ids = {section.section_id for section in report.sections}
        missing = sorted(REQUIRED_SECTION_IDS - section_ids)
        if missing:
            warnings.append(f"Report is missing required sections: {missing}")

        appendix = next((section for section in report.sections if section.section_id == "appendix"), None)
        if appendix and "manifest.json" not in appendix.content:
            warnings.append("Report appendix does not reference manifest.json.")

        if report.metadata.requires_review:
            review_section = next((section for section in report.sections if section.section_id == "review_status"), None)
            if review_section and "需要专家复核" not in review_section.content:
                warnings.append("High-risk or review-required report does not clearly mark expert review.")

        full_text = "\n".join(section.content for section in report.sections).lower()
        for term in OVERSTRONG_TERMS:
            if term.lower() in full_text:
                warnings.append(f"Report contains over-strong wording: {term}")
        return warnings
