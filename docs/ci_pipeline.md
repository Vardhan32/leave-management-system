# CI Pipeline Report — Area 1

## 1. Pipeline Design

**File:** `.github/workflows/ci.yml`  
**Trigger:** Every push to `main` and every pull request  
**No escape hatches:** No `[skip ci]`, no `continue-on-error`, no manual override

### Quality Gates

| Gate | Tool | Threshold | Fails If |
|------|------|-----------|----------|
| Unit tests | pytest | All 43 must pass | Any test fails |
| Mutation score | mutmut | 100% (0 survivors) | Any mutant survives |

### Pipeline Steps

```
quality-gate job:
  1. Checkout code
  2. Setup Python 3.11
  3. Install dependencies
  4. Run 43 unit tests (pytest -v)
  5. Run mutmut mutation testing on services.py
  6. Check mutmut results -- fail if any mutant survived

frontend-build job:
  1. Checkout code
  2. Setup Node 20
  3. npm ci + npm run build
```

---

## 2. PR That Pipeline Blocks (Failing PR)

**Branch:** `area1/weaken-balance-check`  
**Change:** Introduced an intentionally wrong assertion in `test_end_before_start` — asserts no errors when the function should return an error, and removed two boundary tests.

The pipeline fails at the **unit test** step because the broken assertion causes `test_end_before_start` to fail, blocking the PR from merging.

*(Screenshot: GitHub Actions showing red X on the PR)*

---

## 3. PR That Pipeline Passes (Passing PR)

**Branch:** `area1/all-gates-pass`  
**Change:** Contains all 43 tests with exact assertions, 100% mutation score.

The pipeline passes both gates: all tests pass and all mutants are killed.

*(Screenshot: GitHub Actions showing green check on the PR)*

---

## 4. How to Create the Two PRs

### Prerequisites

```bash
cd "d:\Semester 5\SQE Project\leave-management-system"
git init
git add -A
git commit -m "Initial commit: LeaveDesk leave management system"
```

Create a GitHub repo (e.g., `LeaveDesk`) and push:

```bash
git remote add origin https://github.com/YOUR_USERNAME/LeaveDesk.git
git branch -M main
git push -u origin main
```

### PR 1: Failing PR (pipeline blocks it)

```bash
git checkout -b area1/weaken-balance-check
```

Edit `tests/team/area1/test_services.py` — in `test_end_before_start`, change:

```python
# FROM (exact — kills the mutant):
assert errors["end_date"] == "End date cannot be before the start date."

# TO (substring — lets the mutant survive):
assert "before" in errors["end_date"].lower()
```

Also remove the `assert days == 0` and `assert bal is None` lines from that same test.

```bash
git add tests/team/area1/test_services.py
git commit -m "test: weaken balance check assertion (intentional failure)"
git push -u origin area1/weaken-balance-check
```

Open a PR on GitHub from `area1/weaken-balance-check` → `main`.  
Wait for CI — it will show a **red X**. Screenshot that.

### PR 2: Passing PR

```bash
git checkout main
git checkout -b area1/all-gates-pass
```

No changes needed — main already has the passing tests. Just push:

```bash
git push -u origin area1/all-gates-pass
```

Open a PR on GitHub from `area1/all-gates-pass` → `main`.  
Wait for CI — it will show a **green check**. Screenshot that.

---

## 5. Evidence Files

| Evidence | Location |
|----------|----------|
| CI workflow | `.github/workflows/ci.yml` |
| This document | `docs/ci_pipeline.md` |
| Failing PR screenshot | *(take from GitHub)* |
| Passing PR screenshot | *(take from GitHub)* |
