"""Small building blocks that several test modules use to reach a starting state."""

from datetime import date, timedelta

from .generated import load_cases
from .tokens import add_working_days, base_monday, resolve_body


def baseline(operation_id):
    """A fresh copy of the generator's baseline body for an operation."""
    return dict(load_cases()["baselines"][operation_id])


def leave_body(leave_type_id, start, end, reason="Family event and travel arrangements."):
    return {
        "leave_type_id": leave_type_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "reason": reason,
    }


def submit(api, token, leave_type_id, start, end, expect=201):
    result = api.post("/api/leave-requests", token=token,
                      body=leave_body(leave_type_id, start, end))
    if expect is not None:
        assert result.status == expect, result
    return result


def submit_days(api, token, leave_type_id, working_days, start=None, expect=201):
    """Submit a request holding exactly working_days weekdays."""
    start = start or base_monday()
    end = add_working_days(start, working_days)
    return submit(api, token, leave_type_id, start, end, expect=expect)


def submit_baseline(api, token):
    """Submit the generator's baseline request (three weekdays next March)."""
    body = resolve_body(baseline("createLeaveRequest"))
    result = api.post("/api/leave-requests", token=token, body=body)
    assert result.status == 201, result
    return result.json


def review(api, token, request_id, decision="approve", note="Reviewed by the test suite.", expect=200):
    body = {"decision": decision}
    if note is not None:
        body["note"] = note
    result = api.post("/api/leave-requests/{}/review".format(request_id), token=token, body=body)
    if expect is not None:
        assert result.status == expect, result
    return result


def cancel(api, token, request_id, expect=200):
    result = api.post("/api/leave-requests/{}/cancel".format(request_id), token=token)
    if expect is not None:
        assert result.status == expect, result
    return result


def read_request(api, token, request_id):
    result = api.get("/api/leave-requests/{}".format(request_id), token=token)
    assert result.status == 200, result
    return result.json


def balances(api, token, year, user_id=None):
    """Balance rows keyed by leave type code."""
    query = {"year": str(year)}
    if user_id is not None:
        query["user_id"] = str(user_id)
    result = api.get("/api/leave-balances", token=token, query=query)
    assert result.status == 200, result
    return {row["leave_type"]["code"]: row for row in result.json["balances"]}


def request_count(api, token, **filters):
    query = {key: str(value) for key, value in filters.items()}
    result = api.get("/api/leave-requests", token=token, query=query)
    assert result.status == 200, result
    return result.json["total"]


def next_year():
    return date.today().year + 1


def later(start, weeks):
    """Same weekday, a number of weeks later. Keeps test requests apart."""
    return start + timedelta(weeks=weeks)
