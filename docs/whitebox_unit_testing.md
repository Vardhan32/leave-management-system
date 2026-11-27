# White-Box Unit Testing Report — Area 1

## 1. Scope

**Target module:** `backend/app/services.py` — the core business logic layer  
**Test location:** `tests/team/area1/test_services.py`  
**Test framework:** pytest 9.2.0 with pytest-cov 7.1.0  
**Total tests:** 43  
**All passing:** Yes

### Functions Under Test

| # | Function | Lines | Purpose |
|---|----------|-------|---------|
| 1 | `ensure_leave_types()` | 7–16 | Creates standard leave types (idempotent) |
| 2 | `working_days(start, end)` | 19–27 | Counts weekdays in inclusive date range (BR-4) |
| 3 | `balance_for(user, leave_type, year)` | 30–44 | Gets or creates a leave balance record (BR-1) |
| 4 | `balances_for(user, year)` | 47–51 | Returns balances for all leave types |
| 5 | `overlapping_request(user_id, start, end, exclude_id)` | 54–63 | Detects date overlaps with pending/approved requests (BR-3) |
| 6 | `validate_leave_window(user, leave_type, start, end, year)` | 66–97 | Validates all business rules for a leave request (BR-1,2,3,4) |
| 7 | `approve_request(leave_request, reviewer, note)` | 100–119 | Approves a request and deducts balance (BR-1) |

### Business Rules Covered

| ID | Business Rule | Functions | Test Count |
|----|---------------|-----------|------------|
| BR-1 | Leave balance boundary (can't exceed allocated days) | `balance_for`, `validate_leave_window`, `approve_request` | 7 |
| BR-2 | Date validation (end ≥ start, same year, no past dates) | `validate_leave_window` | 4 |
| BR-3 | Overlap detection (no pending/approved overlap) | `overlapping_request`, `validate_leave_window` | 9 |
| BR-4 | Working days only (Mon–Fri, weekends don't count) | `working_days`, `validate_leave_window` | 9 |

---

## 2. Coverage Results

### Statement + Branch Coverage

```
Name             Stmts   Miss   Branch   BrPart   Cover   Missing
──────────────────────────────────────────────────────────────────
app/services.py     65      0       30        0   100.0%
```

**Statement coverage: 100%** (65/65 statements executed)  
**Branch coverage: 100%** (30/30 branches taken)  
**Partial branches: 0** (every branch taken in both directions)

*(Screenshot: HTML coverage report at `backend/coverage_area1/index.html` — to be inserted)*

---

## 3. Test Cases by Function

### 3.1 ensure_leave_types (2 tests)

| # | Test | What It Covers |
|---|------|----------------|
| 1 | `test_creates_standard_types_on_first_call` | `if item["code"] not in existing` → True branch |
| 2 | `test_idempotent_when_types_already_exist` | `if item["code"] not in existing` → False branch |

### 3.2 working_days (8 tests) — BR-4

| # | Test | Input | Expected | Branch Exercised |
|---|------|-------|----------|------------------|
| 1 | `test_single_weekday` | Mon–Mon | 1 | while=T, weekday<5=T, while=F |
| 2 | `test_full_week` | Mon–Fri | 5 | while=T×5(weekday<5=T), while=F |
| 3 | `test_weekend_only` | Sat–Sun | 0 | while=T(weekday<5=F)×2, while=F |
| 4 | `test_two_full_weeks` | Mon–Fri×2 | 10 | Multiple iterations both branches |
| 5 | `test_single_saturday` | Sat–Sat | 0 | while=T, weekday<5=F, while=F |
| 6 | `test_single_sunday` | Sun–Sun | 0 | while=T, weekday<5=F, while=F |
| 7 | `test_mid_week_range` | Wed–Thu | 2 | while=T×2(weekday<5=T), while=F |
| 8 | `test_range_spanning_weekend` | Thu–Tue | 4 | Mixed weekday/weekend iterations |

### 3.3 balance_for (3 tests) — BR-1

| # | Test | Branch |
|---|------|--------|
| 1 | `test_creates_balance_when_none_exists` | `if balance is None` → True |
| 2 | `test_returns_existing_balance` | `if balance is None` → False |
| 3 | `test_different_years_get_separate_balances` | Verifies year isolation |

### 3.4 balances_for (2 tests)

| # | Test | What It Covers |
|---|------|----------------|
| 1 | `test_returns_balance_for_each_leave_type` | List comprehension with 3 types |
| 2 | `test_balances_ordered_by_sort_order` | Verifies sort_order ordering |

### 3.5 overlapping_request (8 tests) — BR-3

| # | Test | Branch |
|---|------|--------|
| 1 | `test_no_overlap_when_no_requests_exist` | query.first() → None |
| 2 | `test_detects_exact_overlap` | Exact date match → overlap found |
| 3 | `test_detects_partial_overlap` | Partial date overlap → found |
| 4 | `test_no_overlap_with_rejected_request` | `status.in_(pending,approved)` filters out rejected |
| 5 | `test_no_overlap_with_cancelled_request` | `status.in_(pending,approved)` filters out cancelled |
| 6 | `test_exclude_id_skips_given_request` | `if exclude_id is not None` → True |
| 7 | `test_exclude_id_none_still_matches` | `if exclude_id is not None` → False |
| 8 | `test_adjacent_non_overlapping` | Adjacent dates → no overlap |

### 3.6 validate_leave_window (9 tests) — BR-1, BR-2, BR-3, BR-4

| # | Test | Branch Path |
|---|------|-------------|
| 1 | `test_end_before_start` | `end < start` → T |
| 2 | `test_cross_year_rejected` | `end < start` → F, `start.year != end.year` → T |
| 3 | `test_past_start_date` | First two → F, `start < date.today()` → T |
| 4 | `test_weekend_only_range` | Date checks pass, `not errors` → T, `days == 0` → T |
| 5 | `test_overlap_error` | Date checks pass, days > 0, `not errors AND overlap` → T |
| 6 | `test_insufficient_balance` | All pass, `remaining_days < days` → T |
| 7 | `test_valid_request` | All checks pass → happy path |
| 8 | `test_date_error_skips_overlap_and_balance` | Error early → `not errors` → F (skips later) |
| 9 | `test_no_overlap_passes_to_balance_check` | No overlap → `not errors AND overlap` → F, moves to balance |

### 3.7 approve_request (4 tests) — BR-1

| # | Test | Branch |
|---|------|--------|
| 1 | `test_successful_approval` | `remaining_days < days` → F (success) |
| 2 | `test_approval_increases_used_days` | Verifies `used_days += days` |
| 3 | `test_approval_denied_when_balance_insufficient` | `remaining_days < days` → T |
| 4 | `test_approval_with_null_note` | `note=None` path |

### 3.8 LeaveBalance.remaining_days (3 tests) — BR-1

| # | Test | Scenario |
|---|------|----------|
| 1 | `test_remaining_days_normal` | allocated=12, used=5 → 7 |
| 2 | `test_remaining_days_zero` | used == allocated → 0 |
| 3 | `test_remaining_days_never_negative` | used > allocated → `max(..., 0)` → 0 |

---

## 4. Multiple Condition Coverage (MCC)

### Critical Function: `validate_leave_window()`

This function contains several compound Boolean conditions. We perform MCC analysis on the two key compound conditions.

### 4.1 Condition C1: Line 83 — `if not errors and overlapping_request(user.id, start, end)`

This is a compound condition with two atomic conditions:
- **A** = `not errors` (errors dict is empty)
- **B** = `overlapping_request(user.id, start, end)` returns a truthy value

#### MCC Truth Table

| Row | A (`not errors`) | B (`overlap exists`) | A and B | Outcome | Test Case |
|-----|-----------------|---------------------|---------|---------|-----------|
| 1 | F | — (short-circuit) | F | Skip overlap check | `test_end_before_start` (errors from date check) |
| 2 | T | F | F | No overlap error | `test_valid_request` |
| 3 | T | T | T | Overlap error added | `test_overlap_error` |
| 4 | F | — (short-circuit) | F | Skip (errors from days==0) | `test_weekend_only_range` |

> Row 1 and 4 both cover A=F; B is not evaluated due to Python's short-circuit `and`. Rows 2 and 3 cover A=T with both B values.

**All feasible combinations covered.** (A=F,B=T is infeasible due to short-circuit; A=F,B=F is also short-circuited.)

### 4.2 Condition C2: Line 70–74 — if/elif/elif chain

```python
if end < start:              # D1
elif start.year != end.year: # D2
elif start < date.today():   # D3
```

This is a chained condition where each predicate is evaluated only if the previous ones were False.

| Row | D1 (`end < start`) | D2 (`year != year`) | D3 (`start < today`) | Path | Test Case |
|-----|-------------------|--------------------|--------------------|------|-----------|
| 1 | T | — | — | end_date error | `test_end_before_start` |
| 2 | F | T | — | end_date error (cross-year) | `test_cross_year_rejected` |
| 3 | F | F | T | start_date error (past) | `test_past_start_date` |
| 4 | F | F | F | Passes date validation | `test_valid_request` |

**All branches covered.**

### 4.3 Condition C3: Line 78 — `if not errors` (after date validation)

| Row | `not errors` | Outcome | Test Case |
|-----|-------------|---------|-----------|
| 1 | T | Proceeds to `working_days` check | `test_valid_request` |
| 2 | F | Skips working days check | `test_end_before_start` |

### 4.4 Condition C4: Line 80 — `if days == 0`

| Row | `days == 0` | Outcome | Test Case |
|-----|------------|---------|-----------|
| 1 | T | Error: no working days | `test_weekend_only_range` |
| 2 | F | Proceeds to overlap check | `test_valid_request` |

### 4.5 Condition C5: Line 89 — `if not errors` (before balance check)

| Row | `not errors` | Outcome | Test Case |
|-----|-------------|---------|-----------|
| 1 | T | Checks balance | `test_insufficient_balance` / `test_valid_request` |
| 2 | F | Skips balance check, returns errors | `test_overlap_error` |

### 4.6 Condition C6: Line 91 — `if balance.remaining_days < days`

| Row | `remaining < days` | Outcome | Test Case |
|-----|-------------------|---------|-----------|
| 1 | T | Error: insufficient balance | `test_insufficient_balance` |
| 2 | F | No error, returns valid result | `test_valid_request` |

---

## 5. MC/DC (Modified Condition/Decision Coverage)

MC/DC requires that for each condition in a compound decision, there exists a pair of test cases where:
- Only that condition changes value
- The decision outcome changes

### 5.1 Decision: `not errors and overlapping_request(...)` (Line 83)

| Condition | Independence Pair | A (`not errors`) | B (`overlap`) | Decision | Why |
|-----------|------------------|-----------------|--------------|----------|-----|
| **A** | Row 1 ↔ Row 3 | F→T | —→T | F→T | A alone flips decision |
| **B** | Row 2 ↔ Row 3 | T | F→T | F→T | B alone flips decision |

**MC/DC pair for A:** `test_date_error_skips_overlap_and_balance_checks` (A=F) ↔ `test_overlap_error` (A=T, B=T)  
**MC/DC pair for B:** `test_valid_request` (A=T, B=F) ↔ `test_overlap_error` (A=T, B=T)

### 5.2 Decision: `if end < start` / `elif start.year != end.year` / `elif start < date.today()` (Lines 70–74)

Since this is an `if/elif/elif` chain (not a single compound condition with `and`/`or`), each predicate acts as an independent decision point. MC/DC for each:

| Predicate | Pair (T↔F) | Test T | Test F |
|-----------|-----------|--------|--------|
| D1: `end < start` | `test_end_before_start` ↔ `test_cross_year_rejected` | T→error | F→check D2 |
| D2: `start.year != end.year` | `test_cross_year_rejected` ↔ `test_past_start_date` | T→error | F→check D3 |
| D3: `start < date.today()` | `test_past_start_date` ↔ `test_valid_request` | T→error | F→pass |

### 5.3 Decision: `remaining_days < days` (Line 91, also in `approve_request` Line 104)

| Condition | Pair (T↔F) | Test T | Test F |
|-----------|-----------|--------|--------|
| `remaining < days` | `test_insufficient_balance` ↔ `test_valid_request` | T→error | F→pass |

In `approve_request`:
| Condition | Pair (T↔F) | Test T | Test F |
|-----------|-----------|--------|--------|
| `remaining < days` | `test_approval_denied...` ↔ `test_successful_approval` | T→error dict | F→None |

---

## 6. Justification for Uncovered Code

The tests in `tests/team/area1/` target `services.py` (business logic layer). The following modules have less than 100% coverage from these tests alone:

| Module | Coverage | Justification |
|--------|----------|---------------|
| `api/leaves.py` | 14.2% | API endpoint layer — covered by Area 2 (API testing) |
| `api/auth.py` | 22.7% | Authentication endpoints — covered by Area 2 |
| `api/dashboard.py` | 23.9% | Dashboard aggregation — covered by Area 2 |
| `utils.py` | 20.0% | Validator class and utilities — covered by Area 2 |
| `models.py` | 92.3% | Serialization methods (`to_dict`) — exercised via API tests |
| `__init__.py` | 64.2% | Error handlers and CLI commands — framework glue code |
| `seed.py` | 0.0% | Demo data seeder — not production code, not tested |

The **business logic in `services.py` has 100% statement and branch coverage** from Area 1 tests alone.

---

## 7. Evidence Files

| Evidence | Location |
|----------|----------|
| Test source code | `tests/team/area1/test_services.py` |
| Test configuration | `tests/team/area1/conftest.py` |
| Coverage HTML report | `backend/coverage_area1/index.html` |
| Coverage XML report | `backend/coverage_area1.xml` |
| This document | `docs/whitebox_unit_testing.md` |

### How to Reproduce

```bash
cd backend
SQLALCHEMY_DISABLE_CEXT=1 python -m pytest ../tests/team/area1/test_services.py \
    -v --cov=app --cov-branch \
    --cov-report=term-missing \
    --cov-report=html:coverage_area1
```

---
