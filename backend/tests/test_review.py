from datetime import timedelta

from app.extensions import db
from app.models import LeaveBalance
from tests.support import create_request, next_monday


def make_pending(client, headers, leave_types, days=4, code="CASUAL"):
    start = next_monday()
    return create_request(
        client,
        headers,
        leave_types[code]["id"],
        start,
        start + timedelta(days=days),
    ).get_json()


def test_admin_approves_request_and_updates_balance(
    client, employee_headers, admin_headers, leave_types
):
    request = make_pending(client, employee_headers, leave_types)

    response = client.post(
        f"/api/leave-requests/{request['id']}/review",
        headers=admin_headers,
        json={"decision": "approve", "note": "Enjoy the break."},
    )
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["status"] == "approved"
    assert body["reviewed_by"]["name"] == "Test Admin"
    assert body["reviewed_at"] is not None
    assert body["review_note"] == "Enjoy the break."

    balances = client.get(
        "/api/leave-balances", headers=employee_headers
    ).get_json()["balances"]
    casual = next(
        item for item in balances if item["leave_type"]["code"] == "CASUAL"
    )
    assert casual["used_days"] == 5
    assert casual["remaining_days"] == 7


def test_employee_cannot_review_requests(
    client, employee_headers, leave_types
):
    request = make_pending(client, employee_headers, leave_types)
    response = client.post(
        f"/api/leave-requests/{request['id']}/review",
        headers=employee_headers,
        json={"decision": "approve"},
    )
    assert response.status_code == 403
    assert response.get_json()["message"] == "Admin access is required."


def test_rejection_requires_a_note(
    client, employee_headers, admin_headers, leave_types
):
    request = make_pending(client, employee_headers, leave_types)

    missing_note = client.post(
        f"/api/leave-requests/{request['id']}/review",
        headers=admin_headers,
        json={"decision": "reject"},
    )
    assert missing_note.status_code == 422
    assert "note" in missing_note.get_json()["errors"]


def test_admin_can_reject_with_a_note(
    client, employee_headers, admin_headers, leave_types
):
    request = make_pending(client, employee_headers, leave_types)
    response = client.post(
        f"/api/leave-requests/{request['id']}/review",
        headers=admin_headers,
        json={"decision": "reject", "note": "Sprint release that week."},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "rejected"
    assert body["review_note"] == "Sprint release that week."

    balances = client.get(
        "/api/leave-balances", headers=employee_headers
    ).get_json()["balances"]
    casual = next(
        item for item in balances if item["leave_type"]["code"] == "CASUAL"
    )
    assert casual["used_days"] == 0


def test_review_validates_decision(
    client, employee_headers, admin_headers, leave_types
):
    request = make_pending(client, employee_headers, leave_types)
    response = client.post(
        f"/api/leave-requests/{request['id']}/review",
        headers=admin_headers,
        json={"decision": "maybe"},
    )
    assert response.status_code == 422
    assert "decision" in response.get_json()["errors"]


def test_admin_cannot_review_own_request(
    client, admin_headers, leave_types
):
    start = next_monday()
    created = create_request(
        client, admin_headers, leave_types["CASUAL"]["id"], start, start
    ).get_json()

    response = client.post(
        f"/api/leave-requests/{created['id']}/review",
        headers=admin_headers,
        json={"decision": "approve"},
    )
    assert response.status_code == 403
    assert "your own" in response.get_json()["message"]


def test_only_pending_requests_can_be_reviewed(
    client, employee_headers, admin_headers, leave_types
):
    request = make_pending(client, employee_headers, leave_types)
    first = client.post(
        f"/api/leave-requests/{request['id']}/review",
        headers=admin_headers,
        json={"decision": "approve"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/leave-requests/{request['id']}/review",
        headers=admin_headers,
        json={"decision": "reject", "note": "Changed my mind."},
    )
    assert second.status_code == 409


def test_review_rejects_unknown_request(client, admin_headers):
    response = client.post(
        "/api/leave-requests/9999/review",
        headers=admin_headers,
        json={"decision": "approve"},
    )
    assert response.status_code == 404


def test_approval_checks_current_balance(
    client, app, make_user, login_headers, admin_headers, leave_types
):
    employee = make_user(name="Kiran Das", email="kiran@example.com")
    headers = login_headers(employee["email"])
    request = make_pending(client, headers, leave_types)

    with app.app_context():
        balance = LeaveBalance.query.filter_by(
            user_id=employee["id"],
            leave_type_id=leave_types["CASUAL"]["id"],
        ).first()
        balance.allocated_days = 2
        db.session.commit()

    response = client.post(
        f"/api/leave-requests/{request['id']}/review",
        headers=admin_headers,
        json={"decision": "approve"},
    )
    assert response.status_code == 422
    assert "Only 2 day(s)" in response.get_json()["errors"]["leave_type_id"]

    detail = client.get(
        f"/api/leave-requests/{request['id']}", headers=headers
    ).get_json()
    assert detail["status"] == "pending"
