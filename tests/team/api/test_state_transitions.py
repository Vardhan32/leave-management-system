"""BR3 state machine of a leave request, repeated requests, and read-backs of
the shared records (request status and leave balance) after every change.

States: pending, approved, rejected, cancelled.
Allowed:   pending -> approved     (review approve)
           pending -> rejected     (review reject)
           pending -> cancelled    (cancel, before the start date)
           approved -> cancelled   (cancel, before the start date)
Everything else must be refused and must leave the record unchanged.
"""

from datetime import date, timedelta

import pytest

from support.flows import balances, cancel, next_year, read_request, request_count, review, submit, submit_days
from support.tokens import base_monday

pytestmark = pytest.mark.req("BR3", "FR-07", "FR-08", "FR-11")

DAYS = 3


def casual(api, token):
    return balances(api, token, next_year())["CASUAL"]


@pytest.fixture()
def pending(api, people, type_ids):
    return submit_days(api, people["employee"].token, type_ids["CASUAL"], DAYS).json


def move_to(state, api, people, request_id):
    employee, admin = people["employee"].token, people["admin"].token
    if state == "approved":
        review(api, admin, request_id, "approve")
    elif state == "rejected":
        review(api, admin, request_id, "reject", note="Project deadline that week.")
    elif state == "cancelled":
        cancel(api, employee, request_id)


# -- allowed transitions ------------------------------------------------------
def test_pending_to_approved(api, people, pending):
    employee = people["employee"].token
    result = review(api, people["admin"].token, pending["id"], "approve", note="Enjoy.")

    assert result.json["status"] == "approved"
    stored = read_request(api, employee, pending["id"])
    assert stored["status"] == "approved"
    assert stored["reviewed_by"]["id"] == people["admin"].id
    assert stored["reviewed_at"] is not None
    assert stored["review_note"] == "Enjoy."
    row = casual(api, employee)
    assert row["used_days"] == DAYS
    assert row["remaining_days"] == row["allocated_days"] - DAYS


def test_pending_to_rejected(api, people, pending):
    employee = people["employee"].token
    review(api, people["admin"].token, pending["id"], "reject", note="Release week.")

    stored = read_request(api, employee, pending["id"])
    assert stored["status"] == "rejected"
    assert stored["review_note"] == "Release week."
    assert casual(api, employee)["used_days"] == 0


def test_pending_to_cancelled(api, people, pending):
    employee = people["employee"].token
    cancel(api, employee, pending["id"])

    assert read_request(api, employee, pending["id"])["status"] == "cancelled"
    assert casual(api, employee)["used_days"] == 0


def test_approved_to_cancelled_returns_days(api, people, pending):
    employee = people["employee"].token
    move_to("approved", api, people, pending["id"])
    assert casual(api, employee)["used_days"] == DAYS

    cancel(api, employee, pending["id"])

    assert read_request(api, employee, pending["id"])["status"] == "cancelled"
    assert casual(api, employee)["used_days"] == 0


# -- disallowed transitions, at least one from every state ---------------------
DISALLOWED = [
    # from state, action, expected status
    ("approved", "approve", 409),
    ("approved", "reject", 409),
    ("rejected", "approve", 409),
    ("rejected", "reject", 409),
    ("rejected", "cancel", 409),
    ("cancelled", "approve", 409),
    ("cancelled", "reject", 409),
    ("cancelled", "cancel", 409),
]


@pytest.mark.parametrize("state,action,expected", DISALLOWED,
                         ids=["{}-{}".format(row[0], row[1]) for row in DISALLOWED])
def test_disallowed_transition(state, action, expected, api, people, pending):
    employee, admin = people["employee"].token, people["admin"].token
    move_to(state, api, people, pending["id"])
    before = read_request(api, employee, pending["id"])
    used_before = casual(api, employee)["used_days"]

    if action == "cancel":
        result = cancel(api, employee, pending["id"], expect=None)
    else:
        result = review(api, admin, pending["id"], action, note="Second decision.", expect=None)

    assert result.status == expected, result
    after = read_request(api, employee, pending["id"])
    assert after["status"] == before["status"] == state
    assert after["review_note"] == before["review_note"]
    assert casual(api, employee)["used_days"] == used_before


def test_pending_that_started_cannot_be_cancelled(api, people, type_ids, insert_request):
    """The disallowed change from pending: cancelling once the start date has passed."""
    employee = people["employee"]
    start = date.today() - timedelta(days=2)
    item_id = insert_request(employee.id, type_ids["CASUAL"], start, start + timedelta(days=4), 2)

    result = cancel(api, employee.token, item_id, expect=None)

    assert result.status == 409
    assert read_request(api, employee.token, item_id)["status"] == "pending"


def test_approved_that_started_cannot_be_cancelled(api, people, type_ids, insert_request):
    employee = people["employee"]
    start = date.today() - timedelta(days=2)
    item_id = insert_request(employee.id, type_ids["CASUAL"], start, start + timedelta(days=4), 2)
    review(api, people["admin"].token, item_id, "approve")
    used = balances(api, employee.token, start.year)["CASUAL"]["used_days"]

    result = cancel(api, employee.token, item_id, expect=None)

    assert result.status == 409
    assert read_request(api, employee.token, item_id)["status"] == "approved"
    assert balances(api, employee.token, start.year)["CASUAL"]["used_days"] == used


# -- repeated requests: no duplicates, no double counting ---------------------
def test_repeated_submission_is_not_duplicated(api, people, type_ids):
    employee = people["employee"].token
    start = base_monday()
    submit(api, employee, type_ids["CASUAL"], start, start + timedelta(days=2))

    again = submit(api, employee, type_ids["CASUAL"], start, start + timedelta(days=2), expect=None)

    assert again.status == 422
    assert "start_date" in again.error_fields()
    assert request_count(api, employee) == 1


def test_repeated_approval_counts_days_once(api, people, pending):
    employee, admin = people["employee"].token, people["admin"].token
    review(api, admin, pending["id"], "approve")

    again = review(api, admin, pending["id"], "approve", expect=None)

    assert again.status == 409
    assert casual(api, employee)["used_days"] == DAYS


def test_repeated_cancel_returns_days_once(api, people, pending):
    employee = people["employee"].token
    move_to("approved", api, people, pending["id"])
    cancel(api, employee, pending["id"])

    again = cancel(api, employee, pending["id"], expect=None)

    assert again.status == 409
    assert casual(api, employee)["used_days"] == 0


def test_repeated_rejection_keeps_first_note(api, people, pending):
    employee, admin = people["employee"].token, people["admin"].token
    review(api, admin, pending["id"], "reject", note="First note.")

    again = review(api, admin, pending["id"], "reject", note="Second note.", expect=None)

    assert again.status == 409
    assert read_request(api, employee, pending["id"])["review_note"] == "First note."


# -- full cross-workflow scenario ---------------------------------------------
@pytest.mark.req("BR1", "BR3", "FR-05", "FR-09")
def test_balance_flows_between_workflows(api, people, type_ids):
    """Approve uses days, cancel returns them, and W1 sees the change at once."""
    employee, admin = people["employee"].token, people["admin"].token
    base = base_monday()
    allocation = casual(api, employee)["allocated_days"]

    # W1: a request that takes all but two days
    big = submit_days(api, employee, type_ids["CASUAL"], allocation - 2, start=base).json
    # W2: approve it
    review(api, admin, big["id"], "approve")
    assert casual(api, employee)["remaining_days"] == 2

    # W1 now reads the smaller balance: three days is too many, two is fine
    later = base + timedelta(weeks=8)
    too_many = submit_days(api, employee, type_ids["CASUAL"], 3, start=later, expect=422)
    assert "leave_type_id" in too_many.error_fields()
    submit_days(api, employee, type_ids["CASUAL"], 2, start=later, expect=201)

    # W2 cancel of the big request gives the days back to W1
    cancel(api, employee, big["id"])
    assert casual(api, employee)["remaining_days"] == allocation
