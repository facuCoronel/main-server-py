from src.infrastructure.agents.agent_framework_report import parse_report


def test_parse_json_object():
    report = parse_report('{"resumen": "todo bien", "limitations": "ninguna"}')
    assert report == {"resumen": "todo bien", "limitations": "ninguna"}


def test_parse_fenced_json():
    report = parse_report('```json\n{"resumen": "ok"}\n```')
    assert report == {"resumen": "ok"}


def test_parse_non_json_falls_back_to_content():
    report = parse_report("This is a plain text report, not JSON.")
    assert report == {"content": "This is a plain text report, not JSON."}


def test_parse_json_list_falls_back_to_content():
    report = parse_report('["a", "b"]')
    assert report == {"content": ["a", "b"]}
