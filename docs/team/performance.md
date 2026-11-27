# Performance and recovery (Area 3)

## 1. Operation and limits (set before any load run)

These limits were written on 24 Nov 2026, before the first k6 run, from the
way the operation is used and not from measurements.

**Operation under test:** `POST /api/leave-requests` (an employee sends a leave
request, workflow W1). It is the state-changing step of W1: it validates the
body, checks the dates and the overlap rule, reads the balance and writes one
row. Each iteration of the script creates one single-day request and then
cancels it (`POST /api/leave-requests/{id}/cancel`), so the database returns to
the same state after every iteration and every run starts from the same data.
Only the create call is judged against the limits; the cancel call is
bookkeeping and is reported separately.

| Workload | Simulated users | Response time limit (p95 of create) | Unexpected failures |
| --- | --- | --- | --- |
| W-1 | 1 | at most **500 ms** | fewer than **1 %** |
| W-5 | 5 at the same time | at most **1000 ms** | fewer than **1 %** |

**Why these limits suit the operation**

- *p95, not the average.* p95 is the time that 95 of every 100 measured
  requests finished within. A leave form that is fast on average but takes
  several seconds for one submission in twenty is felt by users; the average
  hides that, p95 does not.
- *500 ms for one user.* A person who presses "Send request" waits for the
  confirmation. Up to about one second the wait does not break the flow of
  work; half a second leaves room on a slow laptop. The request does one
  `SELECT` for overlap, one for the balance and one `INSERT`, so it should
  need far less than this when nothing else is running.
- *1000 ms for five users.* The app is a small-team tool (the seed has ten
  people) and its API runs on Flask's single-process development server with
  SQLite, which serialises writes. Five people sending at the same instant
  will wait for each other a little, so the limit is doubled, but it stays at
  the one-second mark where users still feel the system is responding.
- *Fewer than 1 % unexpected failures.* The script expects exactly one answer
  for the create call (`201`). Anything else (a `5xx`, a timeout, a `422` that
  means the data collided, or a refused connection) is an unexpected failure.
  One in a hundred is the example the brief gives and is already generous for
  a call that, with distinct dates per user, has no legitimate reason to fail.
  Rejections that are part of the business rules (422 overlap, 422 balance) are
  not produced by this script, so they cannot hide failures.

## 2. Method

- Tool: Grafana k6 OSS 2.4.0, script `tests/team/perf/leave_requests.js`, runner
  `tests/team/perf/run_perf.ps1`, summary script `summarise_perf.py`.
- One scenario per run with a fixed number of virtual users (VUs). The first 10 s are a warm-up and
  are not measured; the next **60 s are the steady phase** the numbers are taken from (requests carry
  the tags `op:create|cancel` and `phase:warmup|steady`, and thresholds look only at `phase:steady`).
- Each iteration: create a one-day Casual request, then cancel it. Every iteration uses a new weekday
  date (starting 3 March 2031) and each VU is a different seeded employee (`demo`, `rohan.iyer`,
  `kabir.shah`, `isha.verma`, `arjun.menon`, password `demo1234`), so VUs never collide and a failed
  cancel cannot block the next create.
- No pause between iterations: a VU sends its next request as soon as the previous one is answered, which
  shows how the server behaves when kept busy.
- Each setup (1 VU, 5 VUs) is run twice on the same build, machine and data. The database is reset
  (`tests/team/scripts/reset_db.py`) before every run.
- **Calibration.** Before every run, and at the start and the end of the batch, k6 sends `GET /api/health`
  from one VU (`baseline_health.js`). It needs no login and no database, so it shows how fast this machine
  can answer at that moment. The figures sit in section 3 next to the run they belong to.
- Unexpected failure = any create answered with something other than `201` (5xx, 4xx, timeout, refused
  connection). The script never produces a business-rule rejection on purpose, so every non-201 counts.

### How the workload changed before the reported runs

The reported numbers are from the third version of the script. The two earlier versions were
discarded because the script, not the application, produced the failures:

1. **Version 1** ran a warm-up scenario and a steady scenario one after the other. The two scenarios
   overlapped for a few seconds and used the same employee and date, so the overlap rule (HTTP 422)
   rejected some creates. Fixed with one scenario for the whole run.
2. **Version 2** used one fixed date per VU. In one run a single cancel call failed during a latency spike
   (1 of 428); the request stayed pending and every later create of that VU hit the overlap rule: 123
   "unexpected" failures (22.3 %). Fixed by using a new date every iteration. The v2 files are kept in
   `tests/team/perf/results/superseded_v2/` with an explanation.

Both changes fix defects in the test. They were made after seeing earlier results, so they are
disclosed here; the limits in section 1 were not changed at any point.


## 3. Results

Raw output: `tests/team/perf/results/vus*_run*.txt` (k6 console output) and `.json` (summary export).
Numbers are for the 60 s steady phase of the create call. Requests per second counts all requests of the
steady phase (create and cancel).

| Run | Users | p95 create | Limit | Requests/s | Creates/s | Unexpected failures (create) | Unexpected failures (cancel) | Result against the limits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vus1_run1 | 1 | **994 ms** | 500 ms | 4.47 | 2.23 | 0.00 % (0 of 134) | 0.00 % | p95 **over** the limit, failures within |
| vus1_run2 | 1 | 242 ms | 500 ms | 10.87 | 5.43 | 0.00 % (0 of 326) | 0.00 % | meets both limits |
| vus5_run1 | 5 | 675 ms | 1000 ms | 16.63 | 8.32 | 0.00 % (0 of 499) | 0.00 % | meets both limits |
| vus5_run2 | 5 | 754 ms | 1000 ms | 16.73 | 8.37 | 0.00 % (0 of 502) | 0.00 % | meets both limits |

Other figures of the create call (milliseconds):

| Run | average | median | p90 | p99 | max |
| --- | --- | --- | --- | --- | --- |
| vus1_run1 | 234 | 76 | 779 | 1487 | 3615 |
| vus1_run2 | 96 | 64 | 180 | 477 | 1613 |
| vus5_run1 | 319 | 256 | 577 | 1210 | 1459 |
| vus5_run2 | 334 | 279 | 576 | 1092 | 1357 |

**Calibration** (`GET /api/health`, 1 user, no database): how fast the machine answered the cheapest
request right before each run.

| Measured | Requests answered | Median | p95 | Max | Belongs to |
| --- | --- | --- | --- | --- | --- |
| start of batch, 30 s | 553 | 9 ms | 121 ms | 499 ms | |
| before vus1_run1, 10 s | **25** | **332 ms** | 499 ms | 2626 ms | vus1_run1 (the run over the limit) |
| before vus1_run2, 10 s | 131 | 68 ms | 130 ms | 299 ms | vus1_run2 |
| before vus5_run1, 10 s | 563 | 9 ms | 45 ms | 233 ms | vus5_run1 |
| before vus5_run2, 10 s | 51 | 126 ms | 459 ms | 783 ms | vus5_run2 |
| end of batch, 30 s | 826 | 12 ms | 145 ms | 617 ms | |

## 4. Environment

From `tests/team/perf/results/environment.txt`:

| Item | Value |
| --- | --- |
| OS | Microsoft Windows 10 Pro 10.0.19045 |
| CPU / RAM | Intel Core i5-5300U 2.30 GHz (2 cores, 4 threads), 15.8 GB |
| Python / Flask / Werkzeug / SQLAlchemy | 3.12.10 / 3.1.3 / 3.1.9 / 2.1.9 |
| Node | 22.17.1 |
| k6 | 2.4.0 (go1.26.11, windows/amd64), installed with `winget install GrafanaLabs.k6` |
| Server | `flask run` (Werkzeug development server, threaded), SQLite file `backend/leave.db`, no reverse proxy |
| Build | git commit `a706e764f9358058f9d7d6d40d211b35c468f5fb` plus the working-tree changes of this branch |
| Load generator | k6 on the same machine as the server (they share the 2 cores) |

The machine is a laptop that was also running a code editor, browsers and an unrelated background
search process during the runs. That load was not controlled and it is the main limit on how far
these numbers can be trusted (see section 5).

## 5. Interpretation against the limits

| Criterion (set before the runs) | Target | Actual | Verdict |
| --- | --- | --- | --- |
| W-1, p95 of create | at most 500 ms | 994 ms and 242 ms | met in 1 of 2 runs |
| W-1, unexpected failures | under 1 % | 0 % and 0 % | met |
| W-5, p95 of create | at most 1000 ms | 675 ms and 754 ms | met in 2 of 2 runs |
| W-5, unexpected failures | under 1 % | 0 % and 0 % | met |

- **Correctness under concurrency held.** Across the 1461 create calls of the four reported runs (and the
  same number of cancel calls) there was not one unexpected response, and the data returned to its starting
  state after every iteration. Five users writing to SQLite at the same time did not produce
  "database is locked" errors or duplicates in these runs.
- **The 500 ms limit for one user was missed once, and the evidence points at the machine, not the code.**
  In `vus1_run1` the median create took 76 ms, but a minority of requests were very slow (p90 779 ms,
  max 3.6 s). The calibration taken 10 s before that run answered 25 requests in 10 s with a 332 ms median
  for a request that normally takes 9 ms, so the machine itself was stalled at that time. In `vus1_run2`,
  with a quieter machine, the same script on the same build gave p95 242 ms. Two runs are too few to give a
  confident pass for this workload, so the honest status of W-1 is "met when the machine is quiet, not
  reproducibly met on this laptop". A repeat on an idle machine (or more runs) is the next step.
- **The 1000 ms limit for five users was met twice**, including `vus5_run2`, whose calibration shows the same
  kind of disturbance (median 126 ms) while p95 stayed at 754 ms.
- **Throughput does not scale with users.** Five users completed about 8.3 creates/s, against a best of
  5.4 creates/s for one user: 5 times the users gave about 1.5 times the throughput, and the latency per request
  rose (median 64 to 279 ms). That is the signature of a single-process server on two cores that also run the
  load generator, with SQLite serialising writes. The development server is not meant for production; a
  production WSGI server and a client/server database would be the first change to try.
- **Why the limits suited the operation.** The problem showed in the slow tail (p90 to max) and not in the
  average: the average of `vus1_run1` (234 ms) was well inside 500 ms, only p95 exposed the problem.

Finding PERF-01 in [defects_area3.md](defects_area3.md): the latency tail of `POST /api/leave-requests` is
sensitive to host load, and throughput is capped at about 8 creates/s on this machine.

## 6. Failure and recovery test

`tests/team/recovery/` (pytest, 4 tests, all passing). A test double replaces `db.session.commit` for the
first call so it raises `sqlalchemy.exc.OperationalError("database is locked")`, which is what SQLite reports
when the database is unavailable at the moment a write completes. The real application code runs.

| Step | Approval (`POST .../review`) | Create (`POST /api/leave-requests`) |
| --- | --- | --- |
| Before | request pending, `used_days` 0, one request | no requests |
| Fault | commit fails once; the error reaches the caller (HTTP 500 when exception propagation is off) | commit fails once |
| State after the failure | request still `pending`, no reviewer, no note, `used_days` 0, still one request | still no request |
| Retry with the fault removed | `200`, status `approved`, note kept | `201`, one request stored |
| Final state | `used_days` grew by the request's 3 days **once**, one request (no duplicate) | exactly one request; sending the same body again is refused with `422` (overlap), so still one |
| Extra | a second approval after the success gets `409`, so the balance cannot be charged twice | |

Why it is safe: the code changes the request and the balance inside one session and commits once at the end,
so a failed commit rolls back both. The recovery relies on Flask discarding the session at the end of the
request, which the dedicated `app` fixture in `tests/team/recovery/conftest.py` reproduces (see the README
there for why the shared Area 2 fixture could not be used).

Known gap, from the Area 2 weaknesses (WK-10): the overlap rule is checked in Python only, so two identical
create requests sent at exactly the same moment could still both pass. The recovery test covers sequential
retries; the concurrent case was not reproduced by the k6 runs because every virtual user has its own dates.
