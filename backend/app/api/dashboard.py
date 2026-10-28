from datetime import date

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from ..extensions import db
from ..models import LeaveRequest, User
from ..services import balances_for, ensure_leave_types
from ..utils import admin_required, current_user

bp = Blueprint("dashboard", __name__, url_prefix="/api")


def approved_days_in_year(user_id, year):
    return (
        db.session.query(func.coalesce(func.sum(LeaveRequest.days), 0))
        .filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date >= date(year, 1, 1),
            LeaveRequest.start_date <= date(year, 12, 31),
        )
        .scalar()
        or 0
    )


@bp.get("/dashboard")
@jwt_required()
def dashboard():
    user = current_user()
    today = date.today()
    year = today.year

    if user.is_admin:
        employee_query = User.query.filter_by(role="employee", is_active=True)
        headcount = employee_query.count()
        pending_requests = (
            LeaveRequest.query.filter_by(status="pending")
            .order_by(LeaveRequest.created_at.asc())
            .all()
        )
        on_leave = (
            LeaveRequest.query.filter(
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= today,
                LeaveRequest.end_date >= today,
            )
            .order_by(LeaveRequest.start_date.asc())
            .all()
        )
        upcoming = (
            LeaveRequest.query.filter(
                LeaveRequest.status == "approved",
                LeaveRequest.start_date > today,
            )
            .order_by(LeaveRequest.start_date.asc())
            .limit(5)
            .all()
        )
        recent_decisions = (
            LeaveRequest.query.filter(
                LeaveRequest.status.in_(("approved", "rejected")),
                LeaveRequest.reviewed_at.isnot(None),
            )
            .order_by(LeaveRequest.reviewed_at.desc())
            .limit(5)
            .all()
        )
        approved_days = (
            db.session.query(func.coalesce(func.sum(LeaveRequest.days), 0))
            .filter(
                LeaveRequest.status == "approved",
                LeaveRequest.start_date >= date(year, 1, 1),
                LeaveRequest.start_date <= date(year, 12, 31),
            )
            .scalar()
            or 0
        )

        departments = {}
        for employee in employee_query.all():
            key = employee.department or "Unassigned"
            item = departments.setdefault(
                key, {"name": key, "headcount": 0, "on_leave": 0, "pending": 0}
            )
            item["headcount"] += 1
            item["pending"] += sum(
                1 for request in employee.requests if request.status == "pending"
            )
            item["on_leave"] += sum(
                1
                for request in employee.requests
                if request.status == "approved"
                and request.start_date <= today <= request.end_date
            )

        return jsonify(
            role="admin",
            year=year,
            stats={
                "headcount": headcount,
                "pending_requests": len(pending_requests),
                "on_leave_today": len(on_leave),
                "approved_days": approved_days,
            },
            pending_requests=[
                request.to_dict() for request in pending_requests[:6]
            ],
            on_leave=[request.to_dict() for request in on_leave],
            upcoming=[request.to_dict() for request in upcoming],
            departments=sorted(departments.values(), key=lambda item: item["name"]),
            recent_decisions=[
                request.to_dict() for request in recent_decisions
            ],
        )

    ensure_leave_types()
    balances = balances_for(user, year)
    db.session.commit()

    pending_count = LeaveRequest.query.filter_by(
        user_id=user.id, status="pending"
    ).count()
    upcoming = (
        LeaveRequest.query.filter(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status == "approved",
            LeaveRequest.end_date >= today,
        )
        .order_by(LeaveRequest.start_date.asc())
        .limit(3)
        .all()
    )
    recent = (
        LeaveRequest.query.filter_by(user_id=user.id)
        .order_by(LeaveRequest.created_at.desc())
        .limit(5)
        .all()
    )
    on_leave_today = any(
        request.start_date <= today <= request.end_date for request in upcoming
    )

    return jsonify(
        role="employee",
        year=year,
        balances=[balance.to_dict() for balance in balances],
        stats={
            "pending_requests": pending_count,
            "approved_days": approved_days_in_year(user.id, year),
            "remaining_days": sum(balance.remaining_days for balance in balances),
            "on_leave_today": on_leave_today,
        },
        upcoming=[request.to_dict() for request in upcoming],
        recent_requests=[request.to_dict() for request in recent],
    )


@bp.get("/team")
@admin_required()
def team():
    today = date.today()
    year = today.year
    ensure_leave_types()
    employees = (
        User.query.filter_by(role="employee", is_active=True)
        .order_by(User.name.asc())
        .all()
    )

    items = []
    departments = set()
    for employee in employees:
        balances = balances_for(employee, year)
        pending = LeaveRequest.query.filter_by(
            user_id=employee.id, status="pending"
        ).count()
        on_leave = (
            LeaveRequest.query.filter(
                LeaveRequest.user_id == employee.id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= today,
                LeaveRequest.end_date >= today,
            ).first()
            is not None
        )
        next_leave = (
            LeaveRequest.query.filter(
                LeaveRequest.user_id == employee.id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date > today,
            )
            .order_by(LeaveRequest.start_date.asc())
            .first()
        )
        item = employee.to_dict()
        item.update(
            {
                "balances": [balance.to_dict() for balance in balances],
                "pending_requests": pending,
                "approved_days": approved_days_in_year(employee.id, year),
                "on_leave_today": on_leave,
                "next_leave": next_leave.to_dict() if next_leave else None,
            }
        )
        items.append(item)
        departments.add(employee.department or "Unassigned")

    db.session.commit()
    return jsonify(
        items=items,
        count=len(items),
        departments=sorted(departments),
        year=year,
    )
