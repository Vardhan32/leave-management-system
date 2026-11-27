"""Checks on the test tooling itself: the generator, the token resolver and the
schema checker. These run without the Flask app, so they also work as a quick
first check on a machine where the backend is not installed yet.
"""

import json
import sys
from datetime import date
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "generator"))

import generate_cases  # noqa: E402
from support.schema_check import validate  # noqa: E402
from support.tokens import add_working_days, base_monday, resolve_body, resolve_value  # noqa: E402

SPEC = HERE / "spec" / "openapi.yaml"


def by_id(result):
    return {case["id"]: case for case in result["cases"]}


def test_committed_cases_match_the_spec():
    committed = json.loads((HERE / "generated" / "cases.json").read_text(encoding="utf-8"))
    assert committed == generate_cases.generate(SPEC), "run the generator again"


def test_reason_gets_three_point_bva_on_both_limits():
    cases = by_id(generate_cases.generate(SPEC))
    expected = {
        "minLength-1_(9)": 422, "minLength_(10)": 201, "minLength+1_(11)": 201,
        "maxLength-1_(499)": 201, "maxLength_(500)": 201, "maxLength+1_(501)": 422,
    }
    for partition, status in expected.items():
        case = cases["createLeaveRequest.reason.BVA." + partition]
        assert case["expected_status"] == status
        assert case["value"] == {"$text": case["limit_length"]}


def test_every_invalid_body_case_changes_one_field_only():
    result = generate_cases.generate(SPEC)
    for case in result["cases"]:
        if case["location"] == "body" and case["field"] != "(body)":
            assert set(case.get("overrides", {})) <= {"end_date"}, case["id"]


def test_changing_two_constraints_changes_the_cases(tmp_path):
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    spec["components"]["schemas"]["LeaveRequestInput"]["properties"]["reason"]["maxLength"] = 300
    spec["x-business-rules"]["balance-limit"]["allocations"]["CASUAL"] = 10
    changed_spec = tmp_path / "openapi.yaml"
    changed_spec.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    before = generate_cases.generate(SPEC)
    after = generate_cases.generate(changed_spec)
    added, removed, _ = generate_cases.compare(before, after)

    assert "createLeaveRequest.reason.BVA.maxLength+1_(301)" in added
    assert "createLeaveRequest.reason.BVA.maxLength+1_(501)" in removed
    assert "createLeaveRequest.CASUAL.BVA.allocation+1_(11_days)" in added
    assert "createLeaveRequest.CASUAL.BVA.allocation+1_(13_days)" in removed


def test_tokens_resolve_relative_to_today():
    today = date(2026, 11, 18)
    assert resolve_value("{today}", {}, today) == "2026-11-18"
    assert resolve_value("{today-1}", {}, today) == "2026-11-17"
    assert resolve_value("{next_working_monday+2}", {}, today) == "2027-03-03"
    assert base_monday(today).weekday() == 0
    # the trailing space would be trimmed by the API, so it becomes a full stop
    assert resolve_value({"$text": 7, "$pad": 2}, {}, today) == "  Annual.  "


def test_end_date_follows_start_date():
    body = {"start_date": "{today+1}", "end_date": "{start_date-1}", "reason": "x"}
    resolved = resolve_body(body, today=date(2026, 11, 18))
    assert resolved == {"start_date": "2026-11-19", "end_date": "2026-11-18", "reason": "x"}


def test_missing_fields_are_dropped():
    assert resolve_body({"a": {"$missing": True}, "b": 1}) == {"b": 1}


def test_add_working_days_skips_weekends():
    monday = date(2027, 3, 1)
    assert add_working_days(monday, 1) == monday
    assert add_working_days(monday, 5) == date(2027, 3, 5)
    assert add_working_days(monday, 6) == date(2027, 3, 8)


def test_schema_checker_catches_missing_and_wrong_types():
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    schema = {"$ref": "#/components/schemas/LeaveType"}
    good = {"id": 1, "code": "CASUAL", "name": "Casual Leave", "default_days": 12, "description": None}
    assert validate(spec, schema, good) == []
    assert validate(spec, schema, {"id": "1", "code": "CASUAL", "name": "x", "default_days": 1})
    assert validate(spec, schema, {"id": 1, "code": "OTHER", "name": "x", "default_days": 1})
    assert validate(spec, schema, {"id": 1, "code": "CASUAL", "name": "x"})
