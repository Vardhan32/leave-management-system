# Area 2 — API testing and data generation (what is left)

Owner: Moez. Worth API and integration testing 10 + automated test data
generation 7, plus your share of the viva.

The code is written (`tests/team/api/`). It has **not been run** against the
real dependencies yet; the expected status codes were derived from reading the
backend source. The work below turns it into verified, owned work.

## 1. First run

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r ..\tests\team\api\requirements.txt
cd ..
python -m pytest tests/team/api -rxX
```

Expect about 251 tests. For each failure:

1. Read the assertion message — it prints the case, the body sent and the
   response.
2. Open the backend code for that endpoint and decide who is wrong: the test's
   expectation or the API.
3. Wrong expectation → fix the test (or the spec, then regenerate).
   API really wrong → it is a defect: move the test into
   `test_endpoint_weaknesses.py` with a strict `xfail` and add a row to
   `reports/endpoint_weaknesses.md`.

Keep a short list of what you changed and why; it goes in the AI-use record.

## 2. Confirm the weaknesses

```powershell
python -m pytest tests/team/api/test_endpoint_weaknesses.py -rxX
```

All six should be `XFAIL`. One that is `XPASS` (shown as a failure, because
the markers are strict) means the prediction was wrong: delete that test and
its row in the report.

## 3. Coverage

```powershell
python -m pytest tests/team/api --api-coverage-min=100
```

Open `reports/api_coverage.md`. Every criterion should be 100 %. Anything
under "Not covered" needs a test. Put the table in the PDF.

## 4. Generator demo

Practise until you can do it without notes:

```powershell
copy tests\team\api\generated\cases.json old_cases.json
# edit spec/openapi.yaml: e.g. reason maxLength 500 -> 300
python tests/team/api/generator/generate_cases.py --compare old_cases.json
python -m pytest tests/team/api -k reason
```

Say beforehand which tests will fail and which gate (the Area 1 CI job running
the API suite). Then make the matching code change (`max_length=300` in
`backend/app/api/leaves.py`) and show everything passing. Revert after.

## 5. Understand every file

The viva treats anything you cannot explain as not your work. Be able to
explain:

- EP vs BVA, and why each test changes only one field
- why dates are tokens (`{today-1}`) rather than fixed values
- how the generator turns `minLength`, `maxLength`, `minimum`, `enum`,
  `x-lookup-max`, `x-min-relative` and the balance allocations into cases
- what each of the 8 API coverage criteria means
- the BR2 and cancel decision tables, and the state-transition list
- why the weakness tests are `xfail(strict=True)`
- why tests use the Flask test client with a new in-memory database per test
  (isolation and reset), and how that differs from Requests against a live server

## 6. Hand over to the group

- Give the shared-documents owner `reports/test_traceability.csv` and
  `reports/api_coverage.md`.
- Log WK-01..WK-12 as GitHub Issues (severity, priority, status, triage).
- Tell the Area 1 owner the CI command:
  `python -m pytest tests/team/api --api-coverage-min=100`.
- Agree requirement ids; if they change, edit `support/requirements.py` only.

## 7. Your own use cases

The brief asks for two use cases per member. Write yours (2 alternative and
2 exception flows each, preconditions, postconditions) and give them to the
Area 3 owner for automation, or automate them yourself — agree which.

## 8. Commit

On a branch, under your own name, without any AI co-author line:

```powershell
git checkout -b area2-api-tests
git add tests/team/api tests/team/handoff
git commit -m "test(api): spec, EP/BVA generator and API tests for apply and review"
git push -u origin area2-api-tests
```

Then open a pull request and merge it once CI is green.

## Checklist

- [ ] Suite runs; failures resolved and recorded
- [ ] 6 weakness tests confirmed XFAIL
- [ ] API coverage 100 % on all criteria
- [ ] Generator demo rehearsed
- [ ] Every file understood
- [ ] Issues logged, CSV and coverage handed over
- [ ] Two use cases written
- [ ] Committed under your name; AI-use record rows added
