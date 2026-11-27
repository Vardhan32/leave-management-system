import pytest
from datetime import date, timedelta

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models import LeaveBalance, LeaveRequest, LeaveType, User
from app.services import ensure_leave_types


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        ensure_leave_types()
        _db.session.commit()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    with app.app_context():
        yield _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    counter = {"n": 0}

    def _make(
        name="Employee",
        email=None,
        role="employee",
        department="Engineering",
        password="password123",
    ):
        counter["n"] += 1
        email = email or f"area1_user{counter['n']}@test.com"
        user = User(name=name, email=email, role=role, department=department)
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        return user

    return _make


@pytest.fixture()
def employee(make_user):
    return make_user()


@pytest.fixture()
def admin(make_user):
    return make_user(name="Admin", email="area1_admin@test.com", role="admin")


@pytest.fixture()
def casual_type(app):
    return LeaveType.query.filter_by(code="CASUAL").one()


@pytest.fixture()
def sick_type(app):
    return LeaveType.query.filter_by(code="SICK").one()


def _next_monday():
    today = date.today()
    days_ahead = 7 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


@pytest.fixture()
def next_monday():
    return _next_monday()


@pytest.fixture()
def login_headers(client):
    def _login(email, password="password123"):
        resp = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert resp.status_code == 200
        return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}

    return _login
