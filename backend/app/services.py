from datetime import date, timedelta

from .extensions import db
from .models import LEAVE_TYPE_DEFAULTS, LeaveBalance, LeaveRequest, LeaveType, utcnow


def ensure_leave_types():
    """Create the standard leave types once, and return them ordered."""
    existing = {leave_type.code: leave_type for leave_type in LeaveType.query.all()}
    for item in LEAVE_TYPE_DEFAULTS:
        if item["code"] not in existing:
            leave_type = LeaveType(**item)
            db.session.add(leave_type)
            existing[item["code"]] = leave_type
    db.session.flush()
    return sorted(existing.values(), key=lambda item: item.sort_order)


def working_days(start, end):
    """Number of weekdays in an inclusive date range."""
    total = 0
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            total += 1
        cursor += timedelta(days=1)
    return total


def balance_for(user, leave_type, year):
    balance = LeaveBalance.query.filter_by(
        user_id=user.id, leave_type_id=leave_type.id, year=year
    ).first()
    if balance is None:
        balance = LeaveBalance(
            user_id=user.id,
            leave_type_id=leave_type.id,
            year=year,
            allocated_days=leave_type.default_days,
            used_days=0,
        )
        db.session.add(balance)
        db.session.flush()
    return balance


def balances_for(user, year):
    return [
        balance_for(user, leave_type, year)
        for leave_type in LeaveType.query.order_by(LeaveType.sort_order.asc()).all()
    ]


def overlapping_request(user_id, start, end, exclude_id=None):
    query = LeaveRequest.query.filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.status.in_(("pending", "approved")),
        LeaveRequest.start_date <= end,
        LeaveRequest.end_date >= start,
    )
    if exclude_id is not None:
        query = query.filter(LeaveRequest.id != exclude_id)
    return query.first()


def validate_leave_window(user, leave_type, start, end, year):
    """Validate dates, overlap, and remaining balance for a new request."""
    errors = {}

    if end < start:
        errors["end_date"] = "End date cannot be before the start date."
    elif start.year != end.year:
        errors["end_date"] = "A leave request cannot span two calendar years."
    elif start < date.today():
        errors["start_date"] = "Leave cannot start in the past."

    days = 0
    if not errors:
        days = working_days(start, end)
        if days == 0:
            errors["end_date"] = "The selected range has no working days (Mon–Fri)."

    if not errors and overlapping_request(user.id, start, end):
        errors["start_date"] = (
            "You already have a pending or approved request that overlaps these dates."
        )

    balance = None
    if not errors:
        balance = balance_for(user, leave_type, year)
        if balance.remaining_days < days:
            errors["leave_type_id"] = (
                f"Only {balance.remaining_days} day(s) of {leave_type.name} "
                f"remain for {year}."
            )

    return days, balance, errors


def approve_request(leave_request, reviewer, note):
    balance = balance_for(
        leave_request.user, leave_request.leave_type, leave_request.start_date.year
    )
    if balance.remaining_days < leave_request.days:
        return {
            "leave_type_id": (
                f"Only {balance.remaining_days} day(s) of "
                f"{leave_request.leave_type.name} remain for "
                f"{leave_request.start_date.year}. This request needs "
                f"{leave_request.days}."
            )
        }

    balance.used_days += leave_request.days
    leave_request.status = "approved"
    leave_request.reviewed_by_id = reviewer.id
    leave_request.review_note = note
    leave_request.reviewed_at = utcnow()
    return None
