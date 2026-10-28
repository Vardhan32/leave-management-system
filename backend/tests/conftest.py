import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import LeaveType, User
from app.services import ensure_leave_types


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        ensure_leave_types()
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    counter = {"value": 0}

    def _make_user(
        name="Test Employee",
        email=None,
        role="employee",
        department="Engineering",
        job_title="Software Engineer",
        password="password123",
    ):
        counter["value"] += 1
        email = email or f"user{counter['value']}@example.com"
        with app.app_context():
            user = User(
                name=name,
                email=email,
                role=role,
                department=department,
                job_title=job_title,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "password": password,
                "role": role,
            }

    return _make_user


@pytest.fixture()
def login_headers(client):
    def _login(email, password="password123"):
        response = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.get_json()
        token = response.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login


@pytest.fixture()
def employee_headers(make_user, login_headers):
    user = make_user()
    return login_headers(user["email"])


@pytest.fixture()
def admin_headers(make_user, login_headers):
    user = make_user(
        name="Test Admin",
        email="admin@example.com",
        role="admin",
        department="People Ops",
        job_title="HR Manager",
    )
    return login_headers(user["email"])


@pytest.fixture()
def leave_types(app):
    with app.app_context():
        return {
            item.code: item.to_dict()
            for item in LeaveType.query.order_by(LeaveType.sort_order.asc()).all()
        }
