"""Fixtures for the recovery tests.

The application, API client and sign-in fixtures are the ones from
tests/team/api/conftest.py. That file is loaded under another name and its
fixtures are re-exported here, so the recovery tests start from the same
empty in-memory database and the same three signed-in people.

Run from the repository root:

    python -m pytest tests/team/recovery
"""

import importlib.util
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api"

_spec = importlib.util.spec_from_file_location("area2_conftest", API_DIR / "conftest.py")
_area2 = importlib.util.module_from_spec(_spec)
sys.modules["area2_conftest"] = _area2
_spec.loader.exec_module(_area2)

import pytest

api = _area2.api
make_user = _area2.make_user
people = _area2.people
type_ids = _area2.type_ids


@pytest.fixture()
def app():
    """The application with no app context kept open between requests.

    The Area 2 fixture keeps one app context open for the whole test, so every
    request shares one database session. Here each request gets its own
    session, which Flask discards at the end of the request, as in real use.
    That is what makes a failed commit leave nothing behind. The in-memory
    SQLite database is shared between contexts, so the data survives.
    """
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
    with application.app_context():
        db.session.remove()
        db.drop_all()
