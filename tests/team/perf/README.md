# Performance tests (k6)

Operation under test: `POST /api/leave-requests` (workflow W1). Each iteration creates a
one-day request and cancels it again, so the database returns to the same state.
Limits and their reasons are written in `docs/team/performance.md` (set before the first run).

| File | Purpose |
| --- | --- |
| `leave_requests.js` | the workload; `VUS` users at the same time, 10 s warm-up then 60 s steady phase |
| `baseline_health.js` | calibration: how fast the machine answers `GET /api/health` (30 s, 1 user) |
| `run_perf.ps1` | resets the database, runs 1 user x 2 and 5 users x 2, saves raw output to `results/` |
| `summarise_perf.py` | turns `results/*.json` into the tables in `performance.md` |
| `results/` | raw k6 output (`*.txt`), summary exports (`*.json`), `environment.txt` |

Run (the API must be running on port 5001, k6 installed with `winget install k6`):

```powershell
powershell -ExecutionPolicy Bypass -File tests\team\perf\run_perf.ps1
backend\.venv\Scripts\python tests\team\perf\summarise_perf.py
```

k6 exits with code 99 when a threshold is crossed. The runner records that as a result
and continues with the next run.
