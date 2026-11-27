# Area 3 — use cases, usability, accessibility, security, performance

Worth use case specification 3 + use case automation 6 + usability and
accessibility 5 + defensive security 6 + performance and recovery 5, plus
your share of the viva.

Folders: `tests/team/e2e/` (Playwright, Node) and `tests/team/perf/` (k6).
Tools: Playwright (Chromium), @axe-core/playwright, Lighthouse, OWASP ZAP,
pip-audit, npm audit, k6.

## 0. Before you start

1. Clone the group repo, set `git config user.name` / `user.email` to yourself.
2. Install: Python 3.12, Node 20, Docker (for ZAP), k6
   (`winget install k6 --source winget`), ZAP desktop or the Docker image.
3. Run the app (two terminals):
   ```powershell
   cd backend; python -m venv .venv; .venv\Scripts\activate
   pip install -r requirements.txt
   flask --app run:app init-db; flask --app run:app seed-db; python run.py
   ```
   ```powershell
   cd frontend; npm install; npm run dev
   ```
   API on http://localhost:5001, UI on http://localhost:5173.
4. **Reset** before every recorded run (browser, ZAP, k6): stop the API,
   delete `backend/leave.db`, run `init-db`, `seed-db`, start again.
5. Playwright:
   ```powershell
   mkdir tests\team\e2e; cd tests\team\e2e
   npm init playwright@latest   # TypeScript or JS, Chromium only
   npm install -D @axe-core/playwright
   ```

## The UI you are testing

| Route | Who | What |
| --- | --- | --- |
| `/login` | anyone | "Work email", "Password"; quick-fill buttons "Employee" and "HR admin" |
| `/` | both | dashboard (balances for employees, headcount and pending for admins) |
| `/leave` | both | My leave list; opens the Apply modal (form `#apply-leave-form`: "Leave type", "Start date", "End date", "Reason"); cancel buttons |
| `/approvals` | admin | queue with tabs; Review modal with approve / reject and "Decision note" |
| `/team` | admin | directory with balances |

The token is kept in `localStorage` (`frontend/src/api/client.js`,
`frontend/src/auth/AuthContext.jsx`). The Apply modal's submit button sits
outside the `<form>` element and is linked by the `form` attribute — check
where it lands in the tab order.

## 1. Use cases (3 + 6 marks)

Two per **member** — six total. Agree who writes which. Each needs: actor,
preconditions, main flow, at least 2 alternative flows, at least 2 exception
flows, postconditions, and the FR/BR ids it covers
(`tests/team/api/support/requirements.py`).

Suggested set:

| UC | Actor | Alternatives | Exceptions |
| --- | --- | --- | --- |
| Apply for leave | Employee | other leave type; range over a weekend | balance too low; overlapping dates (or past start) |
| Approve request | Admin | approve with no note; approve from the detail view | own request (log in as admin with a request); already decided |
| Reject request | Admin | reject from detail; reject after checking balance | no note; already approved |
| Cancel leave | Employee | cancel approved future leave (days come back) | leave already started; rejected request |
| View balances | Employee | after an approval; filter by year | session expired |
| Team directory | Admin | search; department filter | employee opens `/team` |

Automate **every flow** in Playwright. Assert what the screen shows **and**
the postcondition (call the API from the test with Playwright's `request`
fixture, e.g. `GET /api/leave-balances`, and check `used_days`).

## 2. Usability and accessibility (5 marks)

1. Two task tests, one per workflow. In one, first submit a value the rule
   rejects (e.g. 13 casual days), assert the error says what to correct, fix
   it, assert success.
2. Keyboard test in one of them: Tab from the first field, assert focus goes
   Leave type → Start date → End date → Reason → Submit, press Enter, assert
   success.
3. Lighthouse (accessibility, best practices, SEO) on the key screen of each
   use case, logged in — DevTools after logging in, or Lighthouse CI with a
   login script. Save the HTML reports.
4. Full axe scans with `@axe-core/playwright` on the same screens. Save JSON.
5. Merge findings (an issue found by both tools counts once). For each:
   element, user impact, proposed fix, severity.
6. Fix one screen (in the app or your own HTML copy), rerun both tools,
   compare before and after.

Submit the scripts, the Playwright HTML report, Lighthouse and axe reports
before and after.

## 3. Defensive security (6 marks)

1. List the routes and data in both workflows (the spec
   `tests/team/api/spec/openapi.yaml` lists the endpoints).
2. Access matrix: role × action → allowed / denied. Example rows: employee
   approves (denied), admin approves another's (allowed), admin approves own
   (denied), employee opens `/approvals` (denied), employee reads another's
   request (hidden, 404), employee cancels own pending (allowed).
3. Playwright checks for at least four of them, at least one allowed and one
   denied, recording role, action, expected, observed, evidence (screenshot or
   response).
4. ZAP passive scan: run ZAP as a proxy, point Playwright at it
   (`use: { proxy: { server: 'http://localhost:8080' } }`), run both
   workflows, export the alerts. Review at least two controls, e.g.:
   - token in `localStorage` (readable by any script on the page)
   - security headers missing on API and UI responses
   - CORS origins in `backend/app/config.py`
   - role checks (compare with the source in `backend/app/api/leaves.py`)
   - WK-08: a deactivated user's token still works on `/api/leave-types`
5. Dependency audit: `pip-audit -r backend/requirements.txt` and
   `npm audit --json` in `frontend`. Record each package and version checked.
   For each relevant finding: component, evidence, impact, correction.

## 4. Performance and recovery (5 marks)

1. Pick an operation (`GET /api/leave-requests` is simplest; POST is more
   interesting). **Before running**, set and justify: p95 limit (e.g. ≤ 300 ms)
   and max unexpected failure rate (e.g. < 1 %).
2. k6 script in `tests/team/perf/`: log in in `setup()`, then load. For POST,
   give each request a different date range or most will be expected 422s
   (overlap); count expected rejections separately from unexpected failures.
3. Runs: 1 VU twice, ≥ 5 VUs twice, ≥ 60 s each at steady load, same build,
   machine and starting data (reset between runs). Report p95 ms, requests/s,
   unexpected failure %. Compare with your limits. Save raw output
   (`--summary-export`).
4. Recovery test (pytest, put it in `tests/team/recovery/`): make the database
   write fail once during an approval (monkeypatch `db.session.commit` to
   raise `sqlalchemy.exc.OperationalError`), check the request is still
   pending and `used_days` unchanged, remove the fault, retry, check it is
   approved and `used_days` grew exactly once. Reuse the fixtures in
   `tests/team/api/conftest.py`.

Record environment details: OS, CPU, RAM, Python, Node, k6 version, commit hash.

## Viva — expect these

- Rerun one Playwright flow and explain its assertions and postconditions.
- Explain one axe finding and your fix.
- Walk through the access matrix and the evidence for one denied action.
- Explain p95 and why your limits suit the operation.
- Explain how the recovery test proves there is no duplicate.

## Checklist

- [ ] Six use cases written (two per member), FR/BR ids attached
- [ ] Every flow automated with postcondition checks
- [ ] Two task tests, one with reject-then-correct, one keyboard test
- [ ] Lighthouse + axe before and after one fix, issues merged and explained
- [ ] Access matrix, 4+ Playwright checks with evidence
- [ ] ZAP passive report, 2+ controls reviewed against source
- [ ] pip-audit and npm audit recorded
- [ ] k6: limits set first, 4 runs, raw output, interpretation
- [ ] Recovery test passing
- [ ] AI-use record rows for your area
