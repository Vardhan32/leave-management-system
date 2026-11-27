"""EP and BVA on every input, driven entirely by generated/cases.json.

Each case changes one field of a valid baseline request (one invalid value
per test), sends it, checks the status code and the field named in the error,
and then reads the shared records back to confirm that a rejected call left
nothing behind and an accepted call stored what was sent.
"""

import copy

import pytest

from support.flows import balances, baseline, next_year, read_request, request_count, submit_baseline
from support.generated import cases_where
from support.requirements import OPERATION_REQS
from support.tokens import is_missing, resolve_body, resolve_value

BODY_OPS = ("createLeaveRequest", "login", "reviewLeaveRequest")
QUERY_OPS = ("listBalances", "listLeaveRequests")
PATH_OPS = ("getLeaveRequest", "cancelLeaveRequest", "reviewLeaveRequest")


def as_params(cases):
    return [
        pytest.param(case, id=case["id"], marks=pytest.mark.req(*OPERATION_REQS[case["operation"]]))
        for case in cases
    ]


def build_body(case):
    if case["field"] == "(body)":
        return copy.deepcopy(case["value"])
    body = baseline(case["operation"])
    body[case["field"]] = copy.deepcopy(case["value"])
    body.update(case.get("overrides", {}))
    return body


# -- request bodies -----------------------------------------------------------
@pytest.mark.parametrize("case", as_params(cases_where(location="body", operation="createLeaveRequest")))
def test_create_leave_request_input(case, api, people):
    employee = people["employee"].token
    body = resolve_body(build_body(case))

    result = api.post("/api/leave-requests", token=employee, body=body)

    assert result.status == case["expected_status"], (case["partition"], body, result)
    if case.get("expected_error_field"):
        assert case["expected_error_field"] in result.error_fields(), result

    if result.status == 201:
        stored = read_request(api, employee, result.json["id"])
        assert stored["status"] == "pending"
        assert stored["start_date"] == body["start_date"]
        assert stored["end_date"] == body["end_date"]
        assert stored["reason"] == str(body["reason"]).strip()
        assert stored["days"] >= 1
        assert request_count(api, employee) == 1
    else:
        # a rejected submission must not leave a request behind
        assert request_count(api, employee) == 0


@pytest.mark.parametrize("case", as_params(cases_where(location="body", operation="login")))
def test_login_input(case, api, people):
    body = resolve_body(build_body(case))

    result = api.post("/api/auth/login", body=body)

    assert result.status == case["expected_status"], (case["partition"], result)
    if case.get("expected_error_field"):
        assert case["expected_error_field"] in result.error_fields(), result
    if result.status == 200:
        me = api.get("/api/auth/me", token=result.json["access_token"])
        assert me.status == 200
        assert me.json["user"]["email"] == people["employee"].email


@pytest.mark.parametrize("case", as_params(cases_where(location="body", operation="reviewLeaveRequest")))
def test_review_input(case, api, people):
    employee, admin = people["employee"].token, people["admin"].token
    pending = submit_baseline(api, employee)
    body = resolve_body(build_body(case))

    result = api.post("/api/leave-requests/{}/review".format(pending["id"]), token=admin, body=body)

    assert result.status == case["expected_status"], (case["partition"], body, result)
    if case.get("expected_error_field"):
        assert case["expected_error_field"] in result.error_fields(), result

    stored = read_request(api, employee, pending["id"])
    casual = balances(api, employee, next_year())["CASUAL"]
    if result.status == 200:
        decision = str(body["decision"]).strip()
        expected_status = "approved" if decision == "approve" else "rejected"
        assert stored["status"] == expected_status
        assert stored["reviewed_by"]["id"] == people["admin"].id
        assert casual["used_days"] == (pending["days"] if decision == "approve" else 0)
    else:
        # rejection by validation: the request and the balance stay as they were
        assert stored["status"] == "pending"
        assert stored["reviewed_by"] is None
        assert casual["used_days"] == 0


# -- query parameters ---------------------------------------------------------
QUERY_PATHS = {"listBalances": "/api/leave-balances", "listLeaveRequests": "/api/leave-requests"}
PAGING_DEFAULTS = {"page": 1, "per_page": 10}


@pytest.mark.parametrize("case", as_params(cases_where(location="query", operation=QUERY_OPS)))
def test_query_parameter(case, api, people):
    person = people[case.get("role", "employee")]
    submit_baseline(api, people["employee"].token)
    query = {}
    if not is_missing(case["value"]):
        value = resolve_value(case["value"], {"self_id": str(person.id)})
        query[case["field"]] = str(value)

    result = api.get(QUERY_PATHS[case["operation"]], token=person.token, query=query)

    assert result.status == case["expected_status"], (case["partition"], query, result)
    if "expected_echo" in case:
        # out-of-range paging values are clamped, not rejected
        assert result.json[case["field"]] == case["expected_echo"], result
    elif result.status == 200 and case["field"] in ("page", "per_page"):
        # an omitted parameter falls back to the backend default (utils.pagination_args)
        expected = int(query[case["field"]]) if case["field"] in query else PAGING_DEFAULTS[case["field"]]
        assert result.json[case["field"]] == expected


# -- path ids -----------------------------------------------------------------
PATH_TEMPLATES = {
    "getLeaveRequest": ("GET", "/api/leave-requests/{}", "employee"),
    "cancelLeaveRequest": ("POST", "/api/leave-requests/{}/cancel", "employee"),
    "reviewLeaveRequest": ("POST", "/api/leave-requests/{}/review", "admin"),
}


@pytest.mark.parametrize("case", as_params(cases_where(location="path", operation=PATH_OPS)))
def test_path_id(case, api, people):
    pending = submit_baseline(api, people["employee"].token)
    method, template, role = PATH_TEMPLATES[case["operation"]]
    value = resolve_value(case["value"], {"existing_id": str(pending["id"])})
    body = {"decision": "approve"} if case["operation"] == "reviewLeaveRequest" else None

    if method == "GET":
        result = api.get(template.format(value), token=people[role].token)
    elif body is None:
        result = api.post(template.format(value), token=people[role].token)
    else:
        result = api.post(template.format(value), token=people[role].token, body=body)

    assert result.status == case["expected_status"], (case["partition"], result)
    # whatever happened, the request the test created is still readable by its owner
    stored = read_request(api, people["employee"].token, pending["id"])
    if result.status == 404:
        assert stored["status"] == "pending"
