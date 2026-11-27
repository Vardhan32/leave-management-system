# Area 3 browser tests (Playwright)

Use cases, usability, accessibility scans and access-control checks for LeaveDesk.
TypeScript, Playwright with Chromium, `@axe-core/playwright`, Lighthouse.

## Run

Start the API and the UI first (two terminals), from the repository root:

```powershell
# API (port 5001)
cd backend; .venv\Scripts\activate
flask --app run:app init-db; flask --app run:app seed-db
flask --app run:app run --port 5001

# UI (port 5173): the production build is what the tests and Lighthouse audit
cd frontend; npm install; npm run build; npx vite preview --port 5173
```

Then:

```powershell
cd tests\team\e2e
npm install
npx playwright install chromium
npm test                                   # everything
npx playwright test --project=use-cases    # UC-01..UC-03, every flow
npx playwright test --project=usability    # task tests and keyboard test
npx playwright test --project=security     # access control checks
$env:AXE_PHASE="before"; npx playwright test --project=accessibility   # or "after"
node lighthouse-run.mjs before             # or "after"
npm run report                             # opens the HTML report
```

`npm test` for the use-case and usability projects creates requests with dates in
next year and cancels them again in the fixture teardown, so the database ends
as it started. For a recorded run, reset first:

```powershell
backend\.venv\Scripts\python tests\team\scripts\reset_db.py
```

## Layout

| Path | Content |
| --- | --- |
| `specs/use-cases/` | one file per use case, one test per flow, titled with the flow id (`UC-01-E3 ...`) |
| `specs/usability/` | W1 and W2 task tests, keyboard test, focus-management tests |
| `specs/accessibility/` | full axe-core scans of the key screens, JSON to `reports/axe/<phase>/` |
| `specs/security/` | access-control checks with recorded evidence |
| `support/` | API helper (postconditions), fixtures, date helpers, evidence recorder |
| `lighthouse-run.mjs` | signs in through Playwright's browser and runs Lighthouse on four screens |
| `scripts/render-reports.mjs` | traceability CSV and access-results table |
| `scripts/compare-a11y.mjs` | before/after accessibility comparison |
| `reports/` | HTML report, JSON results, axe, Lighthouse and access evidence |

## Notes

- Tests run one at a time (`workers: 1`) because the app uses one SQLite file.
- Each test uses its own date slot (`support/dates.ts`), so tests never share dates.
- `test.fail(...)` marks a known defect as an expected failure; the test states the
  behaviour it should have and starts failing loudly (as an unexpected pass) when the
  defect is fixed. See `docs/team/accessibility.md` and `docs/team/defects_area3.md`.
- Passive ZAP run: set `ZAP_PROXY=http://127.0.0.1:8080`, `UI_URL=http://host.docker.internal:5173` and
  `API_URL=http://host.docker.internal:5173` (the API is reached through the UI's `/api` proxy so ZAP sees it too).
  The UI server must be started with `--host 0.0.0.0` and `__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=host.docker.internal`
  for that run only. Full commands in `docs/team/security.md` section 4.
- Passive header, cookie and CORS checks without ZAP: `specs/security/passive-controls.spec.ts` (output in `reports/security/`).
