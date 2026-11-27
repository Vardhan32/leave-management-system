# Area 3 viva notes (Ibrahim)

Read these with the files open. Rerun one flow yourself before the viva:
`cd tests/team/e2e; npx playwright test --project=use-cases -g "UC-02-E4" --headed`.

## What each part is, in plain words

**Use cases (3 documents, 22 flows).** `docs/team/use_cases/UC-01..03.md`. UC-01 apply, UC-02
review (approve / reject), UC-03 cancel. Each has a main flow, alternative flows (other
paths that still succeed) and exception flows (paths the rules refuse), plus
preconditions and postconditions. Every flow is one Playwright test whose title starts
with the flow id (`UC-01-E3`). Each test checks what the screen shows *and* the
postcondition through the API (request `status`, `used_days`, number of requests with
those dates), so "the screen says OK" is never the only evidence.

**How a test is built.** `support/api.ts` logs in through the API and reads state back.
`support/fixtures.ts` gives each test an `api` helper and a `signIn(role)` that puts the
token in `localStorage` (so only the login test uses the login form). Each test has its
own date slot (`support/dates.ts`) in next year, and the fixture cancels what the test
made, so the database ends as it began.

**Usability (5 tests).** U-01 is the W1 task: 13 casual days is refused with a message that
says how many days remain, the end date is corrected to 5 days, success. U-02 is the W2
task (admin approves). U-03 types the whole form with the keyboard only and checks the
order Leave type, Start date, End date, Reason, Cancel, Send request, then submits with
Enter. U-04 and U-05 check that focus moves into the dialog and stays there; they failed
on the original build and pass after the fix.

**Accessibility.** axe-core runs inside the browser on six states (login, My leave, apply
dialog, request detail, approvals, review dialog). Lighthouse (accessibility, best
practices, SEO) runs on four pages while signed in: Playwright's browser is started with
a debugging port, the token is written to `localStorage`, and Lighthouse audits the page
over that port without clearing storage. An issue found by both tools is counted once
(colour contrast was found by both). The fix, root cause and numbers are in
`docs/team/accessibility.md` and `accessibility_before_after.md`.

**Security.** `access_matrix.md` lists role, action, expected result; the Playwright
checks run it and save evidence. ZAP ran in passive mode (it only watches traffic the tests
produce; it sends no attacks). `pip-audit` and `npm audit` check package versions
against vulnerability databases. See `security.md`.

**Performance.** One operation: `POST /api/leave-requests`. Limits were fixed before the
first run: p95 at most 500 ms (1 user) and 1000 ms (5 users), unexpected failures under 1 %.
p95 means 95 of 100 requests were at least that fast. Each iteration creates a request and
cancels it, so data is the same after every iteration. Two runs per setup, 10 s warm-up and
60 s measured, database reset between runs. Results in `performance.md`.

**Recovery.** `tests/team/recovery/`. A fake commit raises the error SQLite gives when the
file is locked, once. The test checks nothing was saved (request still pending, `used_days`
unchanged), removes the fault, retries, and checks the request is approved, `used_days`
grew by the request's days once, and there is still exactly one request.

## Likely questions

1. **Why does the test read the API after the screen shows success?** The screen can show a
   message while nothing is stored. The API read proves the postcondition: status, balance,
   no duplicate.
2. **What is p95 and why not the average?** The value 95 % of requests were within. A few very
   slow requests do not move the average but users feel them.
3. **Explain the axe finding and the fix.** `color-contrast`: filter tab text `#6f7484` on
   `#ece4d4` is 3.7:1; WCAG AA needs 4.5:1 for small text. The token `--muted` was darkened to
   `#5d6373` (4.7:1 or better on the cream surfaces).
4. **Why did the recovery test need its own `app` fixture?** The Area 2 fixture keeps one app
   context open for the whole test, so every request shares one database session and a
   failed commit leaves its pending changes in that session. Real requests each get a new
   session that Flask discards at the end of the request.
5. **What does the denied-access evidence show?** AC-03: an employee calling the review endpoint
   gets 403 "Admin access is required." and the request is still pending (file
   `tests/team/e2e/reports/access/evidence/AC-03.json`).
6. **Which tests are "expected failures" and why?** `UC-01-D1`, `UC-02-D1` document DEF-A3-01 (the
   balance hint uses the wrong year). They state the correct behaviour; when the defect is
   fixed they report an unexpected pass so the marker gets removed. `test_wk08...` does the
   same for WK-08.
7. **Why a production build for the tests?** The Vite dev server serves hundreds of
   unbundled modules, which made every page load very slow on this machine; Lighthouse's
   best-practice and performance advice is also meant for a production build.
8. **Live task idea:** "the end date may not be more than 10 days after the start". Predict:
   UC-01 tests that use 13 days (E3) change; update `ApplyLeaveModal`, `validate_leave_window` and
   the OpenAPI spec for the API generator.
