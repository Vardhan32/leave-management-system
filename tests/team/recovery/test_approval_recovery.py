"""Controlled failure and recovery of state-changing operations.

The fault is a test double for the database: the first commit raises the
error SQLite gives when the file is locked or unavailable. The code under
test is the real application. Each test follows the same order:

1. record the state before
2. make the write fail once and check what was persisted
3. remove the fault, retry, and check the final state has no duplicates
"""

from datetime import date, timedelta

import pytest
from sqlalchemy.exc import OperationalError

from app.extensions import db


def next_year_monday(weeks_after=0):
    day = date(date.today().year + 1, 3, 1)
    while day.weekday() != 0:
        day += timedelta(days=1)
    return day + timedelta(weeks=weeks_after)


class FlakyCommit:
    """Replaces db.session.commit: fails the first `failures` calls, then works."""

    def __init__(self, real_commit, failures=1):
        self.real_commit = real_commit
        self.failures_left = failures
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.failures_left > 0:
            self.failures_left -= 1
            raise OperationalError("COMMIT", {}, Exception("database is locked"))
        return self.real_commit()


@pytest.fixture()
def db_fault(monkeypatch):
    """Install the fault and return it; monkeypatch removes it after the test."""

    def install(failures=1):
        fault = FlakyCommit(db.session.commit, failures)
        monkeypatch.setattr(db.session, "commit", fault)
        return fault

    def remove():
        monkeypatch.undo()

    install.remove = remove
    return install


@pytest.fixture()
def pending_request(api, people, type_ids):
    """An employee's pending request of 3 working days (Casual)."""
    start = next_year_monday()
    end = start + timedelta(days=2)
    result = api.post(
        "/api/leave-requests",
        token=people["employee"].token,
        body={
            "leave_type_id": type_ids["CASUAL"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "reason": "Setup request for the recovery test",
        },
    )
    assert result.status == 201, result
    return result.json


def used_days(api, people, who, year):
    result = api.get("/api/leave-balances", token=people[who].token, query={"year": year})
    return next(b["used_days"] for b in result.json["balances"] if b["leave_type"]["code"] == "CASUAL")


def requests_of(api, people, who):
    result = api.get("/api/leave-requests", token=people[who].token, query={"per_page": 50})
    return result.json["items"]


def test_approval_survives_a_failed_commit(app, api, people, pending_request, db_fault):
    """Review fails once at commit; nothing is saved; the retry approves exactly once."""
    request_id = pending_request["id"]
    year = int(pending_request["start_date"][:4])
    admin = people["admin"].token
    before_used = used_days(api, people, "employee", year)
    before_count = len(requests_of(api, people, "employee"))
    assert (before_used, before_count) == (0, 1)

    # step 2: the write fails. With TESTING on, Flask hands the exception to the
    # test instead of turning it into an HTTP 500, so the test catches it.
    fault = db_fault(failures=1)
    with pytest.raises(OperationalError):
        api.post(f"/api/leave-requests/{request_id}/review", token=admin,
                 body={"decision": "approve", "note": "first attempt"})
    assert fault.calls == 1

    stored = api.get(f"/api/leave-requests/{request_id}", token=admin).json
    assert stored["status"] == "pending"
    assert stored["reviewed_by"] is None and stored["review_note"] is None
    assert used_days(api, people, "employee", year) == before_used
    assert len(requests_of(api, people, "employee")) == before_count

    # step 3: the dependency is back; the same request is sent again
    retry = api.post(f"/api/leave-requests/{request_id}/review", token=admin,
                     body={"decision": "approve", "note": "second attempt"})
    assert retry.status == 200
    assert retry.json["status"] == "approved"
    assert retry.json["review_note"] == "second attempt"
    assert used_days(api, people, "employee", year) == before_used + pending_request["days"]
    assert len(requests_of(api, people, "employee")) == before_count  # no duplicate record


def test_failed_commit_is_reported_as_http_500(app, people, pending_request, db_fault):
    """What a browser would see when the write fails: a 500 and no change."""
    app.config["PROPAGATE_EXCEPTIONS"] = False
    client = app.test_client()
    headers = {"Authorization": "Bearer " + people["admin"].token}
    db_fault(failures=1)
    reply = client.post(
        f"/api/leave-requests/{pending_request['id']}/review",
        json={"decision": "approve"},
        headers=headers,
    )
    assert reply.status_code == 500

    db_fault.remove()
    stored = client.get(f"/api/leave-requests/{pending_request['id']}", headers=headers).get_json()
    assert stored["status"] == "pending"


def test_a_second_retry_cannot_double_count(api, people, pending_request, db_fault):
    """Retrying an approval that already succeeded is refused, so used_days grows once."""
    request_id = pending_request["id"]
    year = int(pending_request["start_date"][:4])
    admin = people["admin"].token

    db_fault(failures=1)
    with pytest.raises(OperationalError):
        api.post(f"/api/leave-requests/{request_id}/review", token=admin, body={"decision": "approve"})
    db_fault.remove()

    first = api.post(f"/api/leave-requests/{request_id}/review", token=admin, body={"decision": "approve"})
    again = api.post(f"/api/leave-requests/{request_id}/review", token=admin, body={"decision": "approve"})
    assert first.status == 200
    assert again.status == 409
    assert used_days(api, people, "employee", year) == pending_request["days"]


def test_create_survives_a_failed_commit_without_duplicates(api, people, type_ids, db_fault):
    """Applying fails once at commit; no row is saved; the retry stores exactly one."""
    start = next_year_monday(weeks_after=2)
    body = {
        "leave_type_id": type_ids["EARNED"],
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=1)).isoformat(),
        "reason": "Request sent while the database fails",
    }
    employee = people["employee"].token
    assert requests_of(api, people, "employee") == []

    db_fault(failures=1)
    with pytest.raises(OperationalError):
        api.post("/api/leave-requests", token=employee, body=body)
    assert requests_of(api, people, "employee") == []  # nothing persisted

    db_fault.remove()
    retry = api.post("/api/leave-requests", token=employee, body=body)
    assert retry.status == 201
    items = requests_of(api, people, "employee")
    assert len(items) == 1 and items[0]["id"] == retry.json["id"]

    # sending the same body once more is a duplicate and is refused
    repeat = api.post("/api/leave-requests", token=employee, body=body)
    assert repeat.status == 422
    assert len(requests_of(api, people, "employee")) == 1
