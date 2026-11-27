"""Authentication and role checks on every endpoint in the spec (FR-12),
plus the read endpoints the two workflows rely on (FR-06).
"""

from datetime import timedelta

import pytest

from support.flows import balances, next_year, read_request, request_count, submit_days

PROTECTED = [
    ("GET", "/api/auth/me"),
    ("GET", "/api/leave-types"),
    ("GET", "/api/leave-balances"),
    ("GET", "/api/leave-requests"),
    ("POST", "/api/leave-requests"),
    ("GET", "/api/leave-requests/1"),
    ("POST", "/api/leave-requests/1/cancel"),
    ("POST", "/api/leave-requests/1/review"),
]
IDS = ["{} {}".format(method, path) for method, path in PROTECTED]


def send(api, method, path, token=None, raw_header=None):
    headers = {"Authorization": raw_header} if raw_header else None
    if method == "GET":
        return api.get(path, token=token, headers=headers)
    return api.post(path, token=token, body={}, headers=headers)


@pytest.mark.req("FR-12")
def test_health_needs_no_token(api):
    result = api.get("/api/health")
    assert result.status == 200
    assert result.json == {"status": "ok"}


@pytest.mark.req("FR-12")
@pytest.mark.parametrize("method,path", PROTECTED, ids=IDS)
def test_missing_token_is_401(method, path, api):
    result = send(api, method, path)
    assert result.status == 401
    assert result.json["message"] == "Authentication required."


@pytest.mark.req("FR-12")
@pytest.mark.parametrize("method,path", PROTECTED, ids=IDS)
def test_malformed_token_is_401(method, path, api):
    result = send(api, method, path, raw_header="Bearer not.a.real-token")
    assert result.status == 401


@pytest.mark.req("FR-12")
def test_expired_token_is_401(app, api, people):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(identity=str(people["employee"].id),
                                    expires_delta=timedelta(seconds=-60))
    result = api.get("/api/auth/me", token=token)
    assert result.status == 401
    assert "expired" in result.json["message"]


@pytest.mark.req("FR-12")
def test_token_of_deactivated_user_is_401(app, api, people):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        db.session.get(User, people["employee"].id).is_active = False
        db.session.commit()
    # /me looks the user up on every call; see WK-08 for endpoints that do not
    result = api.get("/api/auth/me", token=people["employee"].token)
    assert result.status == 401


@pytest.mark.req("FR-12")
def test_me_returns_signed_in_user(api, people):
    result = api.get("/api/auth/me", token=people["admin"].token)
    assert result.status == 200
    assert result.json["user"]["role"] == "admin"


@pytest.mark.req("FR-12")
def test_login_email_is_case_insensitive(api, people):
    result = api.post("/api/auth/login",
                      body={"email": people["employee"].email.upper(), "password": "password123"})
    assert result.status == 200


@pytest.mark.req("FR-12")
def test_login_wrong_password_is_401(api, people):
    result = api.post("/api/auth/login",
                      body={"email": people["employee"].email, "password": "password124"})
    assert result.status == 401
    assert result.json["message"] == "Incorrect email or password."


# -- balances -------------------------------------------------------------------
@pytest.mark.req("FR-06", "FR-12")
def test_employee_cannot_read_another_balance(api, people):
    result = api.get("/api/leave-balances", token=people["employee"].token,
                     query={"user_id": str(people["colleague"].id)})
    assert result.status == 403


@pytest.mark.req("FR-06")
def test_admin_reads_any_balance(api, people):
    rows = balances(api, people["admin"].token, next_year(), user_id=people["colleague"].id)
    assert {code: row["allocated_days"] for code, row in rows.items()} == \
        {"CASUAL": 12, "SICK": 10, "EARNED": 15}


@pytest.mark.req("FR-06")
def test_admin_unknown_user_balance_is_404(api, people):
    result = api.get("/api/leave-balances", token=people["admin"].token,
                     query={"user_id": "999999"})
    assert result.status == 404


@pytest.mark.req("FR-06")
def test_balance_defaults_to_current_year(api, people):
    from datetime import date

    result = api.get("/api/leave-balances", token=people["employee"].token)
    assert result.status == 200
    assert result.json["year"] == date.today().year


# -- request visibility -------------------------------------------------------
@pytest.fixture()
def two_requests(api, people, type_ids):
    mine = submit_days(api, people["employee"].token, type_ids["CASUAL"], 2).json
    theirs = submit_days(api, people["colleague"].token, type_ids["SICK"], 1).json
    return mine, theirs


@pytest.mark.req("FR-06", "FR-12")
def test_employee_lists_only_own_requests(api, people, two_requests):
    mine, theirs = two_requests
    result = api.get("/api/leave-requests", token=people["employee"].token,
                     query={"user_id": str(people["colleague"].id)})
    # user_id is an admin-only filter and must be ignored for employees
    assert result.status == 200
    assert [item["id"] for item in result.json["items"]] == [mine["id"]]


@pytest.mark.req("FR-06", "FR-12")
def test_employee_cannot_open_another_request(api, people, two_requests):
    _, theirs = two_requests
    result = api.get("/api/leave-requests/{}".format(theirs["id"]), token=people["employee"].token)
    # 404 instead of 403, so ids of other people's requests are not confirmed
    assert result.status == 404


@pytest.mark.req("FR-06")
def test_admin_sees_and_filters_everything(api, people, two_requests):
    mine, theirs = two_requests
    admin = people["admin"].token
    assert request_count(api, admin) == 2
    assert request_count(api, admin, department="Design") == 1
    assert request_count(api, admin, user_id=people["employee"].id) == 1
    assert request_count(api, admin, q="colleague@leavedesk") == 1
    assert read_request(api, admin, theirs["id"])["employee"]["id"] == people["colleague"].id


@pytest.mark.req("FR-06")
def test_filters_by_status_type_and_year(api, people, two_requests):
    admin = people["admin"].token
    assert request_count(api, admin, status="pending") == 2
    assert request_count(api, admin, status="approved") == 0
    assert request_count(api, admin, leave_type_id=2) == 1
    assert request_count(api, admin, year=next_year()) == 2
    assert request_count(api, admin, year=next_year() + 1) == 0


@pytest.mark.req("FR-11", "FR-12")
def test_admin_cannot_cancel_for_an_employee(api, people, two_requests):
    mine, _ = two_requests
    result = api.post("/api/leave-requests/{}/cancel".format(mine["id"]), token=people["admin"].token)
    assert result.status == 403
    assert read_request(api, people["employee"].token, mine["id"])["status"] == "pending"


@pytest.mark.req("FR-10")
def test_review_unknown_request_is_404(api, people):
    result = api.post("/api/leave-requests/999999/review", token=people["admin"].token,
                      body={"decision": "approve"})
    assert result.status == 404
