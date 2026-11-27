"""White-box unit tests for backend/app/services.py.

Targets 100 % statement + branch coverage of all seven functions:
  ensure_leave_types, working_days, balance_for, balances_for,
  overlapping_request, validate_leave_window, approve_request.

Covers the four business rules:
  BR-1  Leave balance boundary
  BR-2  Date validation (end >= start, same year, no past dates)
  BR-3  Overlap detection
  BR-4  Working days only (Mon–Fri)
"""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import LeaveBalance, LeaveRequest, LeaveType, User
from app.services import (
    approve_request,
    balance_for,
    balances_for,
    ensure_leave_types,
    overlapping_request,
    validate_leave_window,
    working_days,
)


# ── helpers ──────────────────────────────────────────────────────

def _future_weekday(offset_weeks=1):
    """Return a Monday at least one week in the future."""
    today = date.today()
    days_ahead = 7 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead + 7 * (offset_weeks - 1))


def _make_request(user, leave_type, start, end, status="pending"):
    days = working_days(start, end)
    lr = LeaveRequest(
        user_id=user.id,
        leave_type_id=leave_type.id,
        start_date=start,
        end_date=end,
        days=days,
        reason="Unit test leave",
        status=status,
    )
    db.session.add(lr)
    db.session.flush()
    return lr


# ═══════════════════════════════════════════════════════════════
#  1. ensure_leave_types
# ═══════════════════════════════════════════════════════════════

class TestEnsureLeaveTypes:
    def test_creates_standard_types_on_first_call(self, app):
        """All three default leave types are created and returned sorted."""
        LeaveType.query.delete()
        db.session.commit()

        result = ensure_leave_types()
        assert len(result) == 3
        codes = [lt.code for lt in result]
        assert codes == ["CASUAL", "SICK", "EARNED"]

    def test_idempotent_when_types_already_exist(self, app):
        """Calling again when types already exist creates no duplicates."""
        result = ensure_leave_types()
        assert len(result) == 3
        counts = LeaveType.query.count()
        ensure_leave_types()
        assert LeaveType.query.count() == counts


# ═══════════════════════════════════════════════════════════════
#  2. working_days  (BR-4)
# ═══════════════════════════════════════════════════════════════

class TestWorkingDays:
    def test_single_weekday(self):
        """A single Monday → 1 working day."""
        mon = date(2026, 11, 23)  # Monday
        assert working_days(mon, mon) == 1

    def test_full_week(self):
        """Mon to Fri → 5 working days."""
        mon = date(2026, 11, 23)
        fri = date(2026, 11, 27)
        assert working_days(mon, fri) == 5

    def test_weekend_only(self):
        """Sat to Sun → 0 working days."""
        sat = date(2026, 11, 28)
        sun = date(2026, 11, 29)
        assert working_days(sat, sun) == 0

    def test_two_full_weeks(self):
        """Mon to Fri across two weeks → 10 working days."""
        mon = date(2026, 11, 23)
        fri_next = date(2026, 12, 4)
        assert working_days(mon, fri_next) == 10

    def test_single_saturday(self):
        """Saturday only → 0."""
        sat = date(2026, 11, 28)
        assert working_days(sat, sat) == 0

    def test_single_sunday(self):
        """Sunday only → 0."""
        sun = date(2026, 11, 29)
        assert working_days(sun, sun) == 0

    def test_mid_week_range(self):
        """Wed to Thu → 2 working days."""
        wed = date(2026, 11, 25)
        thu = date(2026, 11, 26)
        assert working_days(wed, thu) == 2

    def test_range_spanning_weekend(self):
        """Thu to next Tue (includes Sat, Sun) → 4 working days."""
        thu = date(2026, 11, 26)
        tue = date(2026, 12, 1)
        assert working_days(thu, tue) == 4


# ═══════════════════════════════════════════════════════════════
#  3. balance_for  (BR-1 setup)
# ═══════════════════════════════════════════════════════════════

class TestBalanceFor:
    def test_creates_balance_when_none_exists(self, app, employee, casual_type):
        """First call allocates default days."""
        bal = balance_for(employee, casual_type, 2026)
        assert bal.allocated_days == 12
        assert bal.used_days == 0
        assert bal.remaining_days == 12

    def test_returns_existing_balance(self, app, employee, casual_type):
        """Second call returns same record, no duplicates."""
        b1 = balance_for(employee, casual_type, 2026)
        b2 = balance_for(employee, casual_type, 2026)
        assert b1.id == b2.id

    def test_different_years_get_separate_balances(self, app, employee, casual_type):
        """Each year gets its own balance row."""
        b1 = balance_for(employee, casual_type, 2025)
        b2 = balance_for(employee, casual_type, 2026)
        assert b1.id != b2.id


# ═══════════════════════════════════════════════════════════════
#  4. balances_for
# ═══════════════════════════════════════════════════════════════

class TestBalancesFor:
    def test_returns_balance_for_each_leave_type(self, app, employee):
        """Should return 3 balances (one per leave type)."""
        result = balances_for(employee, 2026)
        assert len(result) == 3

    def test_balances_ordered_by_sort_order(self, app, employee):
        """Balances come back in CASUAL, SICK, EARNED order."""
        result = balances_for(employee, 2026)
        types = [b.leave_type.code for b in result]
        assert types == ["CASUAL", "SICK", "EARNED"]


# ═══════════════════════════════════════════════════════════════
#  5. overlapping_request  (BR-3)
# ═══════════════════════════════════════════════════════════════

class TestOverlappingRequest:
    def test_no_overlap_when_no_requests_exist(self, app, employee, casual_type):
        mon = _future_weekday()
        assert overlapping_request(employee.id, mon, mon) is None

    def test_detects_exact_overlap(self, app, employee, casual_type):
        """Pending request on same dates → overlap detected."""
        mon = _future_weekday()
        fri = mon + timedelta(days=4)
        _make_request(employee, casual_type, mon, fri, "pending")
        db.session.commit()
        assert overlapping_request(employee.id, mon, fri) is not None

    def test_detects_partial_overlap(self, app, employee, casual_type):
        """New request starts mid-way through existing → overlap."""
        mon = _future_weekday()
        fri = mon + timedelta(days=4)
        _make_request(employee, casual_type, mon, fri, "approved")
        db.session.commit()
        wed = mon + timedelta(days=2)
        next_fri = fri + timedelta(days=7)
        assert overlapping_request(employee.id, wed, next_fri) is not None

    def test_no_overlap_with_rejected_request(self, app, employee, casual_type):
        """Rejected requests are not considered."""
        mon = _future_weekday()
        _make_request(employee, casual_type, mon, mon, "rejected")
        db.session.commit()
        assert overlapping_request(employee.id, mon, mon) is None

    def test_no_overlap_with_cancelled_request(self, app, employee, casual_type):
        """Cancelled requests are not considered."""
        mon = _future_weekday()
        _make_request(employee, casual_type, mon, mon, "cancelled")
        db.session.commit()
        assert overlapping_request(employee.id, mon, mon) is None

    def test_exclude_id_skips_given_request(self, app, employee, casual_type):
        """exclude_id filters out the given request (used for edits)."""
        mon = _future_weekday()
        lr = _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        assert overlapping_request(employee.id, mon, mon, exclude_id=lr.id) is None

    def test_exclude_id_none_still_matches(self, app, employee, casual_type):
        """When exclude_id is None, the request is still matched."""
        mon = _future_weekday()
        _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        assert overlapping_request(employee.id, mon, mon, exclude_id=None) is not None

    def test_adjacent_non_overlapping(self, app, employee, casual_type):
        """Request ending day before new one starts → no overlap."""
        mon = _future_weekday()
        tue = mon + timedelta(days=1)
        _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        assert overlapping_request(employee.id, tue, tue) is None


# ═══════════════════════════════════════════════════════════════
#  6. validate_leave_window  (BR-1, BR-2, BR-3, BR-4)
# ═══════════════════════════════════════════════════════════════

class TestValidateLeaveWindow:

    # ── BR-2: end < start ──
    def test_end_before_start(self, app, employee, casual_type):
        start = _future_weekday()
        end = start - timedelta(days=1)
        days, bal, errors = validate_leave_window(
            employee, casual_type, start, end, start.year
        )
        assert errors["end_date"] == "End date cannot be before the start date."
        assert days == 0
        assert bal is None

    # ── BR-2: cross-year span ──
    def test_cross_year_rejected(self, app, employee, casual_type):
        start = date(2026, 12, 28)
        end = date(2027, 1, 2)
        days, bal, errors = validate_leave_window(
            employee, casual_type, start, end, start.year
        )
        assert errors["end_date"] == "A leave request cannot span two calendar years."
        assert days == 0
        assert bal is None

    # ── BR-2: start in the past ──
    def test_past_start_date(self, app, employee, casual_type):
        yesterday = date.today() - timedelta(days=1)
        days, bal, errors = validate_leave_window(
            employee, casual_type, yesterday, yesterday, yesterday.year
        )
        assert errors["start_date"] == "Leave cannot start in the past."
        assert days == 0
        assert bal is None

    # ── BR-2: boundary — start == today is allowed ──
    def test_start_today_is_valid(self, app, employee, casual_type):
        """start == date.today() should NOT be rejected as 'in the past'."""
        fake_today = date(2026, 12, 7)  # a Monday
        with patch("app.services.date") as mock_date:
            mock_date.today.return_value = fake_today
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            days, bal, errors = validate_leave_window(
                employee, casual_type, fake_today, fake_today, fake_today.year
            )
        assert "start_date" not in errors

    # ── BR-4: weekend-only range ──
    def test_weekend_only_range(self, app, employee, casual_type):
        sat = _future_weekday() + timedelta(days=5)  # Saturday
        sun = sat + timedelta(days=1)
        days, bal, errors = validate_leave_window(
            employee, casual_type, sat, sun, sat.year
        )
        assert errors["end_date"] == "The selected range has no working days (Mon–Fri)."
        assert days == 0
        assert bal is None

    # ── BR-3: overlap ──
    def test_overlap_error(self, app, employee, casual_type):
        mon = _future_weekday()
        _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        days, bal, errors = validate_leave_window(
            employee, casual_type, mon, mon, mon.year
        )
        assert errors["start_date"] == (
            "You already have a pending or approved request that overlaps these dates."
        )
        assert bal is None

    # ── BR-1: insufficient balance ──
    def test_insufficient_balance(self, app, employee, casual_type):
        bal = balance_for(employee, casual_type, 2026)
        bal.used_days = bal.allocated_days  # exhaust balance
        db.session.commit()
        mon = _future_weekday()
        days, ret_bal, errors = validate_leave_window(
            employee, casual_type, mon, mon, 2026
        )
        assert errors["leave_type_id"] == (
            f"Only {ret_bal.remaining_days} day(s) of {casual_type.name} "
            f"remain for 2026."
        )

    # ── BR-1: boundary — remaining_days == days is accepted ──
    def test_exact_balance_is_accepted(self, app, employee, casual_type):
        """When remaining == requested days, the request should pass (not fail)."""
        mon = _future_weekday()
        fri = mon + timedelta(days=4)
        bal = balance_for(employee, casual_type, mon.year)
        bal.allocated_days = 5
        bal.used_days = 0
        db.session.commit()
        days, ret_bal, errors = validate_leave_window(
            employee, casual_type, mon, fri, mon.year
        )
        assert errors == {}
        assert days == 5
        assert ret_bal.remaining_days == 5

    # ── Happy path ──
    def test_valid_request(self, app, employee, casual_type):
        mon = _future_weekday()
        fri = mon + timedelta(days=4)
        days, bal, errors = validate_leave_window(
            employee, casual_type, mon, fri, mon.year
        )
        assert errors == {}
        assert days == 5
        assert bal is not None
        assert bal.remaining_days >= 5

    # ── Errors short-circuit: first date error skips overlap/balance checks ──
    def test_date_error_skips_overlap_and_balance_checks(self, app, employee, casual_type):
        """When end < start, we get only end_date error, nothing about overlap or balance."""
        mon = _future_weekday()
        _make_request(employee, casual_type, mon, mon, "pending")
        bal = balance_for(employee, casual_type, mon.year)
        bal.used_days = bal.allocated_days
        db.session.commit()
        end = mon - timedelta(days=1)
        _, _, errors = validate_leave_window(
            employee, casual_type, mon, end, mon.year
        )
        assert "end_date" in errors
        assert "start_date" not in errors
        assert "leave_type_id" not in errors

    # ── Compound condition: not errors AND overlapping ──
    def test_no_overlap_passes_to_balance_check(self, app, employee, casual_type):
        """When dates valid and no overlap, balance is checked."""
        mon = _future_weekday()
        days, bal, errors = validate_leave_window(
            employee, casual_type, mon, mon, mon.year
        )
        assert errors == {}
        assert days == 1


# ═══════════════════════════════════════════════════════════════
#  7. approve_request  (BR-1)
# ═══════════════════════════════════════════════════════════════

class TestApproveRequest:
    def test_successful_approval(self, app, employee, admin, casual_type):
        mon = _future_weekday()
        lr = _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        result = approve_request(lr, admin, "Approved, enjoy!")
        assert result is None
        assert lr.status == "approved"
        assert lr.reviewed_by_id == admin.id
        assert lr.review_note == "Approved, enjoy!"
        assert lr.reviewed_at is not None

    def test_approval_increases_used_days(self, app, employee, admin, casual_type):
        bal = balance_for(employee, casual_type, 2026)
        initial_used = bal.used_days
        mon = _future_weekday()
        lr = _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        approve_request(lr, admin, None)
        assert bal.used_days == initial_used + lr.days

    def test_approval_denied_when_balance_insufficient(self, app, employee, admin, casual_type):
        bal = balance_for(employee, casual_type, 2026)
        bal.used_days = bal.allocated_days
        db.session.commit()
        mon = _future_weekday()
        lr = _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        result = approve_request(lr, admin, "")
        assert result is not None
        expected_msg = (
            f"Only {bal.remaining_days} day(s) of "
            f"{casual_type.name} remain for "
            f"{lr.start_date.year}. This request needs "
            f"{lr.days}."
        )
        assert result["leave_type_id"] == expected_msg
        assert lr.status == "pending"

    def test_approval_exact_balance_boundary(self, app, employee, admin, casual_type):
        """When remaining == requested days, approval should succeed."""
        bal = balance_for(employee, casual_type, 2026)
        bal.allocated_days = 1
        bal.used_days = 0
        db.session.commit()
        mon = _future_weekday()
        lr = _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        result = approve_request(lr, admin, None)
        assert result is None
        assert lr.status == "approved"

    def test_approval_accumulates_used_days(self, app, employee, admin, casual_type):
        """used_days += days, not used_days = days (must accumulate)."""
        bal = balance_for(employee, casual_type, 2026)
        bal.allocated_days = 20
        bal.used_days = 5
        db.session.commit()
        mon = _future_weekday()
        lr = _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        approve_request(lr, admin, None)
        assert bal.used_days == 5 + lr.days

    def test_approval_with_null_note(self, app, employee, admin, casual_type):
        mon = _future_weekday()
        lr = _make_request(employee, casual_type, mon, mon, "pending")
        db.session.commit()
        result = approve_request(lr, admin, None)
        assert result is None
        assert lr.review_note is None


# ═══════════════════════════════════════════════════════════════
#  8. Model property tests (remaining_days edge cases)
# ═══════════════════════════════════════════════════════════════

class TestLeaveBalanceRemainingDays:
    def test_remaining_days_normal(self, app, employee, casual_type):
        bal = balance_for(employee, casual_type, 2026)
        bal.allocated_days = 12
        bal.used_days = 5
        assert bal.remaining_days == 7

    def test_remaining_days_zero(self, app, employee, casual_type):
        bal = balance_for(employee, casual_type, 2026)
        bal.used_days = bal.allocated_days
        assert bal.remaining_days == 0

    def test_remaining_days_never_negative(self, app, employee, casual_type):
        """Even if used > allocated, remaining is floored at 0."""
        bal = balance_for(employee, casual_type, 2026)
        bal.used_days = bal.allocated_days + 5
        assert bal.remaining_days == 0
