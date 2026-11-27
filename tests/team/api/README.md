# Area 2 — API testing and automated test data generation

Owner: Moez. Everything in this folder is team work; nothing here comes from
the upstream repository.

## What is here

```text
tests/team/api/
  spec/openapi.yaml              OpenAPI 3.0 spec of the endpoints under test
  spec/examples/openapi.changed.yaml
                                 the same spec with two constraints changed (demo)
  generator/generate_cases.py    reads the spec, writes EP classes and 3-point BVA values
  generated/cases.json           generator output, committed so runs are reproducible
  support/                       token resolver, schema checker, coverage tracker, helpers
  conftest.py                    app, users, API client that records coverage
  test_generated_inputs.py       EP + BVA on every body field, query parameter and path id
  test_business_rules.py         BR1 BVA, BR2 and cancel decision tables, BR4 overlap BVA, date rules
  test_state_transitions.py      BR3 state machine, repeated requests, cross-workflow read-backs
  test_access_and_auth.py        401 on every protected endpoint, role checks, read endpoints
  test_endpoint_weaknesses.py    weaknesses as strict xfail tests
  test_generator.py              tests for the generator and helpers (no Flask needed)
  reports/                       coverage, traceability, weaknesses, constraint-change demo
```

## Test basis used here

Workflows (module: leave requests):

| | Starting condition | User action | Expected outcome |
| --- | --- | --- | --- |
| W1 Apply for leave | Employee signed in, 12 casual days left, no overlapping request | Submits Casual leave Mon–Wed next March with a 10+ character reason | 201, request stored as `pending` with `days = 3`; balance unchanged |
| W2 Review leave | Admin signed in, the W1 request is pending | Approves it (or rejects with a note) | 200, status `approved` and `used_days` grows by 3 (reject: status `rejected`, balance unchanged) |

Shared records: `LeaveBalance.used_days` (W2 writes it, W1 reads the remaining
balance) and `LeaveRequest.status` (W1 creates it, W2 and cancel change it).

Requirements and business rules: see `support/requirements.py` (FR-01..FR-12,
BR1..BR4). Roles: employee and admin.

> These ids were chosen while building Area 2. The group still has to confirm
> them in the shared test plan; if they are renumbered, change
> `support/requirements.py` and every report follows.

## Setup (once)

Windows PowerShell, from the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r ..\tests\team\api\requirements.txt
cd ..
```

macOS / Linux: same, with `source backend/.venv/bin/activate`.

No database server or running API is needed. Each test builds the Flask app
with `TestConfig` on a new in-memory SQLite database and drops it afterwards,
so there is no seed or reset step between runs.

## Run

```powershell
# 1. regenerate the test data (only needed after editing the spec)
python tests/team/api/generator/generate_cases.py

# 2. run all Area 2 tests and write the reports
python -m pytest tests/team/api -rxX

# 3. same, but fail if any API coverage criterion is below 100 %
python -m pytest tests/team/api --api-coverage-min=100
```

After a run, `reports/` holds:

- `api_coverage.md` / `.json` — path, operation, parameter, parameter value,
  content type, status class, status code and response property coverage
- `test_traceability.csv` — every test with the FR/BR ids it covers and its outcome
  (feed this into the shared traceability matrix)

If the suite says `generated/cases.json is older than spec/openapi.yaml`, run
step 1. The tests refuse to run on stale data on purpose.

## How the generator works

For every operation in the spec it builds a valid baseline body from the
`example` values, then emits one case per partition or boundary, each changing
a single field:

| Spec keyword | Cases produced |
| --- | --- |
| `required` | missing, empty string, whitespace only (if `x-trimmed`) |
| `type: string` | not a string |
| `type: integer` | not a number, boolean, null, numeric string |
| `minLength` / `maxLength` | n-1, n, n+1 characters |
| `minimum` / `maximum` | n-1, n, n+1 (or clamped values with `x-clamped`) |
| `enum` | each value, a value outside the enum, wrong case, padded value |
| `format: date` | wrong separator, impossible date, free text |
| `x-min-relative: today` | today-1, today, today+1 |
| `x-min-field: start_date` | start-1, start, start+1 |
| `x-lookup-max: 3` | 2, 3, 4 (4 passes validation, then 404) |
| `x-business-rules.balance-limit` | per leave type: allocation-1, allocation, allocation+1 working days at submission; 3, 2, 1 days left at approval |

Dates are written as tokens (`{today-1}`, `{start_date+1}`) and resolved when the
test runs, because the "no past dates" rule depends on the run date.

## Changing two constraints (viva demo)

`spec/examples/openapi.changed.yaml` changes `reason.maxLength` 500 → 300 and the
Casual allocation 12 → 10. The diff of the generated cases is saved in
`reports/constraint_change_demo.txt`. To repeat it live:

```powershell
copy tests\team\api\generated\cases.json old_cases.json
# edit spec/openapi.yaml (or copy the example over it)
python tests/team/api/generator/generate_cases.py --compare old_cases.json
python -m pytest tests/team/api -k "reason or CASUAL"
```

Prediction with the code unchanged:

| Test | Why it fails |
| --- | --- |
| `test_create_leave_request_input[...reason.BVA.maxLength+1_(301)]` | expects 422, API still allows 500 characters |
| `test_br1_balance_limit_on_submission[...CASUAL...]` (all three) | `allocated_days` is still 12; 11 days is still accepted |
| `test_br1_balance_rechecked_on_approval[...CASUAL...remaining=need-1...]` | 3 days really remain, so approval succeeds |

To make the code match: `max_length=300` for `reason` in
`backend/app/api/leaves.py`, and `"default_days": 10` for CASUAL in
`backend/app/models.py`. Then everything passes again.

For any other live change: edit the spec, regenerate, run with `--compare`, and
read the Added / Removed / Changed list. Each added or changed case id names the
test that will now behave differently.

## Known limits

- Run dates from 26 to 31 December: the `{today}` start-date cases use
  `end = today + 6`, which crosses the year and gets a different error.
- Concurrency (WK-10) is not tested here; it needs parallel clients (Area 3).
- Weakness tests are predictions from the source until the first run confirms
  them (see `reports/endpoint_weaknesses.md`).
