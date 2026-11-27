# Endpoint weaknesses (Area 2)

Found by reading `backend/app/api/leaves.py`, `services.py` and `utils.py` at the
baseline commit while writing the spec, then checked by the tests named below.

**Status:** predicted from source review. Run
`python -m pytest tests/team/api/test_endpoint_weaknesses.py -rxX` and confirm each
test is reported as `XFAIL` before raising GitHub Issues. If one shows `XPASS`
(strict failure), the prediction was wrong: delete that test and its row here.

Severity and priority use the scale in the shared test plan. The risk ids are
placeholders until the risk register is written (shared test management).

| Id | Endpoint | Observation | Test | Severity | Priority | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| WK-01 | `GET /api/leave-balances` | `year` has no range check. Any whole number (1900, -5) is accepted and a GET creates three balance rows for that year. | `test_wk01_...` | Minor | Low | R-? data integrity |
| WK-02 | `POST /api/leave-requests` | `Validator.integer` calls `int(value)`, so `1.9` becomes 1 and `"2"` becomes 2. A malformed client is not told about its mistake. | `test_wk02_...`, generated case `leave_type_id.EP.numeric_string` | Minor | Low | R-? input validation |
| WK-03 | `GET /api/leave-requests` | `q` is placed into `ILIKE '%q%'` without escaping, so `%` and `_` act as wildcards. `q=%` returns every request the caller can see. | `test_wk03_...` | Minor | Low | R-? search correctness |
| WK-04 | `POST /api/leave-requests/{id}/cancel` | A request may start today (create allows `start >= today`), but cancel refuses any request with `start <= today`, pending ones included. README says pending requests can be cancelled. | `test_wk04_...` | Major | Medium | R-? BR3 state change |
| WK-05 | `GET /api/leave-requests` (admin) | `department` and `q` both call `query.join(User, ...)`. Using them together joins `users` twice; expected to raise a database error (HTTP 500). | `test_wk05_...` | Major | Medium | R-? admin queue unusable with filters |
| WK-06 | `POST /api/leave-requests/{id}/review` | Approval does not look at the dates, so a pending request whose leave has already passed can still be approved and charged to the balance. Basis: our assumption that a stale request should be closed, not approved (agree this in the test basis). | `test_wk06_...` | Minor | Low | R-? BR2/BR3 |
| WK-07 | `POST /api/auth/login` | `password` is passed through `str()`, so a number gets 401 instead of a 422 field error; `0` or `false` get 422 "Password is required". Inconsistent error contract. | generated case `login.password.EP.not_a_string` | Trivial | Low | – |
| WK-08 | All endpoints that do not call `current_user()` (e.g. `GET /api/leave-types`) | A token of a deactivated user keeps working there until it expires (12 h). `/api/auth/me` and the leave endpoints do reject it. | not automated; see `test_token_of_deactivated_user_is_401` for the endpoint that checks | Minor | Medium | R-? access control (Area 3 security) |
| WK-09 | `POST /api/leave-requests/{id}/review` | Body validation runs before the record lookup: an unknown id with a bad body answers 422, not 404. | not automated (observation) | Trivial | Low | – |
| WK-10 | `POST /api/leave-requests` | The overlap rule is checked in Python only; there is no database constraint. Two identical submissions sent at the same moment can both pass the check and create duplicates. Sequential repeats are refused (`test_repeated_submission_is_not_duplicated`). | not automated here; candidate for the Area 3 recovery or k6 test | Major | Medium | R-? duplicate records |
| WK-11 | `POST /api/leave-requests` | Pending requests do not reserve days, so an employee can have several pending requests that together exceed the balance. The second approval then fails (by design per README, but the employee only learns this at review time). | `test_br1_balance_rechecked_on_approval`, `test_balance_flows_between_workflows` | Minor | Low | R-? BR1 |
| WK-12 | `GET /api/leave-requests` | `page` and `per_page` out of range are clamped silently (0 → 1, 51 → 50) rather than rejected. Documented behaviour; listed for completeness. | generated BVA cases with `expected_echo` | Trivial | Low | – |

## For each finding, before it goes in the PDF

The brief asks for root cause, severity, risk and fix per finding. Suggested fixes:

- WK-01: validate `year` against a range (e.g. joined year .. current year + 1) and stop creating rows on GET; return zeros for years without rows.
- WK-02: in `Validator.integer`, accept only `int` (not `bool`) or a string of digits.
- WK-03: escape `%`, `_` and `\` in `q` and pass `escape="\\"` to `ilike`.
- WK-04: allow cancelling pending requests regardless of date, or block creating requests that start today. Agree which with the group, then make it one PR (this is a good candidate for the "documented fix through a pull request" in Area 1).
- WK-05: join `User` once when either filter needs it.
- WK-06: refuse approval with 409 when `start_date < today`.
- WK-10: add a unique or exclusion check at the database level, or lock the user's rows during submission.
