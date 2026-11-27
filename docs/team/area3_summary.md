# Area 3 summary: where everything is

Owner: Ibrahim. Area 3 = use cases, usability, accessibility, security, performance and recovery.
Checklist from `tests/team/handoff/area3-human.md`:

| Checklist item | Status | Where |
| --- | --- | --- |
| Use cases written, FR/BR ids attached | 3 written (UC-01 apply, UC-02 review, UC-03 cancel); each has 2+ alternative and 2+ exception flows, pre/postconditions | `docs/team/use_cases/` |
| Every flow automated with postcondition checks | 22 flows, one test each, API read-back of status / `used_days` / counts | `tests/team/e2e/specs/use-cases/` |
| Two task tests; reject-then-correct; keyboard test | U-01 (reject then correct), U-02, U-03 (keyboard) | `tests/team/e2e/specs/usability/` |
| Lighthouse + axe before and after one fix, issues merged and explained | done; My leave screen axe 6 to 0 elements, Lighthouse accessibility 96 to 100 | `docs/team/accessibility.md`, `accessibility_before_after.md`, `tests/team/e2e/reports/{axe,lighthouse}/` |
| Access matrix, 4+ Playwright checks with evidence | 13 checks | `docs/team/access_matrix.md`, `access_results.md`, `tests/team/e2e/specs/security/` |
| ZAP passive report, 2+ controls reviewed against source | done: ZAP 2.17.0 passive, 37 URLs, 0 High / 9 Medium / 63 Low; 8 workflow tests proxied | `tests/team/security/reports/` |
| pip-audit and npm audit recorded | done | `docs/team/security.md` section 5, `tests/team/security/reports/` |
| k6: limits first, 4 runs, raw output, interpretation | done; limits written before the first run | `docs/team/performance.md`, `tests/team/perf/` |
| Recovery test passing | 4 tests, passing | `tests/team/recovery/` |
| AI-use record rows | written; the member must fill the "Checked by member" column | `docs/team/ai_use_record.md` |

Other files: defects `defects_area3.md`, traceability `area3_traceability.md`, viva notes
`area3_viva_notes.md`.

## Run everything

```powershell
# 1. API and UI (see tests/team/e2e/README.md)
# 2. browser tests, accessibility, access control
cd tests\team\e2e; npm install; npx playwright install chromium; npm test
# 3. Python tests
cd ..\..\..
# run the two Python folders one after the other (each has its own conftest.py)
backend\.venv\Scripts\python -m pytest tests/team/recovery
backend\.venv\Scripts\python -m pytest tests/team/security
# 4. load runs
powershell -ExecutionPolicy Bypass -File tests\team\perf\run_perf.ps1
```

## Changes to the application (the one accessibility fix)

`frontend/src/components/Modal.jsx` (focus moves into the dialog, Tab is kept inside, focus
returns to the opener), `frontend/src/styles.css` (`--muted` token darkened, cancelled badge colour,
`.sr-only`), `frontend/src/pages/MyLeavePage.jsx` (header cell text), `frontend/public/robots.txt`.
Nothing under `backend/app/` and nothing under `tests/team/api/` was changed.

## Suggested commits (one per topic, under your own name)

1. `test(e2e): add Playwright harness and use case specs` (`tests/team/e2e/{package.json,playwright.config.ts,support,specs/use-cases}`, `docs/team/use_cases`)
2. `test(e2e): add usability, accessibility scan and access control specs`
3. `fix(web): dialog focus management, text contrast, table header, robots.txt` (the `frontend/` files)
4. `docs(a11y): axe and Lighthouse before/after` (reports and docs)
5. `test(security): passive checks, dependency audit, WK-08 test` + `docs/team/security.md`
6. `test(perf): k6 workload and results` + `docs/team/performance.md`
7. `test(recovery): failure and recovery tests`
8. `docs: defects, traceability, viva notes, AI-use record`

Do not commit `backend/leave.db`, `backend/.venv`, `frontend/dist`, `frontend/node_modules`,
`tests/team/e2e/node_modules` (all ignored already) or `frontend/package-lock.json` changes made by `npm install`.
