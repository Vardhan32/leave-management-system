# Briefing for Claude Code — shared test management and final submission

You are helping a three-person Software Quality Engineering group with the
documents they share. Any member can be questioned on any of them in the
viva, so the documents must reflect the group's real decisions and evidence.

Read `tests/team/handoff/README.md` and `tests/team/handoff/shared-human.md`
first. The human file lists every document and its required content.

## Rules for this session

1. **Ask before any decision**: scope, risk scores, thresholds, exit
   criteria, severity and priority, release or hold. You may propose values
   with reasons, but the group decides. Never invent hours, results or
   numbers; take them from files in the repo or from the member.
2. **Do not commit or push**, and do not create GitHub Issues unless the
   member asks and `gh` is authenticated as them. Never add Claude as a
   co-author or collaborator.
3. Explain any technique the member may not know (three-point estimation,
   GQM, 5 Whys, fishbone, Pareto) briefly the first time.
4. Write plainly, neutral tone, no filler. Keep tables where the brief asks
   for tables.
5. Every figure in a document should point to its source file (a report under
   `tests/team/**/reports/`, a CI run, an Issue).
6. Keep a list of what you drafted for the AI-use record.

## Inputs that already exist

- Workflows, shared records, test basis: `tests/team/api/README.md`
- Requirement and rule ids: `tests/team/api/support/requirements.py`
- Endpoint weaknesses with suggested fixes: `tests/team/api/reports/endpoint_weaknesses.md`
- API coverage: `tests/team/api/reports/api_coverage.md` (after a run)
- Test ↔ requirement tags and outcomes: `tests/team/api/reports/test_traceability.csv` (after a run)
- Area plans: `tests/team/handoff/area1-human.md`, `area3-human.md`
- Upstream facts: `README.md`, baseline commit `b002faa4b46ba2090489c200c61787551591c70d`

Areas 1 and 3 will add their own reports under `docs/team/` and
`tests/team/`; check for them before writing anything that depends on them.

## Tasks, in order

Use a task list. Stop after each task, summarise briefly, wait for the member.

### Task 1 — scope and test basis
Draft `docs/team/scope.md` as described in `shared-human.md` section 1. Mark
every expected behaviour with its source (README line, code file and
function) or label it as an assumption with a reason. Ask the member to
confirm the requirement list and each assumption.

### Task 2 — test plan and estimates
Draft `docs/team/test_plan.md` and `docs/team/estimation.md`. Ask the member
for roles, schedule dates, and O / M / P hours per area; compute
(O + 4M + P) / 6. Leave an "actual" column to fill later.

### Task 3 — risk register and exit criteria
Propose at least 8 product and 2 project risks (the human file lists ideas
from real findings). Ask the member to score likelihood and impact; compute
scores, levels, and a 5 × 5 matrix in Markdown. Map each risk to technique
and depth, and to tests or findings. Propose exit criteria (3+, measurable,
2+ on the top risks) and ask for agreement. Then update the `R-?`
placeholders in `tests/team/api/reports/endpoint_weaknesses.md` after asking.

### Task 4 — traceability
Write a small script `tests/team/tools/traceability.py` that merges the
`test_traceability.csv` files from every area's reports (same columns:
test, requirements, outcome) and outputs `docs/team/traceability.md`:
requirement → tests → results → covered, plus requirements coverage %.
Run it and show the output. Requirements with no passing test must be listed.

### Task 5 — defects
From `endpoint_weaknesses.md` and the other areas' findings, draft one Issue
body per defect (title, steps, expected, actual, evidence, severity,
priority, category, linked risk) in `docs/team/issues_to_create.md`. After
the issues exist, help with triage notes, two RCAs (5 Whys + fishbone as a
Mermaid diagram or table, corrective and preventive action) for the defects
the group picks, and a Pareto chart by category (script producing a PNG, or a
table the member charts).

### Task 6 — weekly reports
Template `docs/team/progress/week-N.md`: planned vs done, deviations, control
actions, GQM (goal, questions, metrics) with defect density, requirements
coverage, reopen rate. Ask for KLOC basis and the counts; compute and
interpret, do not guess.

### Task 7 — completion report and release decision
Once all areas have results, draft `docs/team/completion_report.md`: tested /
not tested, deviations, open defects, residual risk per risk, actual vs target
for each exit criterion, and a release or hold recommendation that follows
from those numbers. The group makes the final call.

### Task 8 — final package check
Walk through the checklist in `shared-human.md` section 11 against the repo:
report what is present and missing. Give the member the commands to build
the zip with `.git` included and the exact file names. Remind them the PDF
must contain the AI-use record and the public GitHub link.
