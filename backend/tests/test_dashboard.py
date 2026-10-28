from datetime import date, timedelta

from app.extensions import db
from app.models import LeaveRequest, utcnow
from tests.support import create_request, next_monday


def test_employee_dashboard_summarises_leave(client, employee_headers):
    response = client.get("/api/dashboard", headers=employee_headers)
    assert response.status_code == 200
    body = response.get_json()

    assert body["role"] == "employee"
    assert body["year"] == date.today().year
    assert len(body["balances"]) == 3
    assert body["stats"]["remaining_days"] == 37
    assert body["stats"]["pending_requests"] == 0
    assert body["stats"]["approved_days"] == 0
    assert body["stats"]["on_leave_today"] is False
    assert body["upcoming"] == []


def test_employee_dashboard_reflects_approved_leave(
    client, employee_headers, admin_headers, leave_types
):
    start = next_monday()
    created = create_request(
        client,
        employee_headers,
        leave_types["CASUAL"]["id"],
        start,
        start + timedelta(days=1),
    ).get_json()
    pending_dashboard = client.get(
        "/api/dashboard", headers=employee_headers
    ).get_json()
    assert pending_dashboard["stats"]["pending_requests"] == 1

    client.post(
        f"/api/leave-requests/{created['id']}/review",
        headers=admin_headers,
        json={"decision": "approve"},
    )

    body = client.get("/api/dashboard", headers=employee_headers).get_json()
    assert body["stats"]["pending_requests"] == 0
    assert body["stats"]["approved_days"] == 2
    assert body["stats"]["remaining_days"] == 35
    assert body["upcoming"][0]["id"] == created["id"]


def test_employee_dashboard_shows_recent_requests(
    client, employee_headers, leave_types
):
    start = next_monday()
    create_request(
        client, employee_headers, leave_types["SICK"]["id"], start, start
    )
    body = client.get("/api/dashboard", headers=employee_headers).get_json()
    assert len(body["recent_requests"]) == 1
    assert body["recent_requests"][0]["leave_type"]["code"] == "SICK"


def test_admin_dashboard_includes_company_overview(
    client, app, admin_headers, make_user, login_headers, leave_types
):
    employee = make_user(
        name="Meera Nair", email="meera@example.com", department="Marketing"
    )
    headers = login_headers(employee["email"])
    start = next_monday()
    create_request(
        client, headers, leave_types["EARNED"]["id"], start, start
    )

    with app.app_context():
        db.session.add(
            LeaveRequest(
                user_id=employee["id"],
                leave_type_id=leave_types["CASUAL"]["id"],
                start_date=date.today() - timedelta(days=1),
                end_date=date.today() + timedelta(days=1),
                days=3,
                reason="Recovering from a minor procedure.",
                status="approved",
                reviewed_at=utcnow(),
            )
        )
        db.session.commit()

    response = client.get("/api/dashboard", headers=admin_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["role"] == "admin"
    assert body["stats"]["headcount"] == 1
    assert body["stats"]["pending_requests"] == 1
    assert body["stats"]["on_leave_today"] == 1
    assert body["pending_requests"][0]["employee"]["name"] == "Meera Nair"
    assert body["on_leave"][0]["employee"]["name"] == "Meera Nair"
    assert body["upcoming"] == []
    assert {item["name"] for item in body["departments"]} == {"Marketing"}


def test_admin_dashboard_groups_departments(
    client, admin_headers, make_user, leave_types
):
    make_user(name="A One", email="aone@example.com", department="Engineering")
    make_user(name="B Two", email="btwo@example.com", department="Engineering")
    make_user(name="C Three", email="cthree@example.com", department="Finance")

    body = client.get("/api/dashboard", headers=admin_headers).get_json()
    departments = {item["name"]: item for item in body["departments"]}
    assert departments["Engineering"]["headcount"] == 2
    assert departments["Finance"]["headcount"] == 1


def test_team_directory_requires_admin(client, employee_headers):
    response = client.get("/api/team", headers=employee_headers)
    assert response.status_code == 403
    assert response.get_json()["message"] == "Admin access is required."


def test_team_directory_lists_employees_with_balances(
    client, admin_headers, make_user, login_headers, leave_types
):
    amit = make_user(
        name="Amit Patel",
        email="amit@example.com",
        department="Engineering",
        job_title="Backend Developer",
    )
    make_user(name="Zara Khan", email="zara@example.com", department="Sales")
    headers = login_headers(amit["email"])

    start = next_monday()
    created = create_request(
        client, headers, leave_types["SICK"]["id"], start, start
    ).get_json()
    client.post(
        f"/api/leave-requests/{created['id']}/review",
        headers=admin_headers,
        json={"decision": "approve"},
    )

    response = client.get("/api/team", headers=admin_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 2
    assert body["departments"] == ["Engineering", "Sales"]

    amit_item = next(item for item in body["items"] if item["name"] == "Amit Patel")
    assert len(amit_item["balances"]) == 3
    assert amit_item["approved_days"] == 1
    assert amit_item["on_leave_today"] is False
    assert amit_item["next_leave"]["id"] == created["id"]


def test_admin_can_view_another_employees_balances(
    client, admin_headers, make_user
):
    employee = make_user(name="Riya Sen", email="riya@example.com")
    response = client.get(
        f"/api/leave-balances?user_id={employee['id']}", headers=admin_headers
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["user"]["id"] == employee["id"]
    assert len(body["balances"]) == 3


def test_employee_cannot_view_another_employees_balances(
    client, employee_headers, make_user
):
    other = make_user(name="Riya Sen", email="riya@example.com")
    response = client.get(
        f"/api/leave-balances?user_id={other['id']}", headers=employee_headers
    )
    assert response.status_code == 403


def test_balance_endpoint_validates_year_and_user(
    client, admin_headers, employee_headers
):
    assert (
        client.get("/api/leave-balances?year=abc", headers=employee_headers).status_code
        == 400
    )
    assert (
        client.get(
            "/api/leave-balances?user_id=abc", headers=admin_headers
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/leave-balances?user_id=9999", headers=admin_headers
        ).status_code
        == 404
    )


def test_dashboard_requires_authentication(client):
    assert client.get("/api/dashboard").status_code == 401
