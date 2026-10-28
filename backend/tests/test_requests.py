from datetime import date, timedelta

from tests.support import create_request, future_year_start, next_monday, next_saturday


def balance_map(client, headers):
    body = client.get("/api/leave-balances", headers=headers).get_json()
    return {
        item["leave_type"]["code"]: item for item in body["balances"]
    }


def test_list_leave_types(client, employee_headers):
    response = client.get("/api/leave-types", headers=employee_headers)
    assert response.status_code == 200
    types = response.get_json()["leave_types"]
    assert [item["code"] for item in types] == ["CASUAL", "SICK", "EARNED"]
    assert [item["default_days"] for item in types] == [12, 10, 15]


def test_create_leave_counts_only_weekdays(client, employee_headers, leave_types):
    start = next_monday()
    end = start + timedelta(days=4)  # Friday
    response = create_request(
        client, employee_headers, leave_types["CASUAL"]["id"], start, end
    )
    assert response.status_code == 201, response.get_json()
    body = response.get_json()
    assert body["days"] == 5
    assert body["status"] == "pending"
    assert body["reviewed_by"] is None


def test_create_leave_skips_the_weekend(client, employee_headers, leave_types):
    start = next_monday()
    end = start + timedelta(days=7)  # Monday of the following week
    response = create_request(
        client, employee_headers, leave_types["EARNED"]["id"], start, end
    )
    assert response.status_code == 201
    assert response.get_json()["days"] == 6


def test_pending_leave_does_not_reduce_balance(
    client, employee_headers, leave_types
):
    start = next_monday()
    create_request(
        client,
        employee_headers,
        leave_types["SICK"]["id"],
        start,
        start + timedelta(days=1),
    )
    balances = balance_map(client, employee_headers)
    assert balances["SICK"]["used_days"] == 0
    assert balances["SICK"]["remaining_days"] == 10


def test_create_leave_rejects_weekend_only_range(
    client, employee_headers, leave_types
):
    start = next_saturday()
    response = create_request(
        client,
        employee_headers,
        leave_types["CASUAL"]["id"],
        start,
        start + timedelta(days=1),
    )
    assert response.status_code == 422
    assert "no working days" in response.get_json()["errors"]["end_date"]


def test_create_leave_rejects_past_start(client, employee_headers, leave_types):
    start = date.today() - timedelta(days=7)
    response = create_request(
        client,
        employee_headers,
        leave_types["CASUAL"]["id"],
        start,
        start + timedelta(days=2),
    )
    assert response.status_code == 422
    assert "past" in response.get_json()["errors"]["start_date"]


def test_create_leave_rejects_reversed_dates(
    client, employee_headers, leave_types
):
    start = next_monday()
    response = create_request(
        client,
        employee_headers,
        leave_types["CASUAL"]["id"],
        start + timedelta(days=3),
        start,
    )
    assert response.status_code == 422
    assert "before the start" in response.get_json()["errors"]["end_date"]


def test_create_leave_rejects_cross_year_range(
    client, employee_headers, leave_types
):
    start = future_year_start()
    response = create_request(
        client,
        employee_headers,
        leave_types["EARNED"]["id"],
        start,
        start + timedelta(days=7),
    )
    assert response.status_code == 422
    assert "two calendar years" in response.get_json()["errors"]["end_date"]


def test_create_leave_requires_a_meaningful_reason(
    client, employee_headers, leave_types
):
    start = next_monday()
    response = create_request(
        client,
        employee_headers,
        leave_types["CASUAL"]["id"],
        start,
        start,
        reason="sick",
    )
    assert response.status_code == 422
    assert "reason" in response.get_json()["errors"]


def test_create_leave_validates_leave_type_and_dates(
    client, employee_headers
):
    response = client.post(
        "/api/leave-requests",
        headers=employee_headers,
        json={
            "leave_type_id": 999,
            "start_date": "not-a-date",
            "end_date": "",
            "reason": "A perfectly reasonable explanation.",
        },
    )
    assert response.status_code == 422
    errors = response.get_json()["errors"]
    assert "start_date" in errors
    assert "end_date" in errors


def test_create_leave_rejects_overlapping_request(
    client, employee_headers, leave_types
):
    start = next_monday()
    first = create_request(
        client,
        employee_headers,
        leave_types["CASUAL"]["id"],
        start,
        start + timedelta(days=4),
    )
    assert first.status_code == 201

    overlap = create_request(
        client,
        employee_headers,
        leave_types["SICK"]["id"],
        start + timedelta(days=2),
        start + timedelta(days=4),
    )
    assert overlap.status_code == 422
    assert "overlap" in overlap.get_json()["errors"]["start_date"]


def test_create_leave_rejects_insufficient_balance(
    client, employee_headers, leave_types
):
    start = next_monday()
    # 13 weekdays runs from Monday into the Wednesday of the third week.
    response = create_request(
        client,
        employee_headers,
        leave_types["CASUAL"]["id"],
        start,
        start + timedelta(days=16),
    )
    assert response.status_code == 422
    message = response.get_json()["errors"]["leave_type_id"]
    assert "Only 12 day(s)" in message


def test_employee_only_sees_their_own_requests(
    client, make_user, login_headers, leave_types
):
    first = make_user(name="Rohan Mehta", email="rohan@example.com")
    second = make_user(name="Sneha Iyer", email="sneha@example.com")
    first_headers = login_headers(first["email"])
    second_headers = login_headers(second["email"])

    start = next_monday()
    assert (
        create_request(
            client,
            first_headers,
            leave_types["CASUAL"]["id"],
            start,
            start,
        ).status_code
        == 201
    )

    own = client.get("/api/leave-requests", headers=first_headers).get_json()
    other = client.get("/api/leave-requests", headers=second_headers).get_json()
    assert own["total"] == 1
    assert other["total"] == 0


def test_admin_can_filter_requests_by_status(
    client, admin_headers, employee_headers, leave_types
):
    start = next_monday()
    create_request(
        client, employee_headers, leave_types["CASUAL"]["id"], start, start
    )
    create_request(
        client,
        employee_headers,
        leave_types["SICK"]["id"],
        start + timedelta(days=7),
        start + timedelta(days=7),
    )

    pending = client.get(
        "/api/leave-requests?status=pending", headers=admin_headers
    ).get_json()
    approved = client.get(
        "/api/leave-requests?status=approved", headers=admin_headers
    ).get_json()
    assert pending["total"] == 2
    assert approved["total"] == 0


def test_admin_can_search_requests_by_employee(
    client, admin_headers, make_user, login_headers, leave_types
):
    employee = make_user(name="Nisha Rao", email="nisha@example.com")
    headers = login_headers(employee["email"])
    start = next_monday()
    create_request(client, headers, leave_types["CASUAL"]["id"], start, start)

    response = client.get("/api/leave-requests?q=Nisha", headers=admin_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 1
    assert body["items"][0]["employee"]["name"] == "Nisha Rao"


def test_request_detail_enforces_ownership(
    client, admin_headers, make_user, login_headers, leave_types
):
    owner = make_user(name="Owner One", email="owner@example.com")
    other = make_user(name="Other Two", email="other@example.com")
    owner_headers = login_headers(owner["email"])
    other_headers = login_headers(other["email"])

    start = next_monday()
    created = create_request(
        client, owner_headers, leave_types["CASUAL"]["id"], start, start
    ).get_json()

    assert (
        client.get(
            f"/api/leave-requests/{created['id']}", headers=owner_headers
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/leave-requests/{created['id']}", headers=other_headers
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/leave-requests/{created['id']}", headers=admin_headers
        ).status_code
        == 200
    )


def test_cancel_pending_request(client, employee_headers, leave_types):
    start = next_monday()
    created = create_request(
        client, employee_headers, leave_types["CASUAL"]["id"], start, start
    ).get_json()

    response = client.post(
        f"/api/leave-requests/{created['id']}/cancel", headers=employee_headers
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "cancelled"

    again = client.post(
        f"/api/leave-requests/{created['id']}/cancel", headers=employee_headers
    )
    assert again.status_code == 409


def test_cancel_approved_request_restores_balance(
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

    approve = client.post(
        f"/api/leave-requests/{created['id']}/review",
        headers=admin_headers,
        json={"decision": "approve"},
    )
    assert approve.status_code == 200
    assert balance_map(client, employee_headers)["CASUAL"]["used_days"] == 2

    cancel = client.post(
        f"/api/leave-requests/{created['id']}/cancel", headers=employee_headers
    )
    assert cancel.status_code == 200
    balances = balance_map(client, employee_headers)
    assert balances["CASUAL"]["used_days"] == 0
    assert balances["CASUAL"]["remaining_days"] == 12


def test_employee_cannot_cancel_someone_elses_request(
    client, make_user, login_headers, leave_types
):
    owner = make_user(name="Owner One", email="owner@example.com")
    other = make_user(name="Other Two", email="other@example.com")
    owner_headers = login_headers(owner["email"])
    other_headers = login_headers(other["email"])

    start = next_monday()
    created = create_request(
        client, owner_headers, leave_types["CASUAL"]["id"], start, start
    ).get_json()

    response = client.post(
        f"/api/leave-requests/{created['id']}/cancel", headers=other_headers
    )
    assert response.status_code == 403


def test_leave_request_list_validates_filters(client, employee_headers):
    response = client.get("/api/leave-requests?status=unknown", headers=employee_headers)
    assert response.status_code == 400

    response = client.get("/api/leave-requests?page=abc", headers=employee_headers)
    assert response.status_code == 400


def test_leave_request_list_is_paginated(
    client, employee_headers, leave_types
):
    start = next_monday()
    for week in range(3):
        create_request(
            client,
            employee_headers,
            leave_types["CASUAL"]["id"],
            start + timedelta(days=7 * week),
            start + timedelta(days=7 * week),
        )

    response = client.get(
        "/api/leave-requests?page=1&per_page=2", headers=employee_headers
    )
    body = response.get_json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert body["has_next"] is True
    assert len(body["items"]) == 2
