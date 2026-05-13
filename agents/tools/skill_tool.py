from __future__ import annotations

from skill_registry import SkillLoader

from agents.exceptions import AgentToolError


class SkillTool:
    def __init__(self, loader: SkillLoader | None = None) -> None:
        self.loader = loader or SkillLoader()

    def list_skills(self):
        return list(self.loader.load_all().values())

    def get_skill(self, skill_id: str):
        skill = self.loader.get_by_id(skill_id)
        if skill is None:
            raise AgentToolError(f"Skill is not registered: {skill_id}")
        return skill

    def find_skills_by_domain(self, domain: str):
        return self.loader.get_by_domain(domain)

    def find_skills_by_input_types(self, input_types: list[str]):
        found = {}
        for input_type in input_types:
            for skill in self.loader.get_by_input_type(input_type):
                found[skill.id] = skill
        return list(found.values())

    def validate_skill_exists(self, skill_id: str) -> bool:
        self.get_skill(skill_id)
        return True
