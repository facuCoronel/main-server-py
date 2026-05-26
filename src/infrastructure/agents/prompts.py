import json
from typing import Any

from src.application.dtos.pipeline import ContextPack
from src.application.dtos.skill import SkillDefinition
from src.domain.value_objects.capability import CapabilityDescriptor
from src.domain.value_objects.intent_type import IntentType


def serialize_capabilities_for_prompt(capabilities: list[CapabilityDescriptor]) -> str:
    payload = [
        {
            "capability_id": c.id,
            "description": c.description,
            "params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "required": p.required,
                    "description": p.description,
                }
                for p in c.params
            ],
        }
        for c in capabilities
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_planner_instructions(
    skill: SkillDefinition, capabilities: list[CapabilityDescriptor]
) -> str:
    caps = serialize_capabilities_for_prompt(capabilities)
    constraints = "\n".join(f"- {c}" for c in skill.constraints) or "- (none)"
    return (
        f"{skill.planner.system_prompt}\n\n"
        "AVAILABLE CAPABILITIES (you may ONLY use these capability_id values):\n"
        f"{caps}\n\n"
        f"CONSTRAINTS:\n{constraints}\n\n"
        f"Select at most {skill.planner.max_capabilities} capabilities.\n"
        "Respond with ONLY a JSON object of this exact shape:\n"
        '{"items": [{"capability_id": "<one id from the list>", '
        '"reason": "<why it is needed>", "params": {"<param_name>": <value>}}]}\n'
        "Never invent capability_id values, endpoints, or parameter names that are not "
        'listed above. If no capability is relevant, return {"items": []}.'
    )


def build_planner_user_message(question: str, intent_type: IntentType) -> str:
    return f"intent_type: {intent_type.value}\nuser question: {question}"


def build_report_instructions(skill: SkillDefinition) -> str:
    sections = ", ".join(skill.report.sections) or "summary"
    constraints = "\n".join(f"- {c}" for c in skill.constraints) or "- (none)"
    return (
        f"{skill.report.system_prompt}\n\n"
        f"Write the report in language: {skill.language}.\n"
        "Use ONLY the data found in the context_pack provided by the user. "
        "Never invent figures, facts, or sources.\n"
        f"CONSTRAINTS:\n{constraints}\n\n"
        "Respond with ONLY a JSON object whose keys are the report sections:\n"
        f"sections: {sections}\n"
        'Also include a "limitations" key describing any missing or failed data '
        "(see data_quality). Each value must be a string (markdown allowed)."
    )


def build_report_user_message(context_pack: ContextPack) -> str:
    return json.dumps(context_pack.model_dump(), ensure_ascii=False, indent=2)


def build_ui_instructions(skill: SkillDefinition) -> str:
    ui = skill.ui
    allowed = ", ".join(ui.allowed_components) if ui and ui.allowed_components else "(none)"
    max_components = ui.max_components if ui else 8
    system_prompt = ui.system_prompt if ui else ""
    return (
        f"{system_prompt}\n\n"
        f"Write any text in language: {skill.language}.\n"
        "Use ONLY data present in the context_pack and the validated report provided by the user. "
        "Never invent figures, facts, or sources.\n"
        f"You may use ONLY these component types: {allowed}.\n"
        f"Use at most {max_components} components.\n"
        "Do NOT return HTML, CSS, Angular, or EChartsOption. Return ONLY a valid JSON object "
        "of this exact shape:\n"
        '{"layout": "executive_dashboard", "components": [{"id": "<unique id>", '
        '"type": "<one allowed type>", "title": "<title>", ...component fields...}]}\n'
        "Each component must have a unique id and a type from the allowed list."
    )


def build_ui_user_message(
    question: str,
    context_pack: ContextPack,
    validated_report: dict[str, Any],
) -> str:
    payload = {
        "question": question,
        "context_pack": context_pack.model_dump(),
        "validated_report": validated_report,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
