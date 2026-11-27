# Briefing for Claude Code — Area 2 (verify and finish the API tests)

You are helping Moez, the owner of Area 2 in a three-person Software Quality
Engineering project. The Area 2 code already exists in `tests/team/api/` but
has never been executed against the real backend dependencies. Your job is to
get it running, correct it where its predictions were wrong, and make sure
Moez can explain all of it in the viva.

Read `tests/team/handoff/README.md` and `tests/team/api/README.md` first.

## Rules for this session

1. **Ask before any decision**: changing an expected status, reclassifying a
   test as a defect, changing the spec, renaming requirement ids. Present the
   evidence (test output and the backend lines) and a recommendation.
2. **Never change `backend/app/`** to make a test pass. A test that fails
   because the API is wrong is a finding, not something to fix here.
3. **Do not commit or push.** Give Moez the commands; he commits under his
   own name. Never add Claude as a co-author or collaborator.
4. Explain any unfamiliar concept the first time it appears, briefly.
5. Keep 4-space indentation and the existing style. Comments neutral and
   human-sounding, only where needed. Do not use f-strings inside `print`
   calls; pass values as separate arguments.
6. Keep a list of every change you make (file, what, why) for the AI-use
   record.
7. Show real command output before saying anything passes.

## Layout

```text
tests/team/api/
  spec/openapi.yaml            source of truth for inputs and constraints
  generator/generate_cases.py  spec -> generated/cases.json
  conftest.py                  app per test (in-memory SQLite), ApiClient that
                               checks every response against the spec and
                               records coverage
  support/                     tokens, schema checker, coverage, flows, requirement ids
  test_generated_inputs.py     EP/BVA driven by cases.json
  test_business_rules.py       BR1 BVA, BR2 and cancel decision tables, BR4 overlap, date rules
  test_state_transitions.py    BR3 state machine, repeated requests, read-backs
  test_access_and_auth.py      401s, role checks, read endpoints
  test_endpoint_weaknesses.py  strict xfail tests for WK-01..WK-06
  test_generator.py            tooling tests, no Flask needed
  reports/                     coverage, traceability, weaknesses, demo diff
```

If you edit `spec/openapi.yaml`, rerun the generator; the suite refuses to
run on stale `cases.json`.

## Tasks, in order

Use a task list. Stop after each task, summarise briefly, and wait for Moez.

### Task 1 — environment and first run
From the repo root (Windows PowerShell):

```text
cd backend; python -m venv .venv; .venv\Scripts\activate
pip install -r ..\tests\team\api\requirements.txt; cd ..
python -m pytest tests/team/api -rxX -q
```

Report the totals. Group failures by cause, not by test.

### Task 2 — triage failures
For each group: show the assertion output, the relevant backend lines, and
your conclusion — *test expectation wrong* or *API defect*. Ask Moez to decide
each one. Then:

- expectation wrong: fix the test, or the spec plus regeneration if the
  constraint itself was wrong
- API defect: move it to `test_endpoint_weaknesses.py` as
  `xfail(strict=True, reason="WK-xx: ...")` and add a row (root cause,
  severity, priority, suggested fix) to `reports/endpoint_weaknesses.md`

Rerun until the suite has only passes and expected xfails.

### Task 3 — weakness confirmation
Run `test_endpoint_weaknesses.py -rxX`. Any XPASS: show why the prediction
was wrong, ask, then remove the test and its report row.

### Task 4 — coverage at 100 %
Run with `--api-coverage-min=100`. For each item under "Not covered" in
`reports/api_coverage.md`, propose the smallest test that covers it, ask,
add it, rerun.

### Task 5 — generator demo rehearsal
Walk Moez through the demo in `tests/team/api/README.md` ("Changing two
constraints"): back up `cases.json`, change `reason.maxLength` and the CASUAL
allocation, regenerate with `--compare`, ask him to predict which tests fail
before running them, run, then revert. Repeat once with a constraint he picks.

### Task 6 — understanding check
Ask Moez to explain, in his own words, one test from each file and the
generator rule for `minLength` / `maxLength`. Correct gaps. Then write
`docs/team/area2_viva_notes.md`: a paragraph per component and five likely
questions with short answers (EP vs BVA, one invalid value per test, API
coverage criteria, why xfail strict, test client vs live server).

### Task 7 — handover material
Produce for the shared documents:
`reports/test_traceability.csv` (from the last full run) and
`reports/api_coverage.md`; a Markdown list of GitHub Issues to create, one per
weakness, with title, body, labels (severity, priority, category). Do not
create the issues yourself unless Moez asks and `gh` is authenticated as him.

### Task 8 — commit commands
Give Moez the branch, `git add`, commit and push commands for
`tests/team/api` and `tests/team/handoff`, with a plain commit message and no
co-author trailer.
