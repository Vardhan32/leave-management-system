# Area 3 findings (usability, accessibility, security, performance)

Severity and priority use the scale of the shared test plan (Critical / Major / Minor /
Trivial; High / Medium / Low). The risk column uses descriptive names until the shared
risk register assigns ids (`R-?`). Each row should become a GitHub Issue; the
`Status` column says what has been done in this branch.

| Id | Area | Finding | Evidence | Severity | Priority | Risk | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DEF-A3-01 | Usability / BR1 | The Apply and Review dialogs show the balance of the **current year** (`GET /api/leave-balances` without `year`), not the year of the requested dates. For a request in another year the "needs N days, but only M remain" warning shows the wrong M and the Approve button is not disabled. The server still refuses the request, so no wrong data is stored, but the user only learns it after sending. | `UC-01-D1`, `UC-02-D1` (expected failures), `UC-02-E2` | Major | Medium | R-? BR1 balance rule, usability | Open |
| A11Y-01 | Accessibility | Text colour `#6f7484` on `#ece4d4` (filter tabs) has contrast 3.68:1 (needs 4.5:1). Same token on the avatar initials (3.62:1, 1.4:1 on login) and on the demo box text (4.09:1). | axe `color-contrast`, Lighthouse `color-contrast` | Serious | Medium | R-? usability / accessibility | Filter tabs fixed (My leave); avatars and login text open |
| A11Y-02 | Accessibility | Opening a dialog does not move focus into it. Focus stays on the button behind it, so a keyboard user must Tab through the whole page to reach the form. | `U-04`, manual Tab order in `U-03` | Major | High | R-? usability / accessibility | Fixed in `Modal.jsx` |
| A11Y-03 | Accessibility | The dialog does not trap focus; Tab leaves it and moves through the page behind (which `aria-modal="true"` says is inert). Closing does not return focus to the opener. | `U-05` | Major | High | R-? usability / accessibility | Fixed in `Modal.jsx` |
| A11Y-04 | Accessibility | Table header cell with no text (`<th aria-label="Actions" />`); screen readers announce an empty header. | axe `empty-table-header` | Minor | Low | R-? accessibility | Fixed on My leave; same pattern left on Approvals |
| A11Y-05 | SEO | `/robots.txt` returns the app shell (HTML), so Lighthouse reports "robots.txt is not valid". | Lighthouse `robots-txt` | Trivial | Low | - | Fixed (`frontend/public/robots.txt`) |
| A11Y-06 | Accessibility | Errors and success messages are all `role="status"`. An error that appears after submit is announced politely, and the field errors are not tied to their inputs with `aria-describedby` or `aria-invalid`. | source review of `InlineAlert.jsx`, `ApplyLeaveModal.jsx` | Minor | Medium | R-? accessibility | Open (not detected by either tool) |
| SEC-01 | Security | The access token is stored in `localStorage` (`leavedesk.token`); any script on the page can read it. No XSS sink was found in `frontend/src` (no `dangerouslySetInnerHTML`, `innerHTML` or `eval`), so the practical risk today is low, but one future XSS would expose every session. | source review, Playwright reads the key | Minor | Medium | R-? session security | Open |
| SEC-02 | Security | No security headers on API or UI responses: no CSP (ZAP Medium), no anti-clickjacking header (ZAP Medium), no `X-Content-Type-Options` (ZAP Low, 34 instances), no `Referrer-Policy`, no HSTS. | ZAP passive scan, Playwright `PC-01`, `docs/team/security.md` section 4 | Major | Medium | R-? transport/session security | Open |
| SEC-03 | Security | WK-08: a token of a deactivated user still works on endpoints that do not call `current_user()` (`GET /api/leave-types`). | `tests/team/security/test_token_of_deactivated_user.py` | Minor | Medium | R-? access control | Open |
| SEC-04 | Security | No rate limit or lockout on `POST /api/auth/login`; unlimited password guesses. | source review (`auth.py`, no limiter anywhere in `backend/app`) | Major | Medium | R-? authentication | Open |
| SEC-05 | Security | `JWT_SECRET_KEY` falls back to a fixed development string when the environment variable is missing (`config.py`). A deployment that forgets `.env` would accept forged tokens. | source review | Major | Medium | R-? deployment configuration | Open |
| SEC-06 | Security | `npm audit`: `react-router` / `react-router-dom` 6.30.6 has two moderate advisories (GHSA-wrjc-x8rr-h8h6 open redirect via backslash in `<Link>`/`useNavigate`; GHSA-337j-9hxr-rhxg `deserializeErrors` in SSR hydration). The app does not navigate to user-supplied URLs and does not use SSR hydration, so exposure is low. | `tests/team/security/reports/npm_audit.json` | Minor | Low | R-? dependency risk | Open (fix is a major upgrade to 7.18+) |
| SEC-07 | Security | The Google Fonts stylesheet is loaded from a third party without a Subresource Integrity attribute (ZAP Medium, `frontend/index.html`). SRI cannot be added because Google serves different CSS per browser; every page load also contacts Google. | ZAP passive scan | Minor | Low | R-? third-party content | Open (self-host the fonts) |
| SEC-08 | Security | Every API response carries `Server: Werkzeug/3.1.9 Python/3.12.10` (ZAP Low, 29 instances). | ZAP passive scan | Trivial | Low | R-? information disclosure | Open |
| PERF-01 | Performance | The tail latency of `POST /api/leave-requests` (p90 to max) depends strongly on how busy the host is: the same 1-user workload gave p95 994 ms (busy machine, limit 500 ms) and 242 ms (quieter machine). Five users reach about 8.3 creates/s against 5.4 for one user, so throughput is capped by the single-process dev server, SQLite and the 2-core host. Correctness held: 0 unexpected failures in 1461 creates. | `tests/team/perf/results/`, `docs/team/performance.md` | Minor | Medium | R-? performance | Open (repeat on an idle machine; a production WSGI server and database are the next change to try) |

## Root cause and fix for the two major findings

**DEF-A3-01 (balance year)**

- Why 1: the dialog shows "only 10 days remain" for a request in 2027 where 12 remain.
- Why 2: it reads the balance list it already holds (`balances` in `MyLeavePage`, loaded once).
- Why 3: that list comes from `GET /api/leave-balances` without a `year`, so the server answers for the current year.
- Why 4: the dialog's price check was written against "the balance" as if there were only one per leave type, while balances are per year.
- Why 5: no test covered a request in a different year than today, and the API tests (Area 2) correctly check the server, which already uses the request's year.
- Corrective action: load the balance for `start_date`'s year when the dates change (Apply dialog) and for `request.start_date`'s year (Review dialog), as the server does (`validate_leave_window(..., start.year)`).
- Preventive action: keep `UC-01-D1` and `UC-02-D1` in the suite. They are expected failures today and become failures-to-remove the day the defect is fixed, because Playwright reports an unexpected pass.

**A11Y-02/03 (dialog focus)**

- Why 1: keyboard users cannot reach the form without tabbing through the page.
- Why 2: focus is never moved when the dialog opens.
- Why 3: `Modal.jsx` renders the markup and handles Escape only.
- Why 4: the component was built and checked with a mouse; no automated tool checks focus order, so neither axe nor Lighthouse flagged it.
- Why 5: no keyboard test existed before this area.
- Corrective action: `Modal.jsx` moves focus into the dialog, keeps Tab inside, and returns focus to the opener.
- Preventive action: `U-03`, `U-04`, `U-05` run on every UI change.
