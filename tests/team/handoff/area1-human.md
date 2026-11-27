# Area 1 — static analysis, white-box, mutation, CI

Worth 37 of the 120 marks (static analysis 5, white-box unit testing 16,
mutation and CI gate 8, plus your share of the viva). You are examined on all
of it, so understand each number you report.

Your folder: `tests/team/unit/`. Tools: pytest, coverage.py, SonarQube,
mutmut, GitHub Actions.

## 0. Before you start

1. Clone the group repo (not upstream), then:
   ```powershell
   git config user.name "<your name>"
   git config user.email "<your email>"
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r ..\tests\team\api\requirements.txt
   pip install pytest-cov mutmut
   cd ..
   ```
2. Check the existing suites run: `cd backend; pytest -q; cd ..` and
   `python -m pytest tests/team/api`.
3. Make a branch per piece of work and merge through pull requests. You need
   real PRs later (one blocked, one fix), so start the habit now.

## 1. What counts as "server-side business logic"

You need 100 % statement **and** branch coverage of it. Agree this list with
the group and write it in the test plan:

| File | Functions |
| --- | --- |
| `backend/app/services.py` | `ensure_leave_types`, `working_days`, `balance_for`, `balances_for`, `overlapping_request`, `validate_leave_window`, `approve_request` |
| `backend/app/utils.py` | `Validator` (all methods), `json_body`, `current_user`, `admin_required`, `pagination_args`, `pagination_meta` |
| `backend/app/api/leaves.py` | `create_leave_request`, `cancel_leave_request`, `review_leave_request`, `get_request_or_404` |
| `backend/app/models.py` | `remaining_days`, `is_admin`, `set_password`, `check_password` |

Code you leave out (`seed.py`, `run.py`, CLI commands, dashboard) needs a
written reason in `.coveragerc` and in the report.

## 2. Unit tests (16 marks)

- Test functions directly, inside an app context with an in-memory database.
  Copy the `app` fixture from `tests/team/api/conftest.py` — it already builds a
  clean database per test.
- For route functions, the Flask test client is fine, but aim each test at a
  branch, not a workflow (that is Area 2).
- Cover all four business rules:
  - BR1 balance limit: `validate_leave_window` balance branch, `approve_request` both outcomes
  - BR2 review permission: every `if` in `review_leave_request`
  - BR3 state change: every `if` in `cancel_leave_request`, including the
    approved branch that gives days back and the `max(0, ...)` clamp
  - BR4 overlap: `overlapping_request` with and without `exclude_id`
- Run:
  ```powershell
  python -m pytest tests/team/unit --cov=backend/app --cov-branch --cov-report=term-missing --cov-report=xml --cov-report=html
  ```
  `term-missing` lists the lines and branches not yet hit.

### MCC and MC/DC on the critical module

Suggested critical decision: who may review (`review_leave_request`).

| Condition | Meaning |
| --- | --- |
| A | reviewer is admin |
| B | request status is pending |
| C | reviewer is not the requester |

1. **MCC** (multiple condition coverage): list all 8 combinations of A, B, C
   and the outcome of each (200, 403 or 409).
2. Mark infeasible or masked rows. The code checks A first and returns 403,
   so B and C have no effect when A is false. Say this explicitly.
3. **MC/DC**: for each condition, pick two rows from the MCC table that differ
   only in that condition and give different outcomes. Write the pairs.
4. Do the same for `decision == "reject" and not note`.

`tests/team/api/test_business_rules.py` (`REVIEW_TABLE`) has the same table at
API level. Yours should be at function level, with your own tests.

## 3. SonarQube (5 marks)

1. Start it: `docker run -d --name sonar -p 9000:9000 sonarqube:lts-community`.
   Open http://localhost:9000, log in admin/admin, change the password, create
   project `leavedesk`, generate a token.
2. Add `sonar-project.properties` at the repo root:
   ```properties
   sonar.projectKey=leavedesk
   sonar.sources=backend/app,frontend/src
   sonar.tests=tests/team
   sonar.python.version=3.12
   sonar.python.coverage.reportPaths=coverage.xml
   sonar.exclusions=**/node_modules/**,**/dist/**
   ```
3. Produce `coverage.xml` (step 2), then scan:
   ```powershell
   docker run --rm -e SONAR_HOST_URL=http://host.docker.internal:9000 -e SONAR_TOKEN=<token> -v "${PWD}:/usr/src" sonarsource/sonar-scanner-cli
   ```
4. Report and explain what each shows **for this code**: complexity
   (cyclomatic and cognitive), duplication, code smells, bugs,
   vulnerabilities, security hotspots, coverage, technical debt, ratings.
5. **Hand-calculate cyclomatic complexity** of `validate_leave_window`:
   draw the control flow graph, count E − N + 2 and decisions + 1, show they
   agree, compare with Sonar's figure for that function, explain any gap.

## 4. Mutation testing

1. `setup.cfg` at the repo root:
   ```ini
   [mutmut]
   paths_to_mutate=backend/app/services.py
   tests_dir=tests/team/unit/
   runner=python -m pytest -x -q tests/team/unit
   ```
   mutmut does not run natively on Windows; use WSL or let CI run it.
2. `mutmut run`, then `mutmut results`. Score = killed / (total − equivalent).
3. **Two custom operators** from the business rules. mutmut has no plugin
   API, so write a small script (`tests/team/unit/custom_mutants.py`) that
   applies each change to a copy of the code, runs the tests, records killed
   or survived, and restores the file. Ideas:
   - BR1 boundary: `remaining_days < days` → `<=`
   - BR4 overlap set: drop `"approved"` from `status.in_(("pending", "approved"))`
   - weekend rule: `weekday() < 5` → `< 6`
4. Analyse at least 15 survivors. Label each: **equivalent** (cannot be
   killed, explain why), **missing test**, or **weak assertion**. Add tests to
   kill the killable ones, rerun, report before and after.

## 5. CI quality gate

Extend `.github/workflows/ci.yml` (it already runs upstream tests and the
frontend build). On every pull request it must:

1. Run unit tests with coverage and fail below your threshold
   (`--cov-fail-under=...`).
2. Run `python -m pytest tests/team/api --api-coverage-min=100` (Area 2's gate).
3. Run mutation and fail below your threshold.
4. Run SonarQube analysis and enforce its quality gate (SonarCloud is free for
   public repos and easiest in CI).
5. No `continue-on-error`, no `|| true`.

Then in GitHub: Settings → Branches → protect `main`, require the checks.

- **Blocked PR:** open a PR that drops coverage or lets a mutant survive.
  Leave it blocked. Screenshot and link go in the report.
- **Fix PR:** pick a real defect — WK-04 (pending request starting today
  cannot be cancelled) or WK-05 (department + search crash) from
  `tests/team/api/reports/endpoint_weaknesses.md`. The PR must fail first
  (a test exposing the defect) and pass after the fix. Remove the matching
  `xfail` marker in the same PR. Link it to the GitHub Issue.
- **Justify each threshold from evidence** ("score was 84 % after killing the
  killable survivors, so the gate is 80 %").

## Viva — expect these

- Rerun one of your tests and explain each assertion.
- Walk through the CFG and your cyclomatic count.
- Show an MC/DC pair and why it proves independence.
- Explain one surviving mutant and why it is equivalent or not.
- Live task: given a rule change, predict which unit tests and which gate fail.

## Checklist

- [ ] Business-logic list agreed and in the test plan
- [ ] Unit tests at 100 % statement and branch, exclusions justified
- [ ] MCC table, infeasible rows, MC/DC pairs (two decisions)
- [ ] SonarQube run, metrics explained, hand-calculated CC compared
- [ ] Mutation score, 2 custom operators, 15+ survivors analysed, killables killed
- [ ] CI gate on PRs, thresholds justified, branch protection on
- [ ] Blocked PR and fix PR, both linked
- [ ] AI-use record rows for your area
