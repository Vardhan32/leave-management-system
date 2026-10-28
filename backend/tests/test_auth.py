from datetime import date

from app.extensions import db
from app.models import User


def register(client, **overrides):
    payload = {
        "name": "Aditi Sharma",
        "email": "aditi@example.com",
        "password": "password123",
        "department": "Design",
        "job_title": "Product Designer",
    }
    payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


def test_register_creates_employee_with_balances(client):
    response = register(client)
    assert response.status_code == 201
    body = response.get_json()
    assert body["access_token"]
    assert body["user"]["role"] == "employee"
    assert body["user"]["email"] == "aditi@example.com"

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    balances = client.get("/api/leave-balances", headers=headers).get_json()
    assert balances["year"] == date.today().year
    remaining = {
        item["leave_type"]["code"]: item["remaining_days"]
        for item in balances["balances"]
    }
    assert remaining == {"CASUAL": 12, "SICK": 10, "EARNED": 15}


def test_register_normalises_email_and_hashes_password(client, app):
    response = register(client, email="  ADITI@Example.com  ")
    assert response.status_code == 201
    assert response.get_json()["user"]["email"] == "aditi@example.com"

    with app.app_context():
        user = User.query.filter_by(email="aditi@example.com").first()
        assert user is not None
        assert user.password_hash != "password123"
        assert user.check_password("password123")


def test_register_rejects_duplicate_email(client):
    assert register(client).status_code == 201
    duplicate = register(client, name="Someone Else")
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.get_json()["message"]


def test_register_validates_required_fields(client):
    response = client.post("/api/auth/register", json={})
    assert response.status_code == 422
    errors = response.get_json()["errors"]
    assert "name" in errors
    assert "email" in errors
    assert "password" in errors


def test_register_validates_email_and_password_length(client):
    response = register(client, email="not-an-email", password="short")
    assert response.status_code == 422
    errors = response.get_json()["errors"]
    assert errors["email"] == "Enter a valid email address."
    assert "at least 8" in errors["password"]


def test_register_rejects_non_object_body(client):
    response = client.post("/api/auth/register", json=["nope"])
    assert response.status_code == 400


def test_login_returns_token_and_profile(client):
    register(client, email="login@example.com")
    response = client.post(
        "/api/auth/login",
        json={"email": "LOGIN@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.get_json()["access_token"]

    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "login@example.com"


def test_login_rejects_wrong_password(client):
    register(client, email="login@example.com")
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert response.get_json()["message"] == "Incorrect email or password."


def test_login_requires_password(client):
    response = client.post("/api/auth/login", json={"email": "a@b.com"})
    assert response.status_code == 422
    assert "password" in response.get_json()["errors"]


def test_inactive_user_cannot_login(client, make_user, app):
    user = make_user(email="inactive@example.com")
    with app.app_context():
        record = db.session.get(User, user["id"])
        record.is_active = False
        db.session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 401


def test_protected_endpoints_require_token(client):
    for path in ("/api/auth/me", "/api/leave-balances", "/api/dashboard"):
        assert client.get(path).status_code == 401


def test_health_check_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
