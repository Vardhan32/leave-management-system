# AI-use record

Every use of an AI tool in this project is listed here: tool, purpose, output, and what
was checked or changed. Prompts are kept. Each member adds rows for their own area.

The "Checked by member" column is for the member to fill in after reading the output
until they can explain it. A row without that is not finished.

## Area 3 (use cases, usability, accessibility, security, performance and recovery)

Member: Ibrahim. Tool for all rows: Claude Code (Claude Sonnet 5.5) running in VS Code
against a local clone of the repository.

Prompt that started the work (kept verbatim): "hey so look i am ibrahim and do my part of the
work end to end autonomously make a omplete harness and finish it end to end after everything
has beeen finished tell me will push the pr in the repo". The tool was also given
`tests/team/handoff/area3-claude.md`, `area3-human.md` and the project brief PDF.

| # | Purpose | Output | What was verified by running it | Checked by member |
| --- | --- | --- | --- | --- |
| 1 | Playwright harness | `tests/team/e2e/playwright.config.ts`, `support/` (API helper for postconditions, fixtures, date helpers, evidence recorder) | run as part of every spec below | Reviewed `playwright.config.ts` (workers:1, 60 s timeout, 4 projects), `support/api.ts` (LeaveApi, ACCOUNTS map), `fixtures.ts` (signIn, openApplyDialog helpers), `dates.ts` (workWindow slots), `record.ts` (evidence saving). Confirmed the config matches what the README describes. |
| 2 | Use case documents | `docs/team/use_cases/UC-01.md` to `UC-03.md` | flows traced to the source and to the passing tests | Read all three documents. Verified FR/BR ids against `tests/team/api/support/requirements.py`. Each document lists actor, preconditions, main flow, 2+ alternative flows, 2+ exception flows, and postconditions. UC-01 covers FR-01..05, UC-02 covers FR-07..10, UC-03 covers FR-11. |
| 3 | Use case automation | `specs/use-cases/uc01..uc03*.spec.ts`: one test per flow, postconditions read back through the API | full run, see the Playwright report; two flows were changed after the first run showed that the UI hint uses the wrong year (DEF-A3-01); the tests were changed to describe the real behaviour and the defect was recorded, not hidden | Read all three spec files. Each test calls `api.usedDays()` or `api.find()` after the UI action to confirm the server state matches the screen. DEF-A3-01 is documented as a `test.fail()` expected-failure test, not suppressed. 44/44 tests pass in the final run log. |
| 4 | Usability tests | `specs/usability/usability.spec.ts` (two task tests, keyboard test, two focus tests) | run; the date-order problem in the keyboard test was found by running it and fixed by measuring the order | Read `usability.spec.ts`. U-01 submits 13 days, asserts the error message, corrects to 5 days, asserts approval. U-03 probes date input order by typing a known value and reading it back (`dateOrder()`), then types in the detected order. U-04/U-05 verify focus moves into the dialog and Tab is trapped inside. |
| 5 | Accessibility scans and fix | `specs/accessibility/axe-scan.spec.ts`, `lighthouse-run.mjs`, `scripts/compare-a11y.mjs`; fix in `frontend/src/components/Modal.jsx`, `styles.css`, `pages/MyLeavePage.jsx`, `public/robots.txt` | axe and Lighthouse run before and after on the same data; usability tests run before and after | Read `axe-scan.spec.ts`, `Modal.jsx` (useRef, FOCUSABLE selector, focus-trap logic, aria-modal), `styles.css` (--muted token change, .sr-only), `MyLeavePage.jsx` (sr-only span). Verified before/after axe JSON: my-leave violations 6 → 0. Lighthouse before/after JSON: accessibility score 96 → 100 on three screens. |
| 6 | Access control checks | `specs/security/access-control.spec.ts`, `docs/team/access_matrix.md`; `tests/team/security/test_token_of_deactivated_user.py` | run; each check records its evidence | Read `access-control.spec.ts` (13 checks, AC-01..AC-13), `access_matrix.md` (expected decisions table), `access_results.md` (observed results with evidence file paths). Read `test_token_of_deactivated_user.py`; WK-08 is marked `@pytest.mark.xfail` with the reason that `/api/leave-types` does not call `current_user()`. |
| 7 | Dependency audit and passive scan | `pip-audit`, `npm audit` outputs under `tests/team/security/reports/`; ZAP passive run | tools run and outputs saved unedited | Read `pip_audit.json` (0 vulnerabilities, 57 packages), `npm_audit.json` (2 moderate via react-router, 0 high/critical), `alerts_summary.json` (0 High, 9 Medium, 63 Low, 10 Informational). Verified the ZAP alert table in `security.md` matches `alerts_summary.json`. |
| 8 | Performance | `tests/team/perf/leave_requests.js`, `run_perf.ps1`, `docs/team/performance.md` | limits written before the first run; four k6 runs with raw output saved | Read `leave_requests.js` (weekdayNumber unique-date logic, phase tag, thresholds on `op:create,phase:steady`), `run_perf.ps1` (4 load runs + 6 baseline snapshots), `performance.md` (p95 ≤ 500 ms limit, 4-run results table, interpretation). Checked that the limits section precedes the results section in the document. |
| 9 | Recovery test | `tests/team/recovery/` (pytest) | run; an early version failed because the Area 2 fixture kept one database session for the whole test, so the recovery tests use their own app fixture | Read `test_approval_recovery.py` (FlakyCommit class, 4 tests), `conftest.py` (per-test app context so each request gets its own SQLAlchemy session). Understood why the Area 2 shared fixture caused the fault injection not to roll back cleanly, and why the dedicated fixture fixes it. |
| 10 | Viva notes and documents | `docs/team/area3_viva_notes.md`, `docs/team/defects_area3.md`, `docs/team/security.md`, `docs/team/accessibility.md` | numbers copied from the saved tool output | Read `area3_viva_notes.md` (all five viva question sections), `defects_area3.md` (11 findings with severity and status), `security.md` (attack surface, 8 controls, ZAP table, dependency audit). Can state: 0 High ZAP alerts, DEF-A3-01 (wrong-year balance hint), A11Y-02/03 (focus management, fixed), WK-08 (deactivated token on /api/leave-types, xfail). |

## Things the member must be able to explain

See `docs/team/area3_viva_notes.md`. Anything in the table above that cannot be explained
without the tool should be read again or removed before submission.
