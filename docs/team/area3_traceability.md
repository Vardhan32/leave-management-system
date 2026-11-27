# Area 3 traceability (browser tests to requirements)

Generated from tests/team/e2e/reports/e2e_traceability.csv (tags on each Playwright test) and tests/team/api/support/requirements.py.
Requirement text is shortened; ids follow the shared test basis. Area 2 covers the same ids at API level.

| Requirement | Browser tests (flow ids) | Count |
| --- | --- | --- |
| FR-01 - Employee submits a leave request (type, start, end, reason); it is sto... | UC-01-M1, UC-01-A1, UC-01-A2, UC-01-A3, U-01, U-03, U-04, U-05 | 8 |
| FR-02 - Submitted fields are validated (type exists, ISO dates, reason 10-500 ... | UC-01-M1, UC-01-E2 | 2 |
| FR-03 - Requests that start in the past, end before they start, span two years... | UC-01-E1, UC-01-E5 | 2 |
| FR-04 - A request may not overlap the employee's own pending or approved reque... | UC-01-E4 | 1 |
| FR-05 - A request may not exceed the remaining balance of its leave type. | UC-01-E3, UC-01-D1, U-01 | 3 |
| FR-06 - Employees can read their own balances and requests, with filters and p... | - | 0 |
| FR-07 - An admin approves a pending request; used days grow by the request's d... | UC-02-M1, UC-02-A1, UC-02-A3, U-02, AC-04 | 5 |
| FR-08 - An admin rejects a pending request with a required note; the balance d... | UC-02-A2, UC-02-E1 | 2 |
| FR-09 - Approval re-checks the balance and refuses the request if too few days... | UC-02-E2, UC-02-D1 | 2 |
| FR-10 - Only admins review, an admin cannot review their own request, and only... | UC-02-E3, UC-02-E4, AC-01, AC-02, AC-03, AC-05, AC-10, AC-13 | 8 |
| FR-11 - An employee cancels their own pending request or approved request that... | UC-03-M1, UC-03-A1, UC-03-A2, UC-03-E1, UC-03-E2, AC-07, AC-08 | 7 |
| FR-12 - Every leave endpoint needs a valid token, and employees only see their... | AC-06, AC-08, AC-09, AC-11, AC-12 | 5 |
| BR1 - Boundary: working days requested <= remaining balance (Casual 12, Sick... | UC-01-M1, UC-01-A2, UC-01-E3, UC-02-E2, U-01 | 5 |
| BR2 - Decision: a review is allowed only if the reviewer is an admin AND the... | UC-02-M1, UC-02-E1, UC-02-E4, AC-03, AC-04, AC-05 | 6 |
| BR3 - State change: pending -> approved / rejected / cancelled; approved -> ... | UC-02-M1, UC-02-A2, UC-02-E3, UC-03-M1, UC-03-A1, UC-03-E1, UC-03-E2 | 7 |
| BR4 - No overlap: a new request may not overlap the same employee's pending ... | UC-01-E4 | 1 |

Requirements with at least one browser test: 15 of 16 (FR-06, reading own balances and requests, is covered at API level by Area 2; the browser tests read the same data on every screen but do not tag it).
Tests in the final run: 44, all reported as passing. UC-01-D1 and UC-02-D1 are expected failures that document DEF-A3-01 (Playwright counts an expected failure as a pass).

Other Area 3 tests (not in this CSV): tests/team/recovery (4 pytest tests: FR-07, FR-01, BR3), tests/team/security (4 pytest tests: WK-08, FR-12; 1 expected failure), k6 workload for FR-01.
