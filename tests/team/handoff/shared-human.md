# Shared — test management and final submission

Test management is shared by all three members, and the viva can ask any of
you about any of it. Worth: system and scope 5, test plan / estimation /
traceability 7, risk register and exit criteria 5, defect management and RCA
7, monitoring and completion report 5.

Suggested home for the documents: `docs/team/`. Write them in Markdown in the
repo (history shows who did what), then copy into the PDF at the end.

## 0. Group setup (do this first, together)

1. **Group repo.** One member creates a public GitHub repo, then:
   ```powershell
   git remote rename origin upstream
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   git tag baseline b002faa4b46ba2090489c200c61787551591c70d
   git push origin baseline
   ```
   Add the other two as collaborators.
2. **Register** the repo in your section's tab of the shared Google Sheet
   (due within 5 days of the 16 Nov announcement).
3. **Line endings.** On Windows run `git config core.autocrlf true`. If
   `git status` shows every upstream file modified, it is line endings.
4. **Ownership.** Write down who owns Area 1, 2, 3 and who drafts each shared
   document below.
5. **Hours log.** Each member keeps hours per area from today — you need them
   for "actual effort" against the estimates.

## 1. System and scope (`docs/team/scope.md`)

- Upstream URL, licence (MIT), baseline commit, why LeaveDesk fits (browser
  UI, HTTP API, persistent storage, source available).
- Install, start, seed and reset commands (copy from the README and
  `handoff/area3-human.md` section 0).
- The two workflows with starting condition, user action, expected outcome
  (table in `tests/team/api/README.md`).
- The shared records and which workflow reads or changes each.
- At least 8 functional requirements (FR-01..FR-12 in
  `tests/team/api/support/requirements.py`), 4 business rules (BR1 boundary,
  BR2 two-plus-condition decision, BR3 state change, BR4 overlap), 2 roles
  (employee, admin) with their permissions.
- Test basis: for each requirement, the source (README section, code file) or
  the written assumption. Example assumption: WK-06, stale requests should not
  be approvable.

## 2. Test plan (`docs/team/test_plan.md`)

Scope (in and out), approach by risk level, roles, environment (OS, Python,
Node, tool versions), test data (generator output, seed, synthetic accounts),
schedule to 29 Nov, entry / exit / suspension / resumption criteria, risks.
Keep it updated — note changes with dates.

## 3. Estimation (`docs/team/estimation.md`)

Per area: optimistic O, most likely M, pessimistic P, estimate
(O + 4M + P) / 6. At the end add actual hours from the log and explain big
gaps.

## 4. Risk register (`docs/team/risk_register.md`)

At least 8 product and 2 project risks. For each: id, description,
likelihood 1–5, impact 1–5, score, level, technique and depth it drives,
owner, linked tests or findings. Show the 5 × 5 matrix.

Product risk ideas from what the tests found:

- approving more days than the balance (BR1)
- double approval or double cancel counting days twice
- cancel returning the wrong number of days
- duplicate requests under concurrent submission (WK-10)
- admin list crashes with department + search (WK-05)
- pending leave starting today cannot be cancelled (WK-04)
- employees reviewing or reading others' requests
- stale requests approved after their dates (WK-06)
- token in localStorage exposed to injected scripts
- slow request list under load

Project risks: a member unavailable before the viva; CI minutes or SonarQube
setup taking longer than planned; tool not running on Windows (mutmut).

Then replace the `R-?` placeholders in
`tests/team/api/reports/endpoint_weaknesses.md` with real risk ids.

## 5. Exit criteria

At least 3, measurable, at least 2 tied to the highest risks. Examples:

- 100 % API status-code coverage (`tests/team/api/reports/api_coverage.md`)
- 0 open defects of severity Major or above on BR1 or BR3
- p95 of the chosen operation within the Area 3 limit, < 1 % unexpected failures
- 100 % statement and branch coverage of business logic, mutation score ≥ gate

At the end, show actual vs target for each — the release decision rests on
them.

## 6. Traceability (`docs/team/traceability.md`)

Requirement → tests (unit, API, e2e) → latest result → covered yes/no, and a
requirements-coverage percentage. Start from
`tests/team/api/reports/test_traceability.csv`; add the unit and Playwright
tests (tag them with the same ids).

## 7. Defects

- GitHub Issues with labels for severity, priority, category, and a status /
  triage comment (fix now, defer, won't fix — with the reason). Start with
  WK-01..WK-12 from `tests/team/api/reports/endpoint_weaknesses.md`, plus
  whatever Areas 1 and 3 find.
- Root cause analysis for at least 2 major defects (WK-04 and WK-05 suit):
  5 Whys and a fishbone diagram (people, process, code, tools, requirements,
  environment), corrective action and preventive action.
- Pareto chart of defects by category.
- Link each API, accessibility, security and performance finding to a risk.

## 8. Weekly progress reports (`docs/team/progress/week-N.md`)

Planned vs done, deviations, control actions, and GQM metrics read in
context: defect density (defects / KLOC of tested code), requirements
coverage (%), reopen rate (%). At least one per week until submission.

## 9. Completion report (`docs/team/completion_report.md`)

Tested and not tested, deviations from the plan, open defects, residual risk
per risk, actual vs target for each exit criterion, release or hold
recommendation with the evidence.

## 10. AI-use record (`docs/team/ai_use_record.md`)

One table, every member adds rows: date, member, tool, purpose, output,
what was checked or changed. Keep prompts (exported chats or a prompts
folder). Area 2's first rows: Claude wrote `tests/team/api/` and
`tests/team/handoff/`.

## 11. Final package

- PDF: scope, risk register, traceability table, results for every testing
  activity, root cause / severity / risk / fix for every finding, test
  management documents, area ownership, AI-use record, evidence links, the
  public GitHub link, release or hold decision with actual vs target for the
  three release criteria.
- Zip of the repository **including `.git`**.
- Names: `Project_<roll1>_<roll2>_<roll3>_<section>.zip` and `.pdf`.
- Repo must contain: upstream reference and baseline commit, reproducible
  setup and reset, runnable scripts and test data, tool versions, CI config,
  the documented fix PR and the blocked PR.

## Checklist

- [ ] Repo created, baseline tagged, registered in the sheet
- [ ] Scope and test basis
- [ ] Test plan (kept updated)
- [ ] Estimates, and actuals at the end
- [ ] Risk register with 5 × 5 matrix; weakness rows linked
- [ ] 3+ exit criteria
- [ ] Traceability with coverage %
- [ ] Issues logged and triaged; 2 RCAs; Pareto
- [ ] Weekly reports with GQM metrics
- [ ] Completion report and release decision
- [ ] AI-use record complete
- [ ] PDF + zip with `.git`, correct names
