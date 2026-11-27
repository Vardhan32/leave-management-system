"""Helpers for reading generator output inside the tests."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SPEC_PATH = HERE / "spec" / "openapi.yaml"
CASES_PATH = HERE / "generated" / "cases.json"


def spec_digest():
    return hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()


def load_cases():
    """Read cases.json at collection time (fixtures are not available there yet)."""
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def cases_where(**filters):
    """Return generated cases whose attributes match every filter.

    A filter value may be a tuple, meaning "any of these".
    """
    selected = []
    for case in load_cases()["cases"]:
        keep = True
        for key, wanted in filters.items():
            value = case.get(key)
            if isinstance(wanted, tuple):
                keep = keep and value in wanted
            else:
                keep = keep and value == wanted
        if keep:
            selected.append(case)
    return selected
