# Defensive security assessment (Area 3)

Scope: the team's local copy of LeaveDesk, synthetic data, seeded test accounts, no
production systems. Methods: source review, normal use through Playwright, ZAP in
**passive** mode (it only reads the traffic the tests produce), and dependency audits.
No active scanning, fuzzing or attack traffic was used.

Related files: [access_matrix.md](access_matrix.md) (expected decisions),
[access_results.md](access_results.md) (observed results with evidence),
[defects_area3.md](defects_area3.md) (all findings with severity and fix).

## 1. Attack surface

| Surface | Detail |
| --- | --- |
| Browser routes | `/login`, `/register`, `/`, `/leave`, `/approvals` (admin), `/team` (admin) |
| API | `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`, `GET /api/leave-types`, `GET /api/leave-balances`, `GET/POST /api/leave-requests`, `GET /api/leave-requests/{id}`, `POST .../cancel`, `POST .../review`, `GET /api/dashboard`, `GET /api/team`, `GET /api/health` |
| Session | JWT bearer token (HS256, 12 h) kept in `localStorage`; no cookies are set |
| Data | `User` (password hashes), `LeaveBalance.used_days`, `LeaveRequest` (reason text, status, reviewer note) |
| Roles | `employee`, `admin`; role is read from the database on each protected call |

## 2. Access decisions (6 marks: role checks)

Thirteen decisions were verified with Playwright (7 denied, 1 hidden as 404, 3 allowed,
2 unauthenticated); results and evidence files are in
[access_results.md](access_results.md). Highlights:

- An employee calling the review endpoint directly is refused with 403 and the request
  stays pending (AC-03). The UI redirect is not the control; the server checks the role.
- An admin cannot approve their own request (AC-05, 403).
- A request of another employee is invisible: 404, not 403, and none of its data in the
  body (AC-06).
- No token: 401 on the API (AC-12) and redirect to `/login` in the browser (AC-11).

## 3. Controls reviewed against the source

| Control | Observation | Corroborated by | Result |
| --- | --- | --- | --- |
| Role checks | `review_leave_request` checks `reviewer.is_admin`, then status, then `user_id != reviewer.id`; `/api/team` uses `@admin_required()`; cancel checks ownership. Role comes from the database, not from the token. | `backend/app/api/leaves.py`, `utils.py`; AC-03, AC-05, AC-08, AC-10 | Verified |
| Object-level access | `get_request_or_404` answers 404 for another employee's request; `list_balances` refuses another `user_id` with 403 | `leaves.py`; AC-06, AC-09 | Verified |
| Session storage | The JWT is kept in `localStorage`, which any script in the page can read. No cookie is used, so cookie attributes (`HttpOnly`, `Secure`, `SameSite`) do not apply and CSRF is not a risk for this design. No XSS sink exists in `frontend/src` (no `dangerouslySetInnerHTML`, `innerHTML`, `eval`), React escapes text. | `frontend/src/api/client.js`, grep of `src` | Finding SEC-01 (minor): exposure if XSS is ever introduced |
| Token validity | Expired token gives 401 "Your session has expired"; a deactivated user's token is refused by `/api/auth/me` and the leave endpoints but **not** by `GET /api/leave-types` (and any endpoint that never calls `current_user()`) | `tests/team/security/test_token_of_deactivated_user.py` | Finding SEC-03 (WK-08) |
| CORS | Only `http://localhost:5173` (from `CORS_ORIGINS`), no credentials | `backend/app/config.py`, `__init__.py` | Verified (a deployment must set the real origin) |
| Password storage | `werkzeug.security.generate_password_hash` / `check_password_hash` (salted hash); login answers the same 401 for unknown email and wrong password | `models.py`, `auth.py` | Verified |
| Input handling | All queries go through SQLAlchemy with bound parameters; `q` is bound into `ILIKE` (wildcards are not escaped: WK-03, a correctness issue, not injection) | `leaves.py` | Verified (no injection path found) |
| Brute force | No rate limit or lockout on `POST /api/auth/login` | `auth.py`, no limiter in `backend/app` | Finding SEC-04 |
| Secrets | `JWT_SECRET_KEY` defaults to a fixed development string if no environment variable is set | `config.py` | Finding SEC-05 |
| Security headers | None of CSP, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, HSTS is set by the API or the UI server; `Server` discloses `Werkzeug/3.1.9 Python/3.12.10` | ZAP (section 4), `PC-01` | Findings SEC-02, SEC-08 |

## 4. OWASP ZAP passive scan

**Setup.** OWASP ZAP 2.17.0 (Docker image `ghcr.io/zaproxy/zaproxy:stable`, digest
`sha256:9624669db72f54d86c4b46a7064518bd9bf79d8c61a4c31befa9923489f328af`) in daemon mode, bound to
`127.0.0.1:8080`. **Only the passive scanner ran**: no spider, no active scan, no fuzzing. The Playwright
browser was started with `proxy: http://127.0.0.1:8080` (`ZAP_PROXY`) so every request of the tests passed through
ZAP, and ZAP only read the traffic.

Tests that ran through the proxy (all 8 passed) cover both workflows: W1 `UC-01-M1`, `UC-01-E3`, `U-01`;
W2 `UC-02-M1`, `UC-02-A2`, `U-02`, `AC-04`; and `AC-11` (no session). The UI was the production build,
reached as `http://host.docker.internal:5173`; the API calls of the tests also went through the UI's `/api`
proxy, so ZAP saw both. ZAP recorded **37 URLs** (every API endpoint of both workflows, including `/auth/login`,
`/leave-requests`, `/leave-requests/{id}/review` and `/cancel`).

Command used (also in `tests/team/e2e/README.md`):

```powershell
docker run -d --name zap -p 127.0.0.1:8080:8080 ghcr.io/zaproxy/zaproxy:stable zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.disablekey=true -config "api.addrs.addr.name=.*" -config api.addrs.addr.regex=true
$env:ZAP_PROXY="http://127.0.0.1:8080"; $env:UI_URL="http://host.docker.internal:5173"; $env:API_URL="http://host.docker.internal:5173"
npx playwright test --project=use-cases --project=usability --project=security -g "UC-01-M1|UC-02-M1|U-01|U-02|AC-04"
```

(The UI server was started with `--host 0.0.0.0` and `__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=host.docker.internal`
only for this run so the container could reach it, and was restarted on localhost afterwards.)

**Result:** 82 alerts, **0 High, 9 Medium, 63 Low, 10 Informational**, in 9 distinct kinds. Raw export:
`tests/team/security/reports/zap/` (`alerts.json`, `alerts_summary.json`, `urls.json`, `zap_passive_report.html`).

| ZAP alert | Risk | Instances | Affected component | Evidence | Likely impact | Recommended correction | Id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Content Security Policy (CSP) Header Not Set | Medium | 3 (every HTML page) | UI server (Vite preview here; any static host in production) | no `Content-Security-Policy` header on `/login`, `/leave`, `/approvals` | if a script is ever injected nothing limits what it can load or read (the token is in `localStorage`) | send a CSP such as `default-src 'self'; style-src 'self' fonts.googleapis.com; font-src fonts.gstatic.com` | SEC-02 |
| Missing Anti-clickjacking Header | Medium | 3 | same | no `X-Frame-Options` and no `frame-ancestors` | the pages can be framed by another site (clickjacking on Approve / Reject) | `Content-Security-Policy: frame-ancestors 'none'` (or `X-Frame-Options: DENY`) | SEC-02 |
| Sub Resource Integrity Attribute Missing | Medium | 3 | `frontend/index.html`, `<link href="https://fonts.googleapis.com/css2?...">` | stylesheet loaded from a third party without `integrity` | a compromised or changed third-party stylesheet is trusted blindly; every page load also tells Google who loaded the page | self-host the two fonts (and drop the third-party link); SRI cannot be used here because Google serves different CSS per browser | SEC-07 |
| X-Content-Type-Options Header Missing | Low | 34 | API (Flask) and UI server | no `X-Content-Type-Options: nosniff` on API JSON and on assets | a browser may guess the type of a response; low here because API replies are JSON | set `X-Content-Type-Options: nosniff` in an `after_request` handler and on the static host | SEC-02 |
| Server Leaks Version Information via "Server" Header | Low | 29 | API (Werkzeug) | `Server: Werkzeug/3.1.9 Python/3.12.10` on every API response | tells an attacker the exact framework and Python version to look up known issues for | remove or generalise the header at the reverse proxy; the development server should not be exposed at all | SEC-08 |
| Information Disclosure - Sensitive Information in URL | Informational | 1 | `GET /api/leave-balances?user_id=3` | numeric `user_id` in a query string | none: the value is an internal id, not a secret, and the server checks who may ask (AC-09 returns 403 for an employee) | none needed; the finding is a false positive | - |
| Authentication Request Identified | Informational | 4 | `POST /api/auth/login` | form fields `email`, `password` | ZAP notes where authentication happens; no issue | none | - |
| Session Management Response Identified | Informational | 2 | `POST /api/auth/login` response | JSON field `access_token` | confirms the session token is returned in the body (not in a cookie), as in the source review | none; see SEC-01 for where it is stored | SEC-01 |
| Modern Web Application | Informational | 3 | UI | single-page app with a module script | ZAP notes that its crawler would need the AJAX spider; irrelevant for a passive run | none | - |

What ZAP did **not** report: any cookie issue (there are no cookies), any High alert, any error in the
workflows. This agrees with the Playwright passive checks `PC-01` / `PC-02`
(`tests/team/e2e/reports/security/passive_headers.json`, `passive_cors.json`): none of the five security
headers present, no `Set-Cookie`, the token is the only `localStorage` key, and a foreign `Origin` receives no
`Access-Control-Allow-Origin` while `http://localhost:5173` does.

## 5. Dependency audit

Run on 24 Nov 2026. Raw output: `tests/team/security/reports/`.

**Python** (`pip-audit` 2.10.1, `pip-audit -r backend_installed_versions.txt --no-deps --disable-pip`):
57 packages and exact versions checked (list in `backend_installed_versions.txt`), including the
runtime ones: Flask 3.1.3, Werkzeug 3.1.9, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.1.9,
Flask-JWT-Extended 4.7.4, PyJWT 2.15.1, Flask-Cors 6.0.5, PyMySQL 1.2.4, python-dotenv 1.2.4,
itsdangerous 2.2.0, Jinja2 3.1.6, MarkupSafe 3.0.4, click 8.5.1, blinker 1.9.0.
**Result: No known vulnerabilities found.** This is a verified control: no action needed.
(The list also contains the test and audit tools installed in the same virtual environment.)

**JavaScript** (`npm audit --json` in `frontend`, npm registry advisory data): 145
installed packages (37 production, 109 development) checked, among them react 18.3.1,
react-dom 18.3.1, react-router-dom 6.30.6, axios 1.21.0, lucide-react 0.468.0, vite 6.4.5,
@vitejs/plugin-react 4.7.0. **Result: 2 moderate, 0 high, 0 critical**, both through the same package:

| Component | Evidence | Likely impact here | Recommended correction |
| --- | --- | --- | --- |
| `react-router` (via `react-router-dom` 6.30.6) | GHSA-wrjc-x8rr-h8h6: open redirect through a backslash in `<Link>` / `useNavigate` | Low. The app only navigates to fixed internal paths; no redirect target comes from user input | Upgrade to `react-router-dom` 7.18 or later (major version, needs a regression run of the UI tests) |
| `react-router` | GHSA-337j-9hxr-rhxg: arbitrary constructor injection in `deserializeErrors()` during server-side-rendering hydration | None today: the app is a client-side single-page app with no SSR | Same upgrade |

## 6. Summary

| Id | Finding | Severity |
| --- | --- | --- |
| SEC-01 | Token in `localStorage` | Minor |
| SEC-02 | No security headers (CSP, anti-clickjacking, nosniff): ZAP Medium x2, Low x1 | Major |
| SEC-03 | Deactivated user's token works on `/api/leave-types` (WK-08) | Minor |
| SEC-04 | No login rate limit | Major |
| SEC-05 | Default JWT secret | Major |
| SEC-06 | react-router advisories | Minor |
| SEC-07 | Google Fonts stylesheet loaded from a third party without integrity (ZAP Medium) | Minor |
| SEC-08 | `Server` header discloses framework and Python version (ZAP Low) | Low |

Verified controls with no finding: role checks on review, cancel, balances and team endpoints;
hidden foreign requests (404); 401 without token; salted password hashing; parameterised queries;
restricted CORS; no vulnerable Python packages.
