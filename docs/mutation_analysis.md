# Mutation Analysis Report — Area 1

## 1. Tool Setup

**Tool:** mutmut v2.5.1 (Python mutation testing framework)  
**Target module:** `backend/app/services.py` (119 lines, 7 functions)  
**Test suite:** `tests/team/area1/test_services.py` (43 tests)  
**Configuration:** `backend/setup.cfg`

```ini
[mutmut]
paths_to_mutate=app/services.py
tests_dir=../tests/team/area1/
runner=cmd /c "d:\...\run_tests.bat"
```

### How to Reproduce

```bash
cd backend
mutmut run --paths-to-mutate=app/services.py
mutmut results
mutmut show <id>
```

---

## 2. Results Summary

### Initial Run (39 tests)

| Metric | Value |
|--------|-------|
| Total mutants | 81 |
| Killed | 63 |
| Survived | 18 |
| Timeout | 0 |
| Suspicious | 0 |
| **Mutation score** | **77.8%** |

### Final Run (43 tests — after killing survivors)

| Metric | Value |
|--------|-------|
| Total mutants | 81 |
| Killed | 81 |
| Survived | 0 |
| Timeout | 0 |
| Suspicious | 0 |
| **Mutation score** | **100.0%** |

---

## 3. Surviving Mutant Analysis (18 mutants)

### Category 1: String Literal Mutations (11 mutants)

Mutants 36, 40, 44, 53, 58, 65, 66, 71, 72, 73, 74 all changed error message strings by prepending "XX" and appending "XX" (e.g., `"End date cannot be..."` became `"XXEnd date cannot be...XX"`).

**Why they survived:** Our original tests used substring assertions like `assert "before" in errors["end_date"].lower()`. The mutated string still contained the substring, so the assertion passed.

**How we killed them:** Replaced all substring assertions with exact string equality checks:

```python
# Before (too weak):
assert "before" in errors["end_date"].lower()

# After (mutation-killing):
assert errors["end_date"] == "End date cannot be before the start date."
```

| Mutant ID | Line | Original String | Fix Applied |
|-----------|------|----------------|-------------|
| 36 | 71 | `"End date cannot be before the start date."` | Exact string assertion |
| 40 | 73 | `"A leave request cannot span two calendar years."` | Exact string assertion |
| 44 | 75 | `"Leave cannot start in the past."` | Exact string assertion |
| 53 | 81 | `"The selected range has no working days (Mon-Fri)."` | Exact string assertion |
| 58 | 85 | `"You already have a pending or approved..."` | Exact string assertion |
| 65 | 93 | `f"Only {remaining} day(s) of {name} "` | Exact f-string assertion |
| 66 | 94 | `f"remain for {year}."` | Exact f-string assertion |
| 71 | 107 | `f"Only {remaining} day(s) of "` (approve_request) | Exact f-string assertion |
| 72 | 108 | `f"{name} remain for "` | Exact f-string assertion |
| 73 | 109 | `f"{year}. This request needs "` | Exact f-string assertion |
| 74 | 110 | `f"{days}."` | Exact f-string assertion |

### Category 2: Boundary Mutations (3 mutants)

**Mutant 42** — Line 74: `start < date.today()` changed to `start <= date.today()`

This boundary mutation changes whether a leave request starting **today** is accepted. The original code allows `start == today`; the mutant rejects it.

- **Classification:** Missing test — no test exercised the exact boundary `start == today`.
- **Fix:** Added `test_start_today_is_valid` with mocked `date.today()` to ensure today's date is accepted:

```python
def test_start_today_is_valid(self, app, employee, casual_type):
    fake_today = date(2026, 12, 7)  # a Monday
    with patch("app.services.date") as mock_date:
        mock_date.today.return_value = fake_today
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        days, bal, errors = validate_leave_window(
            employee, casual_type, fake_today, fake_today, fake_today.year
        )
    assert "start_date" not in errors
```

**Mutant 63** — Line 91: `balance.remaining_days < days` changed to `balance.remaining_days <= days` (in `validate_leave_window`)

**Mutant 69** — Line 104: Same mutation in `approve_request`

These boundary mutations change the threshold from "strictly less than" to "less than or equal". The original code allows a request when `remaining == days` (exact fit); the mutant rejects it.

- **Classification:** Missing test — no test checked the exact boundary where remaining equals requested days.
- **Fix:** Added `test_exact_balance_is_accepted` and `test_approval_exact_balance_boundary`:

```python
def test_exact_balance_is_accepted(self, app, employee, casual_type):
    bal = balance_for(employee, casual_type, mon.year)
    bal.allocated_days = 5
    bal.used_days = 0
    # Request exactly 5 days (Mon-Fri) with 5 remaining
    days, ret_bal, errors = validate_leave_window(...)
    assert errors == {}
    assert ret_bal.remaining_days == 5
```

### Category 3: Initial Value Mutations (3 mutants)

**Mutant 46** — Line 77: `days = 0` changed to `days = 1`  
**Mutant 47** — Line 77: `days = 0` changed to `days = None`

When date validation fails, the function returns early with `days` still at its initial value. Changing that initial value from 0 to 1 or None changes the return tuple.

- **Classification:** Weak assertion — tests didn't assert the returned `days` value on error paths.
- **Fix:** Added `assert days == 0` to all error-path tests (e.g., `test_end_before_start`).

**Mutant 60** — Line 88: `balance = None` changed to `balance = ""`

Similarly, the initial `balance` value is returned when errors prevent reaching the balance check.

- **Classification:** Weak assertion — tests didn't assert `balance is None` on error paths.
- **Fix:** Added `assert bal is None` to error-path tests.

### Category 4: Assignment Mutation (1 mutant)

**Mutant 75** — Line 114: `balance.used_days += leave_request.days` changed to `balance.used_days = leave_request.days`

This changes the accumulation operator from `+=` to `=`, meaning previous usage is lost.

- **Classification:** Weak assertion — `test_approval_increases_used_days` started with `used_days=0`, so `+= days` and `= days` produce the same result.
- **Fix:** Added `test_approval_accumulates_used_days` which starts with `used_days=5`:

```python
def test_approval_accumulates_used_days(self, app, employee, admin, casual_type):
    bal.used_days = 5
    approve_request(lr, admin, None)
    assert bal.used_days == 5 + lr.days  # Fails if = instead of +=
```

---

## 4. Custom Mutation Operators

We designed two domain-specific mutation operators that go beyond mutmut's generic mutations. These target business rules specific to a leave management system.

### 4.1 Operator 1: BalanceBoundaryMutator (BR-1)

**Business rule:** An employee cannot take more leave days than their remaining balance.

**What it does:** Uses AST transformation to find comparisons of the form `balance.remaining_days < days` and shifts the threshold by +1 or -1, creating off-by-one errors in balance validation.

| Variant | Mutation | Effect | Result |
|---------|----------|--------|--------|
| +1 | `remaining < days + 1` | Rejects requests that exactly fit the balance | **KILLED** by `test_exact_balance_is_accepted` |
| -1 | `remaining < days - 1` | Allows requests that exceed balance by 1 day | **KILLED** by `test_insufficient_balance` |

**Why this matters:** Off-by-one errors in balance checks are a common business logic bug. Generic mutators only change `<` to `<=` or `!=`, but don't test shifting the boundary value itself.

### 4.2 Operator 2: WeekendSkipMutator (BR-4)

**Business rule:** Only weekdays (Monday-Friday) count as working days.

**What it does:** Uses AST transformation to find the weekday boundary check `cursor.weekday() < 5` and changes the constant 5 to 4 (excludes Friday) or 6 (includes Saturday).

| Variant | Mutation | Effect | Result |
|---------|----------|--------|--------|
| 5 -> 6 | `weekday() < 6` | Saturday counted as working day | **KILLED** by `test_weekend_only` |
| 5 -> 4 | `weekday() < 4` | Friday excluded from working days | **KILLED** by `test_full_week` |

**Why this matters:** Incorrect weekend boundaries are a domain-specific bug that generic mutators miss. A generic tool would change `< 5` to `<= 5` or `!= 5`, but wouldn't try `< 4` or `< 6` which represent realistic off-by-one errors in calendar logic.

### Implementation

Both operators are implemented as Python AST transformers in `tests/team/area1/custom_mutators.py`. They:

1. Parse `services.py` into an AST
2. Walk the tree to find the target pattern
3. Apply the mutation
4. Write the mutated file, run the test suite, and restore the original

```bash
cd backend
python ../tests/team/area1/custom_mutators.py
```

**Custom operator score: 4/4 = 100%** (all killed)

---

## 5. Tests Added to Kill Survivors

| # | Test Name | Mutants Killed | Category |
|---|-----------|---------------|----------|
| 1 | `test_start_today_is_valid` | 42 | Boundary (date) |
| 2 | `test_exact_balance_is_accepted` | 63 | Boundary (balance) |
| 3 | `test_approval_exact_balance_boundary` | 69 | Boundary (balance) |
| 4 | `test_approval_accumulates_used_days` | 75 | Assignment (+=) |

Additionally, 14 existing tests were **strengthened** (not new tests, but improved assertions):
- Exact string equality instead of substring matching (killed mutants 36, 40, 44, 53, 58, 65, 66, 71-74)
- Added `assert days == 0` and `assert bal is None` on error paths (killed mutants 46, 47, 60)

---

## 6. Evidence Files

| Evidence | Location |
|----------|----------|
| Test source code | `tests/team/area1/test_services.py` |
| Custom mutation operators | `tests/team/area1/custom_mutators.py` |
| mutmut config | `backend/setup.cfg` |
| Test runner wrapper | `backend/run_tests.bat` |
| This document | `docs/mutation_analysis.md` |

---

## 7. Lessons Learned

1. **Substring assertions are mutation-weak.** Checking `"overlap" in msg` doesn't catch `"XXoverlapXX"`. Always assert exact error messages when the message text is part of the contract.

2. **Boundary values must be tested explicitly.** Three mutants survived because we never tested `remaining_days == days` (the exact threshold) or `start == today`. Boundary value analysis and mutation testing are complementary.

3. **Initial/default values matter.** When a function returns early with a default value (`days = 0`, `balance = None`), tests must assert those defaults, or mutations to the initial value survive.

4. **Accumulation operators need non-zero starting state.** `used_days += days` and `used_days = days` are identical when starting from 0. Tests must start with a non-zero state to distinguish them.

5. **Domain-specific operators find domain-specific bugs.** Generic mutators don't test calendar boundaries or balance thresholds with shifted values. Custom operators targeting business rules (BR-1, BR-4) provide deeper assurance.
