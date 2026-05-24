import pytest

from src.application.errors import PlanningError
from src.infrastructure.agents.agent_framework_planner import parse_plan


def test_parse_plain_json_object():
    text = '{"items": [{"capability_id": "get_sales", "reason": "r", "params": {"month": 4}}]}'
    plan = parse_plan(text)
    assert plan.items[0].capability_id == "get_sales"
    assert plan.items[0].params == {"month": 4}


def test_parse_json_list_is_wrapped():
    plan = parse_plan('[{"capability_id": "get_sales", "reason": "r"}]')
    assert plan.items[0].capability_id == "get_sales"


def test_parse_markdown_fenced_json():
    text = '```json\n{"items": [{"capability_id": "get_sales", "reason": "r"}]}\n```'
    plan = parse_plan(text)
    assert plan.items[0].capability_id == "get_sales"


def test_parse_json_with_surrounding_prose():
    text = (
        'Sure! Here is the plan:\n'
        '{"items": [{"capability_id": "get_sales", "reason": "r"}]}\nLet me know!'
    )
    plan = parse_plan(text)
    assert plan.items[0].capability_id == "get_sales"


def test_parse_empty_items():
    plan = parse_plan('{"items": []}')
    assert plan.items == []


def test_parse_invalid_json_raises_planning_error():
    with pytest.raises(PlanningError):
        parse_plan("this is not json at all")


def test_parse_schema_mismatch_raises_planning_error():
    with pytest.raises(PlanningError):
        parse_plan('{"items": [{"reason": "missing capability_id"}]}')
