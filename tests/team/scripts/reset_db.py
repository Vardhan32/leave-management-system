"""Put the local database back to the seeded baseline.

Works while the API is running: it drops and recreates the tables in the
same SQLite file, then loads the demo data again.

    backend/.venv/Scripts/python tests/team/scripts/reset_db.py
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.seed import seed  # noqa: E402
from app.services import ensure_leave_types  # noqa: E402

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    ensure_leave_types()
    db.session.commit()
    seed()
print("Database reset to the seeded baseline.")
