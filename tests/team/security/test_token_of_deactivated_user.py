"""WK-08: a token keeps working after the account is deactivated.

Control under review: "an account that is switched off can no longer use the API".
Source: backend/app/utils.py `current_user()` checks `is_active`, but endpoints that
only use `@jwt_required()` and never call `current_user()` do not.

The first test records what the application does today (the token still works on
`/api/leave-types`). The second states the expected behaviour and is an expected
failure until the endpoint checks the account.
"""

import pytest

from app.extensions import db
from app.models import User


@pytest.fixture()
def deactivated_employee(app, people):
    with app.app_context():
        user = db.session.get(User, people["employee"].id)
        user.is_active = False
        db.session.commit()
    return people["employee"]


def test_endpoints_that_load_the_user_reject_a_deactivated_token(api, deactivated_employee):
    me = api.get("/api/auth/me", token=deactivated_employee.token)
    requests_list = api.get("/api/leave-requests", token=deactivated_employee.token)
    assert me.status == 401
    assert requests_list.status == 401


def test_wk08_observed_leave_types_still_answers_for_a_deactivated_token(api, deactivated_employee):
    reply = api.get("/api/leave-types", token=deactivated_employee.token)
    assert reply.status == 200  # the weakness: this should be 401


@pytest.mark.xfail(strict=True, reason="WK-08: /api/leave-types does not check is_active")
def test_wk08_expected_deactivated_token_is_rejected_everywhere(api, deactivated_employee):
    reply = api.get("/api/leave-types", token=deactivated_employee.token)
    assert reply.status == 401


def test_login_refuses_a_deactivated_account(api, app, people):
    with app.app_context():
        user = db.session.get(User, people["employee"].id)
        user.is_active = False
        db.session.commit()
    reply = api.post("/api/auth/login", body={"email": people["employee"].email, "password": "password123"})
    assert reply.status == 401
