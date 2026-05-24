import pytest

from src.application.dtos.skill import SkillDefinition
from src.application.errors import SkillNotFound
from src.domain.value_objects.intent_type import IntentType
from src.infrastructure.skills.yaml_skill_repository import YamlSkillRepository

VALID_YAML = """
intent_type: business_report
display_name: "Reporte de negocio"
description: "Genera un reporte."
language: es
planner:
  system_prompt: "Planificá."
  max_capabilities: 5
report:
  system_prompt: "Redactá."
  sections: [resumen]
output_schema: business_report
constraints:
  - "No inventar datos"
"""

MALFORMED_YAML = """
intent_type: business_report
display_name: "Falta planner y report"
description: "Incompleta"
output_schema: business_report
"""


async def test_get_valid_skill(tmp_path):
    (tmp_path / "business_report.yaml").write_text(VALID_YAML, encoding="utf-8")
    repo = YamlSkillRepository(tmp_path)

    skill = await repo.get(IntentType.BUSINESS_REPORT)

    assert isinstance(skill, SkillDefinition)
    assert skill.intent_type == IntentType.BUSINESS_REPORT
    assert skill.planner.max_capabilities == 5
    assert skill.report.sections == ["resumen"]


async def test_get_caches_result(tmp_path):
    path = tmp_path / "business_report.yaml"
    path.write_text(VALID_YAML, encoding="utf-8")
    repo = YamlSkillRepository(tmp_path)

    first = await repo.get(IntentType.BUSINESS_REPORT)
    path.unlink()  # remove the file; cache must still serve it
    second = await repo.get(IntentType.BUSINESS_REPORT)

    assert first is second


async def test_missing_skill_raises(tmp_path):
    repo = YamlSkillRepository(tmp_path)
    with pytest.raises(SkillNotFound):
        await repo.get(IntentType.MARKETING_PLAN)


async def test_malformed_skill_raises(tmp_path):
    (tmp_path / "business_report.yaml").write_text(MALFORMED_YAML, encoding="utf-8")
    repo = YamlSkillRepository(tmp_path)
    with pytest.raises(SkillNotFound):
        await repo.get(IntentType.BUSINESS_REPORT)
