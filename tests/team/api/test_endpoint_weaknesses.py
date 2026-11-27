"""Endpoint weaknesses found while writing the spec and the tests.

Each test asserts what the test basis expects. They are marked
xfail(strict=True) with the weakness id from reports/endpoint_weaknesses.md:
today they fail, which pytest reports as "xfailed". When someone fixes the
code the test passes, strict mode turns that into a failure, and the marker
has to be removed on purpose. That keeps the list honest.

Before logging these as GitHub Issues, run this file once and confirm each
one is reported as xfailed for the reason written in its docstring.
"""

from datetime import date, timedelta

import pytest

from support.flows import cancel, leave_body, request_count, submit, submit_days
from support.tokens import base_monday


@pytest.mark.req("FR-06")
@pytest.mark.xfail(strict=True, reason="WK-01: year is not range-checked and GET creates balance rows")
def test_wk01_balance_year_out_of_range_is_rejected(api, people):
    """GET /api/leave-balances?year=1900 answers 200 and inserts three balance rows."""
    result = api.get("/api/leave-balances", token=people["employee"].token, query={"year": "1900"})
    assert result.status == 400


@pytest.mark.req("FR-02")
@pytest.mark.xfail(strict=True, reason="WK-02: a fractional leave_type_id is truncated by int()")
def test_wk02_fractional_leave_type_id_is_rejected(api, people):
    body = leave_body(1, base_monday(), base_monday() + timedelta(days=2))
    body["leave_type_id"] = 1.9
    result = api.post("/api/leave-requests", token=people["employee"].token, body=body)
    assert result.status == 422


@pytest.mark.req("FR-06")
@pytest.mark.xfail(strict=True, reason="WK-03: % and _ in q are LIKE wildcards, not literal text")
def test_wk03_search_treats_percent_literally(api, people, type_ids):
    employee = people["employee"].token
    submit_days(api, employee, type_ids["CASUAL"], 2)
    # no reason contains a percent sign, so a literal search finds nothing
    assert request_count(api, employee, q="%") == 0


@pytest.mark.req("FR-11", "BR3")
@pytest.mark.xfail(strict=True, reason="WK-04: a pending request that starts today can be created but not cancelled")
def test_wk04_pending_request_starting_today_can_be_cancelled(api, people, type_ids):
    """README: 'Employees can cancel pending requests and approved requests that
    have not started.' The code also blocks pending requests once start <= today."""
    employee = people["employee"].token
    today = date.today()
    created = submit(api, employee, type_ids["CASUAL"], today, today + timedelta(days=6)).json
    result = cancel(api, employee, created["id"], expect=None)
    assert result.status == 200


@pytest.mark.req("FR-06")
@pytest.mark.xfail(strict=True, reason="WK-05: department and q together join users twice")
def test_wk05_admin_can_combine_department_and_search(api, people, type_ids):
    submit_days(api, people["colleague"].token, type_ids["CASUAL"], 2)
    assert request_count(api, people["admin"].token, department="Design", q="colleague") == 1


@pytest.mark.req("FR-07", "FR-09")
@pytest.mark.xfail(strict=True, reason="WK-06: approval does not check whether the leave already started")
def test_wk06_stale_pending_request_cannot_be_approved(api, people, type_ids, insert_request):
    employee = people["employee"]
    start = date.today() - timedelta(days=10)
    item_id = insert_request(employee.id, type_ids["CASUAL"], start, start + timedelta(days=2), 2)
    result = api.post("/api/leave-requests/{}/review".format(item_id), token=people["admin"].token,
                      body={"decision": "approve"})
    assert result.status == 409
