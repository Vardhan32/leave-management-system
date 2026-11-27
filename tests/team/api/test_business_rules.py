"""Business rules through the API: BVA on BR1, decision tables for BR2 and
the cancellation rule, BVA on BR4 (overlap) and the date rules of FR-03.

BR1 values come from the generator (x-business-rules in the spec). The other
tables are written out here because they combine several requests and roles,
which the generator does not model.
"""

from datetime import date, timedelta

import pytest

from support.flows import (
    balances,
    cancel,
    next_year,
    read_request,
    request_count,
    review,
    submit,
    submit_days,
)
from support.generated import cases_where
from support.tokens import add_working_days, base_monday


def rule_params(operation):
    return [
        pytest.param(case, id=case["id"], marks=pytest.mark.req("BR1", "FR-05", "FR-09"))
        for case in cases_where(location="rule", operation=operation)
    ]


# -- BR1: balance limit at submission ----------------------------------------
@pytest.mark.parametrize("case", rule_params("createLeaveRequest"))
def test_br1_balance_limit_on_submission(case, api, people, type_ids):
    employee = people["employee"].token
    code = case["leave_type_code"]
    days = case["value"]["working_days"]

    result = submit_days(api, employee, type_ids[code], days, expect=None)

    assert result.status == case["expected_status"], (case["partition"], result)
    row = balances(api, employee, next_year())[code]
    assert row["allocated_days"] == case["allocation"]
    # submission never touches used_days, accepted or not
    assert row["used_days"] == 0
    if result.status == 201:
        assert result.json["days"] == days
        assert request_count(api, employee) == 1
    else:
        assert case["expected_error_field"] in result.error_fields()
        assert request_count(api, employee) == 0


# -- BR1: balance re-checked at approval (cross-workflow) --------------------
@pytest.mark.parametrize("case", rule_params("reviewLeaveRequest"))
def test_br1_balance_rechecked_on_approval(case, api, people, type_ids):
    """W1 creates two pending requests, W2 approves the first, then reviews the second.

    The first approval changes LeaveBalance.used_days, which the second review
    reads. This is the shared record between the two workflows.
    """
    employee, admin = people["employee"].token, people["admin"].token
    code = case["leave_type_code"]
    prior_days = case["value"]["prior_days"]
    need = case["value"]["request_days"]
    start = base_monday()

    # both requests fit the full balance when submitted
    first = submit_days(api, employee, type_ids[code], prior_days, start=start).json
    second_start = start + timedelta(weeks=6)
    second = submit_days(api, employee, type_ids[code], need, start=second_start).json
    review(api, admin, first["id"], "approve")

    result = review(api, admin, second["id"], "approve", expect=None)

    assert result.status == case["expected_status"], (case["partition"], result)
    row = balances(api, employee, next_year())[code]
    stored = read_request(api, employee, second["id"])
    if result.status == 200:
        assert stored["status"] == "approved"
        assert row["used_days"] == prior_days + need
    else:
        assert case["expected_error_field"] in result.error_fields()
        assert stored["status"] == "pending"
        assert row["used_days"] == prior_days


# -- BR2: who may review what -------------------------------------------------
# C1 reviewer is admin, C2 request is pending, C3 reviewer is not the requester
REVIEW_TABLE = [
    # id     C1     C2     C3     expected
    ("R1", True, True, True, 200),
    ("R2", True, True, False, 403),
    ("R3", True, False, True, 409),
    ("R4", True, False, False, 409),
    ("R5", False, True, True, 403),
    ("R6", False, True, False, 403),
    ("R7", False, False, True, 403),
    ("R8", False, False, False, 403),
]


@pytest.mark.req("BR2", "FR-10")
@pytest.mark.parametrize("rule_id,is_admin,is_pending,not_own,expected", REVIEW_TABLE,
                         ids=[row[0] for row in REVIEW_TABLE])
def test_br2_review_decision_table(rule_id, is_admin, is_pending, not_own, expected,
                                   api, people, type_ids):
    reviewer = people["admin"] if is_admin else people["employee"]
    if not_own:
        # someone other than the reviewer owns the request
        owner = people["colleague"]
    else:
        owner = reviewer
    item = submit_days(api, owner.token, type_ids["CASUAL"], 2).json
    if not is_pending:
        # move it out of pending without a review, so C1 and C3 stay as set
        cancel(api, owner.token, item["id"])

    result = review(api, reviewer.token, item["id"], "approve", expect=None)

    assert result.status == expected, (rule_id, result)
    stored = read_request(api, owner.token, item["id"])
    assert stored["status"] == ("approved" if expected == 200 else
                                "pending" if is_pending else "cancelled")


# decision x note: a rejection needs a note, an approval does not
NOTE_TABLE = [
    ("N1", "approve", "Have a good break.", 200, "approved"),
    ("N2", "approve", None, 200, "approved"),
    ("N3", "reject", "Team is short-staffed that week.", 200, "rejected"),
    ("N4", "reject", None, 422, "pending"),
    ("N5", "reject", "    ", 422, "pending"),
]


@pytest.mark.req("BR2", "FR-07", "FR-08")
@pytest.mark.parametrize("rule_id,decision,note,expected,final_status", NOTE_TABLE,
                         ids=[row[0] for row in NOTE_TABLE])
def test_br2_rejection_needs_note(rule_id, decision, note, expected, final_status,
                                  api, people, type_ids):
    employee, admin = people["employee"].token, people["admin"].token
    item = submit_days(api, employee, type_ids["CASUAL"], 3).json

    result = review(api, admin, item["id"], decision, note=note, expect=None)

    assert result.status == expected, (rule_id, result)
    if expected == 422:
        assert "note" in result.error_fields()
    stored = read_request(api, employee, item["id"])
    assert stored["status"] == final_status
    used = balances(api, employee, next_year())["CASUAL"]["used_days"]
    assert used == (3 if final_status == "approved" else 0)
    if final_status == "rejected":
        assert stored["review_note"] == note


# -- cancellation rule: owner AND (pending or approved) AND not started -------
# C1 caller owns the request, C2 status is pending/approved, C3 start is after today
CANCEL_TABLE = [
    ("C1", True, True, True, 200),
    ("C2", True, True, False, 409),
    ("C3", True, False, True, 409),
    ("C4", True, False, False, 409),
    ("C5", False, True, True, 403),
    ("C6", False, True, False, 403),
    ("C7", False, False, True, 403),
    ("C8", False, False, False, 403),
]


@pytest.mark.req("BR3", "FR-11")
@pytest.mark.parametrize("rule_id,is_owner,is_open,in_future,expected", CANCEL_TABLE,
                         ids=[row[0] for row in CANCEL_TABLE])
def test_cancel_decision_table(rule_id, is_owner, is_open, in_future, expected,
                               api, people, type_ids, insert_request):
    owner = people["employee"]
    caller = owner if is_owner else people["colleague"]
    admin = people["admin"].token
    if in_future:
        start = base_monday()
        item_id = submit_days(api, owner.token, type_ids["CASUAL"], 2, start=start).json["id"]
    else:
        # started yesterday; the API refuses past dates, so it is stored directly
        start = date.today() - timedelta(days=1)
        item_id = insert_request(owner.id, type_ids["CASUAL"], start, start + timedelta(days=3), 2)
    if not is_open:
        review(api, admin, item_id, "reject", note="Closed before the cancel attempt.")

    result = cancel(api, caller.token, item_id, expect=None)

    assert result.status == expected, (rule_id, result)
    stored = read_request(api, owner.token, item_id)
    if expected == 200:
        assert stored["status"] == "cancelled"
    else:
        assert stored["status"] == ("pending" if is_open else "rejected")


# -- BR4: overlap boundaries --------------------------------------------------
# existing request runs Monday..Wednesday (base .. base+2)
OVERLAP_TABLE = [
    ("O1 new ends the day before existing starts", -3, -1, 201),
    ("O2 new ends on the day existing starts", -3, 0, 422),
    ("O3 new ends the day after existing starts", -3, 1, 422),
    ("O4 new starts the day before existing ends", 1, 4, 422),
    ("O5 new starts on the day existing ends", 2, 4, 422),
    ("O6 new starts the day after existing ends", 3, 4, 201),
]


@pytest.mark.req("BR4", "FR-04")
@pytest.mark.parametrize("label,start_offset,end_offset,expected", OVERLAP_TABLE,
                         ids=[row[0].split()[0] for row in OVERLAP_TABLE])
def test_br4_overlap_boundaries(label, start_offset, end_offset, expected, api, people, type_ids):
    employee = people["employee"].token
    base = base_monday()
    submit(api, employee, type_ids["CASUAL"], base, base + timedelta(days=2))

    result = submit(api, employee, type_ids["SICK"], base + timedelta(days=start_offset),
                    base + timedelta(days=end_offset), expect=None)

    assert result.status == expected, (label, result)
    if expected == 422:
        assert "start_date" in result.error_fields()
    assert request_count(api, employee) == (2 if expected == 201 else 1)


@pytest.mark.req("BR4", "FR-04")
@pytest.mark.parametrize("closing", ["reject", "cancel"])
def test_br4_closed_requests_do_not_block(closing, api, people, type_ids):
    employee, admin = people["employee"].token, people["admin"].token
    base = base_monday()
    first = submit(api, employee, type_ids["CASUAL"], base, base + timedelta(days=2)).json
    if closing == "reject":
        review(api, admin, first["id"], "reject", note="Not this week.")
    else:
        cancel(api, employee, first["id"])

    submit(api, employee, type_ids["CASUAL"], base, base + timedelta(days=2), expect=201)


@pytest.mark.req("BR4", "FR-04", "FR-12")
def test_br4_overlap_is_per_employee(api, people, type_ids):
    base = base_monday()
    submit(api, people["employee"].token, type_ids["CASUAL"], base, base + timedelta(days=2))
    submit(api, people["colleague"].token, type_ids["CASUAL"], base, base + timedelta(days=2),
           expect=201)


# -- FR-03: date rules and their order ---------------------------------------
@pytest.mark.req("FR-03")
def test_dates_reversed_range(api, people, type_ids):
    base = base_monday()
    result = submit(api, people["employee"].token, type_ids["CASUAL"], base + timedelta(days=2),
                    base, expect=422)
    assert result.error_fields() == {"end_date"}


@pytest.mark.req("FR-03")
def test_dates_cross_year(api, people, type_ids):
    start = date(next_year(), 12, 28)
    result = submit(api, people["employee"].token, type_ids["CASUAL"], start,
                    date(next_year() + 1, 1, 4), expect=422)
    assert result.error_fields() == {"end_date"}
    assert "calendar years" in result.json["errors"]["end_date"]


@pytest.mark.req("FR-03")
def test_dates_weekend_only(api, people, type_ids):
    saturday = base_monday() + timedelta(days=5)
    result = submit(api, people["employee"].token, type_ids["CASUAL"], saturday,
                    saturday + timedelta(days=1), expect=422)
    assert result.error_fields() == {"end_date"}
    assert "working days" in result.json["errors"]["end_date"]


@pytest.mark.req("FR-03")
def test_dates_weekend_is_not_counted(api, people, type_ids):
    # Friday to the following Monday is two working days
    friday = base_monday() + timedelta(days=4)
    result = submit(api, people["employee"].token, type_ids["CASUAL"], friday,
                    friday + timedelta(days=3))
    assert result.json["days"] == 2


@pytest.mark.req("FR-03")
def test_dates_reversed_range_is_reported_before_past_start(api, people, type_ids):
    # both rules are broken; only the first check in validate_leave_window reports
    today = date.today()
    result = submit(api, people["employee"].token, type_ids["CASUAL"], today - timedelta(days=3),
                    today - timedelta(days=5), expect=422)
    assert result.error_fields() == {"end_date"}


@pytest.mark.req("FR-03", "FR-05")
def test_dates_checked_before_balance(api, people, type_ids):
    # 20 working days would also break BR1, but the past start is reported instead
    start = date.today() - timedelta(days=1)
    end = add_working_days(start if start.weekday() < 5 else start + timedelta(days=2), 20)
    if end.year != start.year:
        pytest.skip("range crosses the year end on this run date")
    result = submit(api, people["employee"].token, type_ids["CASUAL"], start, end, expect=422)
    assert result.error_fields() == {"start_date"}
