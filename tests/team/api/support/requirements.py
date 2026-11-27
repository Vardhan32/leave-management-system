"""Requirement and business-rule ids used to tag tests for the traceability matrix.

These ids follow the test basis in tests/team/api/README.md. If the group
renumbers the requirements in the shared test plan, change them here only.
"""

FUNCTIONAL = {
    "FR-01": "Employee submits a leave request (type, start, end, reason); it is stored as pending with its working-day count.",
    "FR-02": "Submitted fields are validated (type exists, ISO dates, reason 10-500 characters) and field errors come back as 422.",
    "FR-03": "Requests that start in the past, end before they start, span two years or contain no weekday are rejected.",
    "FR-04": "A request may not overlap the employee's own pending or approved request.",
    "FR-05": "A request may not exceed the remaining balance of its leave type.",
    "FR-06": "Employees can read their own balances and requests, with filters and pagination.",
    "FR-07": "An admin approves a pending request; used days grow by the request's days and the reviewer, time and note are stored.",
    "FR-08": "An admin rejects a pending request with a required note; the balance does not change.",
    "FR-09": "Approval re-checks the balance and refuses the request if too few days remain.",
    "FR-10": "Only admins review, an admin cannot review their own request, and only pending requests can be reviewed.",
    "FR-11": "An employee cancels their own pending request or approved request that has not started; approved days are returned.",
    "FR-12": "Every leave endpoint needs a valid token, and employees only see their own records.",
}

BUSINESS_RULES = {
    "BR1": "Boundary: working days requested <= remaining balance (Casual 12, Sick 10, Earned 15 per year).",
    "BR2": "Decision: a review is allowed only if the reviewer is an admin AND the request is pending AND the reviewer is not the requester; a rejection also needs a note.",
    "BR3": "State change: pending -> approved | rejected | cancelled; approved -> cancelled only before the start date; rejected and cancelled are final.",
    "BR4": "No overlap: a new request may not overlap the same employee's pending or approved request.",
}

# which requirement each generated operation exercises
OPERATION_REQS = {
    "login": ("FR-12",),
    "health": (),
    "me": ("FR-12",),
    "listLeaveTypes": ("FR-06",),
    "listBalances": ("FR-06",),
    "listLeaveRequests": ("FR-06",),
    "createLeaveRequest": ("FR-01", "FR-02"),
    "getLeaveRequest": ("FR-06",),
    "cancelLeaveRequest": ("FR-11", "BR3"),
    "reviewLeaveRequest": ("FR-07", "FR-08", "FR-10"),
}
