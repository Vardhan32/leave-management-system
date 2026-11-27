# Access matrix (Area 3, defensive security)

Local copy of LeaveDesk, synthetic data and test accounts only. Roles:

- **employee** - `demo@leavedesk.in` (and `rohan.iyer@leavedesk.in` as "another employee")
- **admin** - `admin@leavedesk.in` (HR admin)
- **anonymous** - no session

## 1. Routes and data in the two workflows

| Workflow | Browser route | API endpoint | Data read or changed |
| --- | --- | --- | --- |
| W1 Apply | `/leave` (dialog "Request time off") | `GET /api/leave-types`, `GET /api/leave-balances`, `POST /api/leave-requests`, `GET /api/leave-requests` | reads `LeaveType`, `LeaveBalance`; creates `LeaveRequest` (pending) |
| W2 Review | `/approvals` (dialog "Review leave request") | `GET /api/leave-requests`, `GET /api/leave-balances?user_id=`, `POST /api/leave-requests/{id}/review` | reads `LeaveRequest`, `LeaveBalance`; changes `LeaveRequest.status`, `LeaveBalance.used_days` |
| Cancel | `/leave` (dialog "Leave request") | `POST /api/leave-requests/{id}/cancel` | changes `LeaveRequest.status`, `LeaveBalance.used_days` |
| Session | `/login`, all routes | `POST /api/auth/login`, `GET /api/auth/me` | reads `User`; JWT kept in `localStorage` (`leavedesk.token`) |
| Directory | `/team` | `GET /api/team` | reads all users and balances (admin only) |

## 2. Expected decisions

| Id | Role | Action | Expected | Source of the rule |
| --- | --- | --- | --- | --- |
| AC-01 | employee | open `/approvals` | denied: redirected to `/` | `AdminOnly` in `frontend/src/App.jsx` |
| AC-02 | employee | open `/team` | denied: redirected to `/` | `AdminOnly` in `frontend/src/App.jsx` |
| AC-03 | employee | `POST /api/leave-requests/{id}/review` | denied: 403 | `review_leave_request`, `reviewer.is_admin` |
| AC-04 | admin | approve another employee's pending request | allowed: status `approved` | `review_leave_request` |
| AC-05 | admin | approve their own request | denied: 403 | `leave_request.user_id == reviewer.id` |
| AC-06 | employee | `GET /api/leave-requests/{id}` of another employee | hidden: 404 | `get_request_or_404` |
| AC-07 | employee | cancel own pending request | allowed: 200, `cancelled` | `cancel_leave_request` |
| AC-08 | employee | cancel another employee's request | denied: 403 | `cancel_leave_request`, owner check |
| AC-09 | employee | `GET /api/leave-balances?user_id=<other>` | denied: 403 | `list_balances` |
| AC-10 | employee | `GET /api/team` | denied: 403 | `@admin_required()` in `dashboard.py` |
| AC-11 | anonymous | open `/leave` | denied: redirected to `/login` | `Protected` in `App.jsx` |
| AC-12 | anonymous | `GET /api/leave-requests` | denied: 401 | `@jwt_required()` |
| AC-13 | admin | open `/approvals` | allowed | `AdminOnly` |

Allowed actions: AC-04, AC-07, AC-13. Denied or hidden actions: all others.

## 3. How each decision is verified

`tests/team/e2e/specs/security/access-control.spec.ts` runs every row through
Playwright (browser for the route checks, the API request fixture for the
endpoint checks). Each test records role, action, expected, observed and an
evidence file (screenshot or the saved HTTP reply) in
`tests/team/e2e/reports/access/`. The observed results are in
[access_results.md](access_results.md).

The UI redirect is a convenience, not the control: the endpoint checks
(AC-03, AC-05, AC-08, AC-09, AC-10) show the server enforces the same rules
without the UI.
