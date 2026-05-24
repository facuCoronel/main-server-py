import logging

from src.application.dtos.business_chat import BusinessChatCommand, BusinessChatResult
from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.application.interfaces.capability_planner import CapabilityPlannerPort
from src.application.interfaces.report_generator import ReportGeneratorPort
from src.application.interfaces.skill_repository import SkillRepositoryPort
from src.application.pipeline.discovery_step import run_discovery
from src.application.pipeline.execution_step import run_execution
from src.application.pipeline.packaging_step import build_context_pack
from src.application.pipeline.planning_step import run_planning, validate_plan
from src.application.pipeline.report_step import run_report
from src.application.pipeline.validation_step import validate_and_repair

logger = logging.getLogger(__name__)


class RunBusinessChatUseCase:
    """Orchestrates the /business-chat pipeline.

    skill resolution → discovery → planning (+ anti-hallucination validation) → execution
    (partial-failure tolerant) → context packaging → report generation (LLM, no tools) →
    output validation (+ one repair pass).
    """

    def __init__(
        self,
        skill_repository: SkillRepositoryPort,
        capability_gateway: CapabilityGatewayPort,
        planner: CapabilityPlannerPort,
        report_generator: ReportGeneratorPort,
    ) -> None:
        self._skill_repository = skill_repository
        self._capability_gateway = capability_gateway
        self._planner = planner
        self._report_generator = report_generator

    async def execute(self, command: BusinessChatCommand) -> BusinessChatResult:
        rid = command.request_id
        logger.info("[%s] business-chat start intent=%s", rid, command.intent_type.value)

        skill = await self._skill_repository.get(command.intent_type)
        logger.info("[%s] resolved skill '%s'", rid, skill.display_name)

        capabilities = await run_discovery(self._capability_gateway)
        logger.info("[%s] discovered %d capabilities", rid, len(capabilities))

        raw_plan = await run_planning(
            self._planner, command.question, command.intent_type, skill, capabilities
        )
        validation = validate_plan(raw_plan, capabilities, skill.planner.max_capabilities)
        logger.info(
            "[%s] plan: %d kept, %d discarded",
            rid,
            len(validation.plan.items),
            len(validation.discarded),
        )

        results = await run_execution(self._capability_gateway, validation.plan)
        context_pack = build_context_pack(
            command.intent_type, command.question, skill, results
        )
        data_quality = context_pack.data_quality
        logger.info(
            "[%s] execution: %d/%d succeeded",
            rid,
            data_quality.succeeded,
            data_quality.requested,
        )

        report = await run_report(self._report_generator, context_pack, skill)
        final_report = await validate_and_repair(
            self._report_generator, report, context_pack, skill
        )

        warnings: list[str] = []
        if validation.discarded:
            warnings.append(
                f"discarded {len(validation.discarded)} capabilities not in catalog: "
                f"{validation.discarded}"
            )
        if data_quality.failed:
            warnings.append(
                f"{data_quality.failed} capabilities failed: {data_quality.failed_capabilities}"
            )

        return BusinessChatResult(
            request_id=rid,
            intent_type=command.intent_type,
            report=final_report,
            data_quality=data_quality,
            warnings=warnings,
        )
