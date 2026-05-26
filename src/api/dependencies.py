from functools import lru_cache

from fastapi import Depends

from config import get_settings
from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.application.interfaces.capability_planner import CapabilityPlannerPort
from src.application.interfaces.report_generator import ReportGeneratorPort
from src.application.interfaces.skill_repository import SkillRepositoryPort
from src.application.interfaces.ui_generator import UiGeneratorPort
from src.application.use_cases.run_business_chat import RunBusinessChatUseCase
from src.infrastructure.agents.agent_framework_planner import AgentFrameworkPlanner
from src.infrastructure.agents.agent_framework_report import AgentFrameworkReportGenerator
from src.infrastructure.agents.agent_framework_ui import AgentFrameworkUiGenerator
from src.infrastructure.capabilities.capability_gateway import FastFixProCapabilityGateway
from src.infrastructure.skills.yaml_skill_repository import YamlSkillRepository


@lru_cache
def get_skill_repository() -> SkillRepositoryPort:
    settings = get_settings()
    return YamlSkillRepository(settings.business_chat.skills_dir)


@lru_cache
def get_capability_gateway() -> CapabilityGatewayPort:
    return FastFixProCapabilityGateway()


@lru_cache
def get_capability_planner() -> CapabilityPlannerPort:
    settings = get_settings()
    return AgentFrameworkPlanner(temperature=settings.business_chat.planner_temperature)


@lru_cache
def get_report_generator() -> ReportGeneratorPort:
    settings = get_settings()
    return AgentFrameworkReportGenerator(temperature=settings.business_chat.report_temperature)


@lru_cache
def get_ui_generator() -> UiGeneratorPort:
    settings = get_settings()
    return AgentFrameworkUiGenerator(temperature=settings.business_chat.report_temperature)


def get_run_business_chat_use_case(
    skill_repository: SkillRepositoryPort = Depends(get_skill_repository),
    capability_gateway: CapabilityGatewayPort = Depends(get_capability_gateway),
    planner: CapabilityPlannerPort = Depends(get_capability_planner),
    report_generator: ReportGeneratorPort = Depends(get_report_generator),
    ui_generator: UiGeneratorPort = Depends(get_ui_generator),
) -> RunBusinessChatUseCase:
    return RunBusinessChatUseCase(
        skill_repository, capability_gateway, planner, report_generator, ui_generator
    )
