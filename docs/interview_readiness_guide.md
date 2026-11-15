# Leave Management System — Technical Architecture & Interview Preparation Guide

This guide is designed for technical interviewers, hiring managers, and software engineers reviewing the **Leave Management System** repository. It provides an in-depth architectural breakdown of the role-based workflow, details concurrency-safe leave balance deductions, explains edge-case validations, and provides 40 comprehensive Q&As covering Flask, SQLAlchemy, JWT RBAC (Role-Based Access Control), and transaction isolation.

---

## 1. System Architecture & Component Design

The Leave Management System is an enterprise workflow platform that automates employee leave requests, approval hierarchies, balance tracking, and audit logging.

```
+-----------------------------------------------------------------------------------+
|                           Client Tier (React 18 + Vite)                           |
|  - Role-Aware Routing: Employee Dashboard vs Admin Approval Console               |
|  - Interactive calendar date pickers with weekend and past-date disabling        |
|  - Real-time leave balance cards (Allocated, Used, Remaining) per leave type      |
|  - Dynamic filters: Status (pending/approved/rejected/cancelled), Department, Year|
+-----------------------------------------------------------------------------------+
                                           |  JSON over HTTP (RESTful API)
                                           v
+-----------------------------------------------------------------------------------+
|                        Application Tier (Flask + Flask-JWT-Extended)              |
|  - Blueprints: auth_bp (/api/auth), leaves_bp (/api), dashboard_bp (/api/dashboard)|
|  - RBAC Middleware: JWT claims enforce employee vs admin permissions              |
|  - Service Layer: services.py (validate_leave_window, working_days, approve_request)|
|  - Concurrency Lock: SELECT ... FOR UPDATE on LeaveBalance and LeaveRequest        |
+-----------------------------------------------------------------------------------+
                                           |  SQLAlchemy ORM
                                           v
+-----------------------------------------------------------------------------------+
|                        Data Tier (Relational Storage Engine)                      |
|  - Production: MySQL 8 (InnoDB, composite indexes, CHECK constraints)             |
|  - Test / CI: In-Memory SQLite with isolated test databases                       |
|  - Entities: users, leave_types, leave_balances, leave_requests                   |
|  - Constraints: uq_balance_user_type_year, ck_leave_requests_status               |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Business Rules & Concurrency Safeguards

### 1. Dual-Phase Balance Verification & Race Condition Protection
- **The Problem:** In an enterprise organization, an employee might have 3 days of Casual Leave remaining. They submit two separate requests: Request A for 2 days and Request B for 2 days. Both requests are valid at submission time. If two administrators simultaneously approve Request A and Request B, a naive system would deduct $2 + 2 = 4$ days, leaving the employee at $-1$ days!
- **The Solution:**
  1. **Phase 1 (Submission):** `validate_leave_window` checks that `balance.remaining_days >= requested_days`.
  2. **Phase 2 (Approval with Row Locking):** In `approve_request`:
     ```python
     leave_request = (
         LeaveRequest.query.filter_by(id=request_id).with_for_update().first()
     )
     balance = balance_for(
         leave_request.user,
         leave_request.leave_type,
         leave_request.start_date.year,
         for_update=True,
     )
     if balance.remaining_days < leave_request.days:
         return {"leave_type_id": "Insufficient balance."}
     balance.used_days += leave_request.days
     ```
  - Using `with_for_update()` locks both the `leave_requests` and `leave_balances` rows until the transaction commits. The second approval is forced to wait, re-evaluates the updated `used_days`, and is cleanly rejected with HTTP `422`.

### 2. Overlapping Date Range Detection
- To prevent employees from submitting conflicting leaves, `overlapping_request` executes an efficient interval overlap check:
  $$\text{Existing.start\_date} \le \text{New.end\_date} \quad \text{AND} \quad \text{Existing.end\_date} \ge \text{New.start\_date}$$
  Filtered across `status.in_(('pending', 'approved'))`.

### 3. Business Day (Weekday) Calculation
- The system automatically counts only Monday–Friday (`cursor.weekday() < 5`) as consumed leave days. An employee requesting Friday to Monday is charged exactly 2 days, not 4 days.

### 4. Enterprise RBAC & Separation of Duties
- **Admin Self-Review Prevention:** An administrator who applies for leave cannot approve their own request (`leave_request.user_id == reviewer.id` raises HTTP `403 Forbidden`). Another administrator must review it.
- **Unauthorized Cancellation Prevention:** Only the employee who applied can cancel their request, and cancellation is prohibited once the leave start date has passed (`start_date <= date.today()`).
- **Balance Restoration:** Cancelling an approved request automatically restores the deducted days to `balance.used_days`.

---

## 3. 40 Technical Interview Questions & Answers

### Part 1: Core Fundamentals & Workflow Mechanics (1–15)

#### Q1: What problem does this application solve?
**Answer:** It centralizes organizational leave management, allowing employees to apply for leave, track remaining quotas, and view statuses, while providing managers with approval consoles, conflict detection, and department reports.

#### Q2: What backend framework and libraries were chosen?
**Answer:** Python with Flask, Flask-SQLAlchemy, and Flask-JWT-Extended.

#### Q3: What are the two primary user roles in the system?
**Answer:** `employee` and `admin`.

#### Q4: What leave statuses are supported in the request lifecycle?
**Answer:** Four mutually exclusive statuses: `pending`, `approved`, `rejected`, and `cancelled`.

#### Q5: What standard leave types are seeded into the system?
**Answer:**
1. Casual Leave (`CASUAL`): 12 days per year.
2. Sick Leave (`SICK`): 10 days per year.
3. Earned Leave (`EARNED`): 15 days per year.

#### Q6: How are leave balances initialized for employees?
**Answer:** In `services.balance_for()`, when a user accesses balances or submits a request for a calendar year, any missing `LeaveBalance` record is automatically initialized with `allocated_days = leave_type.default_days` and `used_days = 0`.

#### Q7: How is `remaining_days` calculated?
**Answer:** As a calculated property: `max(self.allocated_days - self.used_days, 0)`.

#### Q8: How does the system handle weekends?
**Answer:** `working_days(start, end)` iterates through dates and increments the count only when `cursor.weekday() < 5` (Monday through Friday). Saturday and Sunday are never deducted from an employee's leave quota.

#### Q9: What happens if an employee submits a leave request covering only a weekend?
**Answer:** `working_days()` returns 0, and the API returns HTTP `422 Unprocessable Entity` with the error: "The selected range has no working days (Mon–Fri)."

#### Q10: Why are leave requests restricted to a single calendar year?
**Answer:** Leave allocations (e.g. 12 casual days) are legally tied to specific calendar years. Spanning across Dec 31 to Jan 2 would complicate year-end balance rollovers and quota deductions, so cross-year requests must be submitted as two separate requests.

#### Q11: Can an employee apply for leave in the past?
**Answer:** No. `validate_leave_window` enforces `start_date >= date.today()`. Historical leave applications return HTTP 422.

#### Q12: How are overlapping requests detected?
**Answer:** Using the SQL condition: `start_date <= :new_end AND end_date >= :new_start` for requests where status is either `pending` or `approved`.

#### Q13: Can an employee cancel their own approved leave?
**Answer:** Yes, provided the leave has not yet started (`start_date > date.today()`). When cancelled, the previously deducted days are credited back to `balance.used_days`.

#### Q14: Can an administrator approve their own leave request?
**Answer:** No. In `review_leave_request`, if `leave_request.user_id == reviewer.id`, the server raises HTTP `403 Forbidden` ("You cannot review your own leave request.").

#### Q15: What HTTP status code is returned when reviewing a non-pending request?
**Answer:** HTTP `409 Conflict` ("Only pending requests can be reviewed.").

---

### Part 2: Intermediate Architecture & Database Integrity (16–30)

#### Q16: Why is pessimistic locking (`with_for_update()`) used during review?
**Answer:** If multiple admins review conflicting requests or if an employee cancels while an admin approves, pessimistic locking serializes the operations, preventing lost updates or overdrafted balances.

#### Q17: What unique constraint protects the `leave_balances` table?
**Answer:** A composite unique constraint: `db.UniqueConstraint("user_id", "leave_type_id", "year", name="uq_balance_user_type_year")`. This guarantees that an employee can never have duplicate balance rows for the same leave type in the same year.

#### Q18: What database check constraint is enforced on `leave_requests`?
**Answer:** `db.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'cancelled')", name="ck_leave_requests_status")` ensures that no invalid status string can ever be written to the database.

#### Q19: What is the purpose of `db.session.flush()` vs `db.session.commit()`?
**Answer:** `flush()` sends SQL operations to the database transaction buffer, generating primary keys and checking constraints, without closing the transaction. `commit()` permanently writes all flushed changes and releases database locks.

#### Q20: Why are foreign keys on `leave_requests.reviewed_by_id` set to `ondelete="SET NULL"`?
**Answer:** If an admin leaves the company and their user record is deleted, historical leave request records must retain their approval history without being cascade-deleted.

#### Q21: Why does `leave_requests.user_id` have `ondelete="CASCADE"`?
**Answer:** If an employee record is permanently purged, all of their personal leave requests are deleted along with them.

#### Q22: How is role information communicated in JWT tokens?
**Answer:** During login, user identity (ID) is encoded into the JWT `sub` claim. When routes require authorization, `current_user()` retrieves the user and checks `user.role == 'admin'`.

#### Q23: How does the admin dashboard aggregate department statistics?
**Answer:** `dashboard.py` executes SQL group-by queries joining `users` and `leave_requests` to aggregate pending reviews, employees on leave today, and department-level utilization rates.

#### Q24: How does search work when an admin searches leave requests?
**Answer:** If `user.is_admin`, the search joins the `users` table and searches across `LeaveRequest.reason`, `User.name`, and `User.email` using `ilike %pattern%`. Non-admin searches search only within their own reasons.

#### Q25: Why is `rejection` required to have a note?
**Answer:** Business compliance requires clear justification when denying time off. The validator returns HTTP 422 if an admin rejects without supplying a `note`.

#### Q26: How does pagination protect the `/leave-requests` endpoint?
**Answer:** Requests use Flask-SQLAlchemy's `.paginate(page=page, per_page=per_page, error_out=False)`, preventing unbounded queries and returning total page metadata for frontend controls.

#### Q27: How is timezone consistency maintained?
**Answer:** The server standardizes all operational timestamps using `utcnow()`, storing naive UTC datetimes uniformly across SQLite and MySQL.

#### Q28: How does the frontend handle authentication state?
**Answer:** `AuthContext` provides React components with user details and role flags (`isAdmin`). Axios interceptors automatically attach `Authorization: Bearer <token>` to requests and trigger global logout upon receiving HTTP 401.

#### Q29: What automated tests protect this system?
**Answer:** 53 comprehensive unit and integration tests using pytest covering auth, role restrictions, date validations, overlap detection, approval workflows, balance integrity, and cancellation rules.

#### Q30: How are tests isolated?
**Answer:** An in-memory SQLite database (`sqlite://`) is created and destroyed per test session with mock leave types pre-seeded.

---

### Part 3: Senior Architecture, Enterprise Workflows & Scalability (31–40)

#### Q31: How would you implement Statutory Holiday calendars (e.g., Diwali, Christmas)?
**Answer:**
1. Create a `Holiday` table with `(date, name, optional_department)`.
2. Update `working_days(start, end)` to check both `cursor.weekday() < 5` and `cursor not in holiday_set`.
3. Statutory holidays falling on weekdays would automatically not consume leave balance days.

#### Q32: How would you handle Half-Day leaves (First Half / Second Half)?
**Answer:**
1. Change `days` column in `leave_requests` and `allocated_days`/`used_days` in `leave_balances` from `Integer` to `Numeric(4, 1)`.
2. Add an `is_half_day` boolean flag and a `half_day_period` enum (`morning` / `afternoon`).
3. Deduct `0.5` days from the balance.

#### Q33: How would you implement multi-level approval hierarchies (e.g. Team Lead -> Department Head -> HR)?
**Answer:**
1. Create an `ApprovalStep` table linking `leave_request_id`, `approver_id`, `step_number`, and `status`.
2. A request transitions from `pending_lead` to `pending_hr` before reaching `approved`.
3. Balance deduction occurs only when the final step completes.

#### Q34: How would you implement annual leave balance carryover (rollover)?
**Answer:**
1. Configure an annual cron job running at midnight on December 31st.
2. For each active employee, calculate `unused_earned = min(balance.remaining_days, max_carryover_limit)`.
3. Initialize the next year's `EARNED` balance with `allocated_days = default_days + unused_earned`.

#### Q35: How would you prevent notification spam and notify managers of pending approvals?
**Answer:**
1. Emit an event `LeaveRequestCreatedEvent` onto an asynchronous message queue (e.g., Celery/RabbitMQ).
2. The worker compiles a daily digest of pending approvals for each manager or sends instant Slack/Teams webhooks.

#### Q36: How does the system handle concurrent leave submissions by the same employee?
**Answer:**
- Even if an employee sends two rapid API requests, the unique constraint on `(user_id, start_date)` or the `overlapping_request` check combined with database transactions prevents duplicate concurrent bookings.

#### Q37: How would you implement compensatory off (Comp-Off) grants?
**Answer:**
1. Create a `CompOffGrant` table recording overtime dates and manager approvals.
2. Once approved, increment the employee's `CASUAL` or dedicated `COMP_OFF` balance for the current year.

#### Q38: How do you verify that non-admin employees cannot view other employees' leave histories?
**Answer:** `list_leave_requests` explicitly filters `query = query.filter(LeaveRequest.user_id == user.id)` when `not user.is_admin`. If a non-admin attempts to pass `user_id=X`, the parameter is ignored for employees.

#### Q39: What auditing is required for enterprise HR compliance (SOX/ISO 27001)?
**Answer:**
1. Retain immutable logs of all status transitions, recording `changed_by_id`, `old_status`, `new_status`, `timestamp`, and `IP address`.
2. Prevent hard-deletions of any leave transaction for at least 7 years.

#### Q40: What are the primary engineering strengths of this Leave Management System?
**Answer:**
1. Bulletproof state machine: strict transitions (`pending -> approved/rejected/cancelled`) with zero ambiguous states.
2. Guaranteed balance integrity: dual-phase validation and pessimistic row locking prevent race conditions and overdrafts.
3. Clean separation of concerns: clear separation between HTTP controllers, domain service validation, and database models.
4. 53 exhaustive automated tests verifying every edge case and security boundary.
