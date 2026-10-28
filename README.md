# LeaveDesk — Employee Leave Management

[![CI](https://github.com/Vardhan32/leave-management-system/actions/workflows/ci.yml/badge.svg)](https://github.com/Vardhan32/leave-management-system/actions/workflows/ci.yml)

LeaveDesk is a full-stack leave management app for a small team. Employees can
see their yearly balances, request time off, and track decisions. Managers get a
single queue for approvals, with the requester's remaining balance shown next to
the dates before they approve anything.

The API is Flask with Flask-SQLAlchemy and JWT authentication, backed by a MySQL 8
schema. The client is a React single-page app built with Vite. SQLite is the
default for local development and tests, so the project runs without a database
server.

![Admin dashboard](docs/screenshots/admin-dashboard.png)

## Features

- JWT authentication with employee and admin roles, plus self-registration
- Year-based balances for casual (12), sick (10), and earned (15) leave
- Requests count weekdays only; weekends are skipped automatically
- Validation for past dates, reversed ranges, cross-year requests, overlapping
  leave, and insufficient balance
- Approval queue with tabs for pending, approved, rejected, and cancelled requests
- Review modal shows the employee's balance and what it will be after approval
- Rejections require a note; the note is stored on the request and shown to the employee
- Employees can cancel pending or upcoming approved leave; approved leave returns
  the days to the balance
- Employee dashboard with balances, upcoming time off, and recent requests
- Admin dashboard with headcount, pending count, who is away today, and recent decisions
- Team directory with per-person balances, availability, and next booked leave
- Search, filters, and pagination on the request lists
- Responsive layout, keyboard-friendly modals, and explicit loading, empty, and
  error states

| Employee dashboard | My leave |
| --- | --- |
| ![Employee dashboard](docs/screenshots/employee-dashboard.png) | ![My leave](docs/screenshots/my-leave.png) |

The request form previews the working-day count before submitting, and the detail
view keeps the decision and note together with the original request:

| Request time off | Request detail |
| --- | --- |
| ![Apply for leave](docs/screenshots/apply-leave.png) | ![Leave request detail](docs/screenshots/request-detail.png) |

| Approval queue | Team directory |
| --- | --- |
| ![Approvals](docs/screenshots/approvals.png) | ![Team directory](docs/screenshots/team.png) |

## Stack

| Layer | Tools |
| --- | --- |
| API | Python 3.12, Flask 3.1, Flask-SQLAlchemy 3.1, Flask-JWT-Extended, Flask-Cors |
| Database | MySQL 8 with PyMySQL; SQLite fallback for local development and tests |
| Frontend | React 18, Vite 6, React Router 6, Axios, Lucide icons, plain CSS |
| Tests | pytest, Flask test client |
| CI | GitHub Actions (API tests and production frontend build) |

## Project layout

```text
backend/
  app/
    api/              auth, leave requests, dashboards
    models.py         User, LeaveType, LeaveBalance, LeaveRequest
    services.py       working-day, balance, overlap, and approval logic
    utils.py          validation, auth helpers, pagination
    seed.py           demo team, balances, and requests
    config.py         environment configuration
  tests/              53 API tests
  schema.sql          MySQL DDL
  run.py              development entry point (port 5001)
frontend/
  src/
    api/              Axios client and token handling
    auth/             session context and protected routes
    components/       layout, modals, badges, form pieces
    pages/            dashboards, leave, approvals, team, auth, 404
    utils/            date and leave-format helpers
docs/screenshots/
.github/workflows/
```

## Running locally

### 1. Database

For MySQL 8, create the database and tables from the schema:

```bash
mysql -u root -p < backend/schema.sql
```

Then create the application user, or reuse an existing one:

```sql
CREATE USER 'leave_desk'@'localhost' IDENTIFIED BY 'leave_desk';
GRANT ALL PRIVILEGES ON leave_desk.* TO 'leave_desk'@'localhost';
FLUSH PRIVILEGES;
```

Copy `backend/.env.example` to `backend/.env` and adjust the credentials:

```text
DATABASE_URL=mysql+pymysql://leave_desk:leave_desk@localhost:3306/leave_desk?charset=utf8mb4
CORS_ORIGINS=http://localhost:5173
SECRET_KEY=replace-this-in-production
JWT_SECRET_KEY=replace-this-in-production-too
```

If `DATABASE_URL` is unset, the API uses `backend/leave.db` instead. That is the
quickest way to try the app without installing MySQL; the seeded demo data works
the same way on both databases.

### 2. API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app run:app init-db
flask --app run:app seed-db
python run.py
```

`seed-db` creates the tables, leave types, 10 users, their balances, and 28
requests. It is a no-op if the demo employee already exists. The API listens on
`http://localhost:5001`; `GET /api/health` is a quick check.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to the Flask server on port
5001, so no client-side base URL configuration is needed.

### Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Employee | `demo@leavedesk.in` | `demo1234` |
| Admin | `admin@leavedesk.in` | `admin1234` |

The sign-in screen also has "Employee" and "HR admin" buttons that fill these
credentials for you.

![Sign in](docs/screenshots/login.png)

## Tests

```bash
cd backend
pytest -q
```

The suite runs against an in-memory SQLite database and covers registration and
login, authorization boundaries, request validation, balance handling, overlapping
dates, approvals, rejections, cancellation, and both dashboards. Current result:
**53 passed**.

## API reference

All endpoints except `/api/health`, `/api/auth/register`, and `/api/auth/login`
require an `Authorization: Bearer <token>` header.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Health check |
| POST | `/api/auth/register` | Create an employee account and return a token |
| POST | `/api/auth/login` | Sign in and return a token |
| GET | `/api/auth/me` | Current user profile |
| GET | `/api/leave-types` | List the configured leave types |
| GET | `/api/leave-balances` | Balances for the signed-in user (`year`, admins may pass `user_id`) |
| GET | `/api/leave-requests` | List requests (`status`, `leave_type_id`, `year`, `q`, `page`, `per_page`) |
| POST | `/api/leave-requests` | Submit a request |
| GET | `/api/leave-requests/:id` | Fetch one request (owner or admin) |
| POST | `/api/leave-requests/:id/cancel` | Cancel a pending or upcoming approved request |
| POST | `/api/leave-requests/:id/review` | Approve or reject a pending request (admin) |
| GET | `/api/dashboard` | Role-specific dashboard payload |
| GET | `/api/team` | Team directory with balances and availability (admin) |

Admin-only list filters also accept `user_id` and `department`.

Create a request:

```json
{
  "leave_type_id": 1,
  "start_date": "2026-11-23",
  "end_date": "2026-11-24",
  "reason": "Cousin's wedding in Hyderabad. Travel on Friday evening."
}
```

Review a request:

```json
{
  "decision": "approve",
  "note": "Have a good time. Please hand over the design review."
}
```

`decision` is `approve` or `reject`. A rejection note is required.

Validation failures return `422` with field-level messages the UI can map back
to the form:

```json
{
  "message": "Please check the submitted fields.",
  "errors": {
    "start_date": "Leave cannot start in the past."
  }
}
```

Missing records return `404`, permission failures return `403`, and conflicting
state changes (reviewing an already-decided request, cancelling started leave)
return `409`.

## Leave rules

- A request is stored as a start date, end date, and the number of **working
  days** in that inclusive range. Saturday and Sunday never count.
- A request must start today or later and stay inside one calendar year.
- A request cannot overlap another pending or approved request for the same person.
- The requested number of days must fit in the remaining balance at submission
  time. Pending requests do not reduce the balance yet.
- Approval re-checks the balance, adds the days to `used_days`, and records the
  reviewer, timestamp, and note. Admins cannot review their own requests.
- Rejection records the reviewer and a required note, and leaves the balance alone.
- Employees can cancel pending requests and approved requests that have not
  started. Cancelling approved leave subtracts its days from `used_days`.
- Balances are created on demand per user, leave type, and year, so a new calendar
  year starts with the full allocation.
- Tokens expire after 12 hours (configurable with `JWT_EXPIRES_HOURS`).

## Data model

```text
User 1 ──── * LeaveRequest * ──── 1 LeaveType
User 1 ──── * LeaveBalance  * ──── 1 LeaveType
User 1 ──── * LeaveRequest (reviewer)
```

`LeaveBalance` has a unique key on `(user_id, leave_type_id, year)`. `LeaveRequest`
stores the computed `days`, status, reason, and review audit fields. The MySQL
schema adds foreign keys, a status check constraint, and indexes for user/status
and date-range lookups.

## Implementation notes

- The date, overlap, and balance rules live in `app/services.py` and are shared by
  request creation, approval, and cancellation instead of being duplicated in routes.
- `Validator` collects every field error before raising, so the client gets one
  response with all problems rather than one at a time.
- Passwords are hashed with Werkzeug's `generate_password_hash`; JWT identities are
  stored as strings for compatibility with Flask-JWT-Extended 4.x.
- The React client attaches the token in an Axios interceptor and clears the
  session on a `401`, so expired tokens return the user to the sign-in screen.
- Lists debounce search input and ignore stale responses; every page handles
  loading, empty, and error states explicitly.
- The interface uses a warm cream, navy, and coral palette with Fraunces and Inter,
  with system serif and sans fallbacks when the web fonts are unavailable.
- SQLite keeps the demo portable, while `schema.sql` and the SQLAlchemy types target
  MySQL 8 for deployment.

## Possible next steps

- Email or Slack notifications when a request is submitted or decided
- Half-day leave and a team holiday calendar
- Admin user management and custom leave-type allocations
- CSV export and payroll integration

## License

MIT
