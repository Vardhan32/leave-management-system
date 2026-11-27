# Briefing for Claude Code — Area 3 (use cases, usability, accessibility, security, performance)

You are helping one member of a three-person Software Quality Engineering
group with their assigned area. They are examined individually on everything
you produce, so build work they can explain and rerun.

Read `tests/team/handoff/README.md` and `tests/team/handoff/area3-human.md`
first. The human file has the UI map and the deliverables.

## Rules for this session

1. **Ask before any decision**: which use cases to write, response-time
   limits, failure-rate limits, which screen to fix, which security controls
   to review, Playwright language (TypeScript or JavaScript). Offer options
   with a recommendation.
2. **Do not commit or push.** The member commits under their own name. Never
   add Claude as a co-author or collaborator.
3. **Explain each new tool** (Playwright fixtures, axe, Lighthouse categories,
   ZAP passive scan, p95, k6 VUs and stages) in a few plain sentences the
   first time it appears.
4. Do not change `backend/app/` or `tests/team/api/`. The only app change
   allowed is the one accessibility fix, and only after the member agrees.
5. Comments neutral and human-sounding, only where needed; match existing
   indentation. In Python, no f-strings inside `print`.
6. Security work is defensive and local: synthetic data, test accounts,
   ZAP in **passive** mode only. No active scanning, no attacks.
7. Keep a list of generated files for the AI-use record.
8. Run what you write and show the output before calling it done.

## Context

- App: API `http://localhost:5001`, UI `http://localhost:5173` (Vite proxies
  `/api`). Start/reset steps are in `area3-human.md` section 0.
- Accounts: `demo@leavedesk.in` / `demo1234`, `admin@leavedesk.in` /
  `admin1234`. The seed creates 10 users; read `backend/app/seed.py` for
  others and their departments.
- Routes: `/login`, `/register`, `/`, `/leave`, `/approvals` (admin),
  `/team` (admin). Components: `ApplyLeaveModal.jsx`
  (form `#apply-leave-form`, labels "Leave type", "Start date", "End date",
  "Reason"; submit button outside the form via `form=`), `ReviewModal.jsx`
  ("Decision note"), `MyLeavePage.jsx` (cancel), `LoginPage.jsx`
  ("Work email", "Password", "Employee" / "HR admin" quick fill).
  Prefer `getByLabel` / `getByRole` locators; read the JSX to confirm names.
- Token storage: `localStorage` (`frontend/src/api/client.js`).
- Endpoints and their rules: `tests/team/api/spec/openapi.yaml`;
  requirement ids: `tests/team/api/support/requirements.py`;
  known weaknesses: `tests/team/api/reports/endpoint_weaknesses.md`.
- API test fixtures to reuse for the recovery test:
  `tests/team/api/conftest.py` (`app`, `api`, `people`, `type_ids`).

## Tasks, in order

Use a task list. Stop after each task, summarise briefly, wait for the member.

### Task 1 — Playwright scaffold
In `tests/team/e2e/`: `npm init playwright@latest` (Chromium only),
`@axe-core/playwright`, a `playwright.config` with `baseURL`
`http://localhost:5173`, HTML reporter, screenshots on failure, and
`webServer` entries that start the API and the UI (or document starting them
by hand — ask). Add a login helper and an `api` helper using Playwright's
`request` fixture with a bearer token for postcondition checks. Add a global
setup that resets the database if the member wants that automated (ask).

### Task 2 — use case documents
Ask which two use cases belong to this member and collect the others' from
the group. Write each in `docs/team/use_cases/UC-xx.md`: actor,
preconditions, main flow (numbered), 2+ alternative flows, 2+ exception
flows, postconditions, FR/BR ids.

### Task 3 — use case automation
One spec file per use case; one `test` per flow (main, each alternative, each
exception), titled with the flow id. Each test asserts the visible outcome
and the postcondition through the API (`used_days`, request `status`,
request count). Use fresh dates far in the future (next year, March) so seed
data does not collide; read the seed first. Run the suite and show the report.

### Task 4 — usability tests
Two task tests (one per workflow). In one, enter 13 casual days, assert the
error text explains what to fix, correct to a valid range, assert success.
Keyboard test: focus the first field, press Tab, assert
`document.activeElement` follows Leave type → Start date → End date →
Reason → Submit, press Enter, assert success. If the order is wrong, that is a
finding, not a test to bend; report it.

### Task 5 — accessibility scans
Axe: a spec that logs in and runs `new AxeBuilder({ page }).analyze()` on the
key screen of each use case, writing JSON to `tests/team/e2e/reports/axe/before/`.
Lighthouse: give the member the DevTools steps, or set up Lighthouse CI with
a puppeteer login script (ask which). Merge both tools' findings into
`docs/team/accessibility.md` (element, impact, fix, severity; duplicates
counted once). After the member picks a screen and agrees a fix, make it,
rerun into `after/`, and write the comparison.

### Task 6 — access control and passive security
Write `docs/team/access_matrix.md` (role × action → expected). Implement at
least four Playwright checks (one allowed, one denied minimum) recording role,
action, expected, observed, and evidence path. Give the member ZAP passive
proxy instructions and a Playwright project that uses the proxy. After they
export alerts, help review two or more controls against the source
(localStorage token, headers, CORS, role checks, WK-08). Run
`pip-audit -r backend/requirements.txt` and `npm audit --json` in `frontend`
and write `docs/team/security.md` with packages and versions checked and each
finding's component, evidence, impact, correction.

### Task 7 — performance
Ask the member for the operation and limits first, and record the
justification. Write `tests/team/perf/leave_requests.js` with `setup()` login,
a constant-VU scenario parameterised by `VUS`, a 60 s+ steady phase after
ramp, checks that separate expected 4xx from unexpected failures, and
`thresholds` matching the limits. Give the four run commands with
`--summary-export`, then help write `docs/team/performance.md` (environment,
p95, req/s, failure %, comparison with limits).

### Task 8 — recovery test
`tests/team/recovery/test_approval_recovery.py`, reusing the API fixtures
(add `tests/team/api` to `sys.path` or a small conftest). Monkeypatch
`app.extensions.db.session.commit` (or the session's commit) to raise
`sqlalchemy.exc.OperationalError` once during approval; assert 500 or
the propagated error, the request still `pending`, `used_days` unchanged;
remove the fault, retry, assert `approved`, `used_days` increased once, no
duplicate request. Note: with `TESTING = True` Flask propagates exceptions to
the test, so expect to catch the exception rather than read a 500. Explain
this to the member.

### Task 9 — viva notes
`docs/team/area3_viva_notes.md`: a paragraph per component in plain words
and five likely questions with short answers. Ask the member to rerun one
flow and explain it back to you.
