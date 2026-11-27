"""Fixtures for the team API and integration tests.

The tests drive the real Flask application through its test client, so every
request goes through routing, JSON parsing, JWT checks, validation and the
database. Each test gets a new in-memory SQLite database, which is the reset
between tests: nothing one test creates is visible to the next.

Run from the repository root:

    python -m pytest tests/team/api
"""

import csv
import json
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
BACKEND = REPO_ROOT / "backend"
SPEC_PATH = HERE / "spec" / "openapi.yaml"
CASES_PATH = HERE / "generated" / "cases.json"
REPORTS = HERE / "reports"

for extra in (str(BACKEND), str(HERE)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from support.api_coverage import CoverageTracker  # noqa: E402
from support.generated import spec_digest  # noqa: E402

PASSWORD = "password123"
EMPLOYEE_EMAIL = "demo@leavedesk.in"


# -- command line and reporting hooks ----------------------------------------
def pytest_addoption(parser):
    parser.addoption(
        "--api-coverage-min",
        type=float,
        default=None,
        help="fail the run if any API coverage criterion is below this percent",
    )


_TRACKER = CoverageTracker(yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8")))
_TRACE_ROWS = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" and not (report.when == "setup" and report.outcome != "passed"):
        return
    reqs = []
    for mark in item.iter_markers(name="req"):
        reqs.extend(mark.args)
    outcome_text = report.outcome
    if hasattr(report, "wasxfail"):
        outcome_text = "xfailed" if report.skipped else "xpassed"
    _TRACE_ROWS.append((item.nodeid, " ".join(sorted(set(reqs))), outcome_text))


def pytest_sessionfinish(session, exitstatus):
    if _TRACKER.calls == 0:
        return
    rows = _TRACKER.write_reports(REPORTS)
    with open(REPORTS / "test_traceability.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["test", "requirements", "outcome"])
        writer.writerows(_TRACE_ROWS)

    minimum = session.config.getoption("--api-coverage-min")
    if minimum is not None:
        low = {name: row["percent"] for name, row in rows.items() if row["percent"] < minimum}
        if low:
            print("\nAPI coverage below", minimum, "%:", low)
            session.exitstatus = 1


# -- spec and generated data --------------------------------------------------
@pytest.fixture(scope="session")
def spec():
    return _TRACKER.index.spec


@pytest.fixture(scope="session")
def generated():
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if data["spec_sha256"] != spec_digest():
        pytest.exit(
            "generated/cases.json is older than spec/openapi.yaml. Run "
            "python tests/team/api/generator/generate_cases.py first.",
            returncode=2,
        )
    return data


# -- application --------------------------------------------------------------
@pytest.fixture()
def app():
    from app import create_app
    from app.config import TestConfig
    from app.extensions import db
    from app.services import ensure_leave_types

    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        ensure_leave_types()
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


class Result:
    def __init__(self, response):
        self.status = response.status_code
        self.json = response.get_json(silent=True)

    def error_fields(self):
        return set((self.json or {}).get("errors", {}))

    def __repr__(self):
        return "<Result {} {}>".format(self.status, self.json)


class ApiClient:
    """Thin wrapper over the Flask test client that records coverage."""

    NO_BODY = object()

    def __init__(self, client):
        self.client = client

    def call(self, method, path, token=None, body=NO_BODY, query=None, headers=None):
        all_headers = dict(headers or {})
        if token:
            all_headers["Authorization"] = "Bearer " + token
        kwargs = {"method": method, "headers": all_headers, "query_string": query or {}}
        if body is not self.NO_BODY:
            kwargs["json"] = body
        response = self.client.open(path, **kwargs)
        result = Result(response)
        problems = _TRACKER.record(
            method, path, query, None if body is self.NO_BODY else body,
            result.status, result.json,
        )
        assert not problems, "Response does not match the spec: {} -> {}".format(problems, result)
        return result

    def get(self, path, token=None, query=None, **kwargs):
        return self.call("GET", path, token=token, query=query, **kwargs)

    def post(self, path, token=None, body=NO_BODY, **kwargs):
        return self.call("POST", path, token=token, body=body, **kwargs)


@pytest.fixture()
def api(app):
    return ApiClient(app.test_client())


@pytest.fixture()
def make_user(app):
    from app.extensions import db
    from app.models import User

    def _make_user(email, role="employee", name="Test User", department="Engineering"):
        with app.app_context():
            user = User(name=name, email=email, role=role, department=department,
                        job_title="Tester")
            user.set_password(PASSWORD)
            db.session.add(user)
            db.session.commit()
            return user.id

    return _make_user


class Person:
    def __init__(self, user_id, email, token):
        self.id = user_id
        self.email = email
        self.token = token


@pytest.fixture()
def people(api, make_user):
    """Two employees in different departments and one admin, all signed in."""
    created = {}
    for key, email, role, department in (
        ("employee", EMPLOYEE_EMAIL, "employee", "Engineering"),
        ("colleague", "colleague@leavedesk.in", "employee", "Design"),
        ("admin", "admin@leavedesk.in", "admin", "People Ops"),
    ):
        user_id = make_user(email, role=role, department=department)
        result = api.post("/api/auth/login", body={"email": email, "password": PASSWORD})
        assert result.status == 200, result
        created[key] = Person(user_id, email, result.json["access_token"])
    return created


@pytest.fixture()
def type_ids(api, people):
    result = api.get("/api/leave-types", token=people["employee"].token)
    assert result.status == 200
    return {item["code"]: item["id"] for item in result.json["leave_types"]}


@pytest.fixture()
def insert_request(app):
    """Store a request straight in the database.

    Only used where the API cannot create the starting state, such as an
    approved request whose start date is already in the past.
    """
    from app.extensions import db
    from app.models import LeaveRequest

    def _insert(user_id, leave_type_id, start, end, days, status="pending"):
        with app.app_context():
            item = LeaveRequest(user_id=user_id, leave_type_id=leave_type_id,
                                start_date=start, end_date=end, days=days,
                                reason="Inserted directly for a test setup.", status=status)
            db.session.add(item)
            db.session.commit()
            return item.id

    return _insert
