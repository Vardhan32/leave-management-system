"""Fixtures for the security checks that need the database (not the browser).

Same approach as tests/team/recovery/conftest.py: the application, API client
and sign-in fixtures come from tests/team/api/conftest.py.

Run from the repository root:

    python -m pytest tests/team/security
"""

import importlib.util
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api"

_spec = importlib.util.spec_from_file_location("area2_conftest", API_DIR / "conftest.py")
_area2 = sys.modules.get("area2_conftest") or importlib.util.module_from_spec(_spec)
sys.modules["area2_conftest"] = _area2
if not hasattr(_area2, "app"):
    _spec.loader.exec_module(_area2)

app = _area2.app
api = _area2.api
make_user = _area2.make_user
people = _area2.people
type_ids = _area2.type_ids
