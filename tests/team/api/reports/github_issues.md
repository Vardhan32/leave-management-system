# GitHub Issues to create (Area 2)

One issue per weakness in `endpoint_weaknesses.md`. Labels are
`severity:*`, `priority:*`, `category:*`. WK-01 to WK-06 are confirmed by a
strict `xfail` test (all six reported XFAIL, no XPASS). WK-07 to WK-12 are
observations from the source review or the generated cases. Fill in the
`Risk` line once the risk register exists. Baseline commit:
`b002faa4b46ba2090489c200c61787551591c70d`.

Re-run any confirmed one with
`python -m pytest tests/team/api/test_endpoint_weaknesses.py -rxX -k wkNN`.

---

## WK-01 Balance year is not range-checked and GET creates rows
- Labels: `severity:minor`, `priority:low`, `category:data-integrity`
- Steps: log in as the employee; `GET /api/leave-balances?year=1900`.
- Expected: 422 for a year outside a sensible range; a GET has no side effects.
- Actual: 200, and three `LeaveBalance` rows for 1900 are created.
- Evidence: `test_wk01_balance_year_out_of_range_is_rejected`
- Suggested fix: validate `year`; return zeros for a year with no rows without inserting.
- Risk: R-?

## WK-02 Fractional leave_type_id is truncated
- Labels: `severity:minor`, `priority:low`, `category:input-validation`
- Steps: `POST /api/leave-requests` with `"leave_type_id": 1.9`.
- Expected: 422 field error.
- Actual: the value is converted by `int()` to 1 and the request is accepted.
- Evidence: `test_wk02_fractional_leave_type_id_is_rejected`; generated case `leave_type_id.EP.numeric string` (a string `"2"` is also accepted).
- Suggested fix: in `Validator.integer`, accept only real integers (not bool) or digit strings.
- Risk: R-?

## WK-03 Search treats % and _ as wildcards
- Labels: `severity:minor`, `priority:low`, `category:search-correctness`
- Steps: `GET /api/leave-requests?q=%`.
- Expected: only requests whose reason contains a literal `%`.
- Actual: every request the caller can see.
- Evidence: `test_wk03_search_treats_percent_literally`
- Suggested fix: escape `%`, `_`, `\` in `q` and pass `escape="\\"` to `ilike`.
- Risk: R-?

## WK-04 Pending request that starts today cannot be cancelled
- Labels: `severity:major`, `priority:medium`, `category:state-change` (BR3)
- Steps: create a leave request starting today (allowed), then `POST /api/leave-requests/{id}/cancel`.
- Expected: pending requests can be cancelled (README).
- Actual: cancel refuses any request with `start_date <= today`.
- Evidence: `test_wk04_pending_request_starting_today_can_be_cancelled`
- Suggested fix: allow cancelling pending requests regardless of date, or refuse creating requests that start today. The group agrees which.
- Risk: R-?

## WK-05 Admin filters department + q together fail
- Labels: `severity:major`, `priority:medium`, `category:admin-workflow`
- Steps: as admin, `GET /api/leave-requests?department=Engineering&q=a`.
- Expected: 200 with filtered results.
- Actual: `users` is joined twice, which raises a database error (500).
- Evidence: `test_wk05_admin_can_combine_department_and_search`
- Suggested fix: join `User` once when either filter needs it.
- Risk: R-?

## WK-06 Stale pending request can be approved
- Labels: `severity:minor`, `priority:low`, `category:state-change` (BR2/BR3)
- Steps: have a pending request whose dates are in the past; approve it as admin.
- Expected (assumption, to be agreed in the test basis): 409, the request cannot be approved after it started.
- Actual: approved and charged to the balance.
- Evidence: `test_wk06_stale_pending_request_cannot_be_approved`
- Suggested fix: refuse approval with 409 when `start_date < today`.
- Risk: R-?

## WK-07 Login password type gives inconsistent errors
- Labels: `severity:trivial`, `priority:low`, `category:error-contract`
- Steps: `POST /api/auth/login` with `"password": 123`, then `0`.
- Expected: the same 422 field error for a non-string.
- Actual: `123` gives 401 (passed through `str()`), `0` or `false` give 422 "Password is required".
- Evidence: generated case `login.password.EP.not_a_string`
- Suggested fix: reject non-string passwords with 422 before the lookup.

## WK-08 Deactivated user's token still works on some endpoints
- Labels: `severity:minor`, `priority:medium`, `category:access-control`
- Steps: deactivate a user, keep their token, `GET /api/leave-types`.
- Expected: 401.
- Actual: 200 until the token expires (12 h); `/api/auth/me` and the leave endpoints do reject it.
- Evidence: not automated; `test_token_of_deactivated_user_is_401` covers the endpoints that do check.
- Suggested fix: check the active flag in one shared place (a `before_request` or a JWT user-lookup callback).
- Risk: R-?

## WK-09 Validation runs before record lookup on review
- Labels: `severity:trivial`, `priority:low`, `category:error-contract`
- Steps: `POST /api/leave-requests/999999/review` with an invalid body.
- Expected: 404.
- Actual: 422.
- Evidence: observation only.

## WK-10 Overlap check is not atomic
- Labels: `severity:major`, `priority:medium`, `category:data-integrity` (BR4)
- Steps: send two identical submissions at the same moment.
- Expected: one is refused.
- Actual (predicted): both can pass the Python-only check and create duplicates. Sequential repeats are refused.
- Evidence: not confirmed; candidate for the Area 3 recovery or k6 test.
- Suggested fix: database-level constraint or lock the user's rows during submission.
- Risk: R-?

## WK-11 Pending requests do not reserve days
- Labels: `severity:minor`, `priority:low`, `category:business-rule` (BR1)
- Steps: submit several pending requests that together exceed the balance, then approve them in turn.
- Expected: employee is warned early.
- Actual: the later approval fails; the employee learns this only at review time. By design per README.
- Evidence: `test_br1_balance_rechecked_on_approval`, `test_balance_flows_between_workflows`.

## WK-12 Paging values are clamped silently
- Labels: `severity:trivial`, `priority:low`, `category:error-contract`
- Observed: `page=0` becomes 1 and `per_page=51` becomes 50, with no error. Documented behaviour, listed for completeness. Probably close without a fix.
- Evidence: generated BVA cases with `expected_echo`.
