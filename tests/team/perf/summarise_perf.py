"""Reads the k6 summary exports in results/ and prints the table used in performance.md.

    python tests/team/perf/summarise_perf.py

Numbers are for the 60 s steady phase of the create call (tags op:create, phase:steady).
Requests per second is all requests of the steady phase (create + cancel) divided by 60.
"""

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
STEADY_SECONDS = 60
LIMITS = {1: 500, 5: 1000}
MAX_FAILED_PERCENT = 1.0

print("| Run | Users | p95 create (ms) | limit (ms) | req/s (create+cancel) | create/s | unexpected failures (create) | unexpected failures (cancel) | verdict |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for path in sorted(RESULTS.glob("vus*_run*.json")):
    users = int(path.name.split("_")[0].replace("vus", ""))
    metrics = json.loads(path.read_text(encoding="utf-8"))["metrics"]
    duration = metrics["http_req_duration{op:create,phase:steady}"]
    create = metrics["http_req_failed{op:create,phase:steady}"]
    cancel = metrics["http_req_failed{op:cancel,phase:steady}"]
    created = create["passes"] + create["fails"]
    cancelled = cancel["passes"] + cancel["fails"]
    p95 = duration["p(95)"]
    create_failed = 100.0 * create["passes"] / created if created else 0.0
    cancel_failed = 100.0 * cancel["passes"] / cancelled if cancelled else 0.0
    ok_time = p95 <= LIMITS[users]
    ok_fail = create_failed < MAX_FAILED_PERCENT
    verdict = "meets both limits" if ok_time and ok_fail else (
        "p95 over the limit" if not ok_time and ok_fail else
        "failure rate over the limit" if ok_time else "both over the limit")
    print("| {} | {} | {:.0f} | {} | {:.2f} | {:.2f} | {:.2f} % ({} of {}) | {:.2f} % | {} |".format(
        path.stem, users, p95, LIMITS[users], (created + cancelled) / STEADY_SECONDS,
        created / STEADY_SECONDS, create_failed, create["passes"], created, cancel_failed, verdict))

print()
print("| Run | create avg (ms) | median | p90 | p99 | max |")
print("| --- | --- | --- | --- | --- | --- |")
for path in sorted(RESULTS.glob("vus*_run*.json")):
    d = json.loads(path.read_text(encoding="utf-8"))["metrics"]["http_req_duration{op:create,phase:steady}"]
    print("| {} | {:.0f} | {:.0f} | {:.0f} | {:.0f} | {:.0f} |".format(
        path.stem, d["avg"], d["med"], d["p(90)"], d["p(99)"], d["max"]))
