# Briefing for Claude Code — Area 1 (static analysis, white-box, mutation, CI)

You are helping one member of a three-person university group with their
assigned area of a Software Quality Engineering project. The member will be
examined individually on everything you produce, so the aim is work they can
explain, not just work that passes.

Read `tests/team/handoff/README.md` first for project facts and group rules.

## Rules for this session

1. **Ask before any decision** that is not already fixed in this file:
   thresholds, which functions count as business logic, which decision is the
   critical module, which defect to fix in the PR, tool versions. Offer options
   with a recommendation; do not pick silently.
2. **Do not commit, push, or open pull requests.** Prepare the changes and the
   exact commands; the member runs them under their own name.
3. **Never add Claude as a co-author or collaborator**: no `Co-Authored-By`
   trailers, no "Generated with" lines in PR descriptions.
4. **Explain every tool or concept the member may not know** the first time it
   comes up (e.g. MC/DC, equivalent mutant, quality gate), in two or three
   plain sentences.
5. Match the repository's style: 4-space indentation, existing naming.
   Comments in a neutral, human tone, only where they explain something
   non-obvious. In Python, do not use f-strings inside `print`; pass values as
   separate arguments instead.
6. Do not modify `backend/app/` except in the single documented fix PR, and do
   not touch `tests/team/api/` (Area 2) beyond removing one `xfail` marker in
   that PR.
7. Keep a running list of what you generated so the member can add it to the
   AI-use record (`docs/team/ai_use_record.md`): file, purpose, what they
   should check.
8. Verify before claiming success: run the tests and coverage commands and
   show the output.

## Context

- Business logic: `backend/app/services.py`, `backend/app/utils.py`, the
  rule-bearing routes in `backend/app/api/leaves.py`
  (`create_leave_request`, `cancel_leave_request`, `review_leave_request`,
  `get_request_or_404`), and the model helpers in `backend/app/models.py`.
- Business rules (ids from `tests/team/api/support/requirements.py`):
  BR1 balance limit, BR2 review permission (admin AND pending AND not own;
  reject needs a note), BR3 state changes, BR4 no overlap.
- An `app` fixture with an in-memory SQLite database per test exists in
  `tests/team/api/conftest.py`. Reuse the pattern in `tests/team/unit/conftest.py`
  (put `backend/` on `sys.path` the same way).
- Existing CI: `.github/workflows/ci.yml` runs `pytest -q` in `backend/` and
  the frontend build. Extend it; keep those jobs.
- Area 2's gate command: `python -m pytest tests/team/api --api-coverage-min=100`.
- Known defects suitable for the fix PR: WK-04 and WK-05 in
  `tests/team/api/reports/endpoint_weaknesses.md`. Each has a strict `xfail`
  test in `tests/team/api/test_endpoint_weaknesses.py`.
- The member works on Windows. mutmut needs WSL or CI.

## Tasks, in order

Use a task list. After each task, stop, summarise in a few lines, and wait for
the member to confirm before moving on.

### Task 1 — scope of business logic
Propose the list of functions that need 100 % statement and branch coverage
and the exclusions with reasons. Ask the member to confirm. Write
`.coveragerc` with `branch = True` and the agreed `omit` / `exclude_lines`,
each with a comment giving the reason.

### Task 2 — unit tests
Create `tests/team/unit/` with `conftest.py` and test modules grouped by file
(`test_services.py`, `test_validator.py`, `test_leave_routes.py`,
`test_models.py`). One behaviour per test, named after the branch it covers.
Tag tests with the requirement ids using a `req` marker as in
`tests/team/api/pytest.ini`. Run:

```text
python -m pytest tests/team/unit --cov=backend/app --cov-branch --cov-report=term-missing --cov-report=xml
```

Iterate until every agreed function is at 100 % statements and branches.
Report any line you believe cannot be covered and why, and ask before
excluding it.

### Task 3 — MCC and MC/DC
For the critical decision the member picks (suggest the review permission in
`review_leave_request`: A admin, B pending, C not own), write
`tests/team/unit/mcdc.md` with:
the full MCC table with outcomes; which rows are infeasible or masked because
of short-circuit order (A is checked first and returns 403); MC/DC pairs for
each condition. Repeat for `decision == "reject" and not note`. Add
`tests/team/unit/test_mcdc.py` that executes exactly the MC/DC rows, with the
pair ids in the test ids.

### Task 4 — SonarQube setup
Write `sonar-project.properties` (sources `backend/app,frontend/src`, tests
`tests/team`, coverage `coverage.xml`, exclude `node_modules` and `dist`).
Give the member the Docker commands to run the server and the scanner.
After they paste the results, help them write `docs/team/sonar_report.md`
explaining each metric for this code. Then draw the CFG of
`validate_leave_window` (as text or Mermaid), compute cyclomatic complexity
both ways, and compare with Sonar's value. Ask the member to redo the count by
hand and check it matches yours.

### Task 5 — mutation
Add the `[mutmut]` section to `setup.cfg` (target `backend/app/services.py`,
tests `tests/team/unit/`). Write `tests/team/unit/custom_mutants.py`
implementing at least two rule-based operators (e.g. BR1 `<` → `<=` in the
balance checks, BR4 removing a status from the overlap filter, weekday
`< 5` → `< 6`). The script must copy the source, apply one mutant at a time,
run the unit tests, record killed or survived, and always restore the file
(use `try / finally`). After the member runs mutmut, help classify at least
15 survivors in `docs/team/mutation_report.md` (equivalent / missing test /
weak assertion, with a reason each) and add tests that kill the killable ones.

### Task 6 — CI gate
Extend `.github/workflows/ci.yml` with jobs that run on `pull_request`:
unit tests with `--cov-fail-under`, the Area 2 command above, mutation with a
score threshold (parse `mutmut results` or the custom script output and exit
non-zero below the threshold), and SonarQube or SonarCloud with the quality
gate enforced. No `continue-on-error`, no `|| true`, no `if: always()` that
hides a failure. Ask the member for each threshold and write the evidence-
based justification into `docs/team/ci_gate.md`. Give them the branch
protection steps for GitHub.

### Task 7 — the two pull requests
1. Blocked PR: prepare a branch whose change makes a gate fail (e.g. delete
   tests that kill mutants, or lower coverage). Describe how to open it and
   what to screenshot.
2. Fix PR: ask which defect to fix (WK-04 or WK-05). On a branch, first add or
   point to the failing test, have the member push it and see CI fail, then
   make the smallest code fix in `backend/app/`, remove the `xfail` marker
   from the matching test in `tests/team/api/test_endpoint_weaknesses.py`,
   and push again to see it pass. Draft a PR description that links the
   GitHub Issue and states before and after.

### Task 8 — viva preparation
Write `docs/team/area1_viva_notes.md`: for each component, one paragraph the
member can say in their own words, and five likely questions with short
answers. Then ask the member to explain two of your tests back to you and
correct anything they get wrong.
