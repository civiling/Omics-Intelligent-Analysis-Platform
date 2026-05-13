from __future__ import annotations

from dataclasses import dataclass

from .loader import SkillLoader
from .models import LoadedSkill, SkillRouteRecommendation


@dataclass(frozen=True)
class _Rule:
    skill_id: str
    keywords: tuple[str, ...]
    reason: str
    weight: int = 10


RULES = [
    _Rule(
        "microbiome.differential_abundance",
        (
            "differential abundance",
            "差异菌群",
            "差异丰度",
            "ancom",
            "aldex",
            "maaslin",
        ),
        "The task asks for microbiome differential abundance analysis.",
        30,
    ),
    _Rule(
        "microbiome.read_qc",
        (
            "read qc",
            "quality control",
            "fastq",
            "reads",
            "feature table qc",
            "质控",
            "质量控制",
            "asv",
            "otu",
            "taxonomy",
        ),
        "The task mentions microbiome reads, ASV/OTU, taxonomy, or QC.",
    ),
    _Rule(
        "transcriptomics.differential_expression",
        (
            "rna-seq",
            "rnaseq",
            "count matrix",
            "differential expression",
            "deseq2",
            "edger",
            "limma",
            "差异表达",
            "差异基因",
            "转录组",
        ),
        "The task asks for transcriptomics differential expression analysis.",
        30,
    ),
    _Rule(
        "metabolomics.differential_metabolites",
        (
            "metabolomics",
            "peak table",
            "differential metabolites",
            "metabolite",
            "差异代谢物",
            "代谢组",
            "峰表",
        ),
        "The task asks for metabolomics differential metabolite analysis.",
        30,
    ),
    _Rule(
        "multiomics.correlation_network",
        (
            "correlation",
            "network",
            "multiomics",
            "multi-omics",
            "sparcc",
            "mixomics",
            "多组学关联",
            "关联网络",
            "相关网络",
        ),
        "The task asks for a multi-omics association or correlation network.",
        30,
    ),
    _Rule(
        "reporting.evidence_report_generation",
        (
            "report",
            "evidence",
            "literature",
            "文献",
            "报告",
            "证据",
            "专家复核",
        ),
        "The task asks for evidence labeling, literature questions, or report drafting.",
        30,
    ),
]

DOMAIN_KEYWORDS = {
    "microbiome": ("microbiome", "菌群", "asv", "otu", "taxonomy", "微生物组"),
    "transcriptomics": ("transcriptomics", "rna-seq", "rnaseq", "转录组", "基因表达"),
    "metabolomics": ("metabolomics", "代谢组", "metabolite", "代谢物", "peak table"),
    "multiomics": ("multiomics", "multi-omics", "多组学", "关联"),
    "reporting": ("report", "evidence", "报告", "文献", "证据"),
}


class SkillRouter:
    def __init__(self, loader: SkillLoader | None = None) -> None:
        self.loader = loader or SkillLoader()

    def recommend(
        self,
        task_description: str,
        available_inputs: list[str] | None = None,
        domain: str | None = None,
    ) -> SkillRouteRecommendation:
        available = set(available_inputs or [])
        skills = self.loader.load_all()
        candidates = self._candidate_skills(skills, domain)

        if not candidates:
            return SkillRouteRecommendation(
                skill_id=None,
                reason=f"No skills are registered for domain {domain!r}.",
                missing_inputs=[],
                risk_level=None,
                requires_review=False,
                next_skills=[],
            )

        normalized_task = task_description.lower()
        scores: dict[str, int] = {skill.id: 0 for skill in candidates}
        reasons: dict[str, list[str]] = {skill.id: [] for skill in candidates}

        for rule in RULES:
            if rule.skill_id not in scores:
                continue
            matched = [keyword for keyword in rule.keywords if keyword.lower() in normalized_task]
            if matched:
                scores[rule.skill_id] += rule.weight + len(matched)
                reasons[rule.skill_id].append(rule.reason)

        for skill in candidates:
            for input_type in skill.metadata.input_types:
                if input_type in available:
                    scores[skill.id] += 1
            for keyword in DOMAIN_KEYWORDS.get(skill.domain, ()):
                if keyword.lower() in normalized_task:
                    scores[skill.id] += 2
                    reasons[skill.id].append(f"The task matches the {skill.domain} domain.")
                    break

        selected = max(candidates, key=lambda skill: (scores[skill.id], -len(skill.metadata.input_types)))
        if scores[selected.id] == 0:
            selected = self._fallback_skill(candidates, available)
            reason = "No keyword rule matched; selected the closest registered skill by available inputs."
        else:
            reason = " ".join(dict.fromkeys(reasons[selected.id])) or "Selected by registry routing rules."

        missing_inputs = [
            input_type
            for input_type in selected.metadata.input_types
            if input_type not in available
        ]
        return SkillRouteRecommendation(
            skill_id=selected.id,
            reason=reason,
            missing_inputs=missing_inputs,
            risk_level=selected.metadata.risk_level,
            requires_review=selected.metadata.requires_review,
            next_skills=selected.metadata.next_skills,
        )

    def _candidate_skills(
        self,
        skills: dict[str, LoadedSkill],
        domain: str | None,
    ) -> list[LoadedSkill]:
        if domain is None:
            return list(skills.values())
        return [skill for skill in skills.values() if skill.domain == domain]

    def _fallback_skill(self, candidates: list[LoadedSkill], available: set[str]) -> LoadedSkill:
        return max(
            candidates,
            key=lambda skill: len(available.intersection(skill.metadata.input_types)),
        )
