from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import or_

from ..extensions import db
from ..models import LeaveRequest, LeaveType, User, utcnow
from ..services import (
    approve_request,
    balance_for,
    balances_for,
    ensure_leave_types,
    validate_leave_window,
)
from ..utils import (
    ApiError,
    Validator,
    current_user,
    json_body,
    pagination_args,
    pagination_meta,
)

bp = Blueprint("leaves", __name__, url_prefix="/api")

ALLOWED_STATUSES = ("pending", "approved", "rejected", "cancelled")


def get_request_or_404(request_id, user):
    leave_request = db.session.get(LeaveRequest, request_id)
    if leave_request is None:
        raise ApiError("Leave request not found.", 404)
    if leave_request.user_id != user.id and not user.is_admin:
        raise ApiError("Leave request not found.", 404)
    return leave_request


@bp.get("/leave-types")
@jwt_required()
def list_leave_types():
    leave_types = ensure_leave_types()
    db.session.commit()
    return jsonify(leave_types=[item.to_dict() for item in leave_types])


@bp.get("/leave-balances")
@jwt_required()
def list_balances():
    user = current_user()
    try:
        year = int(request.args.get("year", date.today().year))
    except ValueError:
        raise ApiError("Year must be a whole number.", 400)

    target = user
    target_id = request.args.get("user_id")
    if target_id:
        try:
            target_id = int(target_id)
        except ValueError:
            raise ApiError("user_id must be a whole number.", 400)
        if target_id != user.id and not user.is_admin:
            raise ApiError("You can only view your own leave balances.", 403)
        target = db.session.get(User, target_id)
        if target is None:
            raise ApiError("Employee not found.", 404)

    ensure_leave_types()
    balances = balances_for(target, year)
    db.session.commit()

    return jsonify(
        user=target.to_dict(),
        year=year,
        balances=[balance.to_dict() for balance in balances],
    )


@bp.get("/leave-requests")
@jwt_required()
def list_leave_requests():
    user = current_user()
    page, per_page = pagination_args()
    query = LeaveRequest.query

    if not user.is_admin:
        query = query.filter(LeaveRequest.user_id == user.id)
    else:
        user_id = request.args.get("user_id")
        if user_id:
            try:
                query = query.filter(LeaveRequest.user_id == int(user_id))
            except ValueError:
                raise ApiError("user_id must be a whole number.", 400)

        department = request.args.get("department")
        if department:
            query = query.join(User, LeaveRequest.user_id == User.id).filter(
                User.department == department
            )

    status = request.args.get("status")
    if status:
        if status not in ALLOWED_STATUSES:
            raise ApiError("Unknown leave status.", 400)
        query = query.filter(LeaveRequest.status == status)

    leave_type_id = request.args.get("leave_type_id")
    if leave_type_id:
        try:
            query = query.filter(LeaveRequest.leave_type_id == int(leave_type_id))
        except ValueError:
            raise ApiError("leave_type_id must be a whole number.", 400)

    year = request.args.get("year")
    if year:
        try:
            query = query.filter(
                db.extract("year", LeaveRequest.start_date) == int(year)
            )
        except ValueError:
            raise ApiError("Year must be a whole number.", 400)

    search = request.args.get("q", "").strip()
    if search:
        pattern = f"%{search}%"
        conditions = [LeaveRequest.reason.ilike(pattern)]
        if user.is_admin:
            query = query.join(User, LeaveRequest.user_id == User.id)
            conditions.extend(
                [User.name.ilike(pattern), User.email.ilike(pattern)]
            )
        query = query.filter(or_(*conditions))

    pagination = query.order_by(
        LeaveRequest.created_at.desc(), LeaveRequest.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        items=[item.to_dict() for item in pagination.items],
        **pagination_meta(pagination),
    )


@bp.post("/leave-requests")
@jwt_required()
def create_leave_request():
    user = current_user()
    data = json_body()
    validator = Validator(data)

    leave_type_id = validator.integer("leave_type_id", required=True, minimum=1)
    start = validator.date("start_date", required=True)
    end = validator.date("end_date", required=True)
    reason = validator.text("reason", required=True, min_length=10, max_length=500)
    validator.raise_if_errors()

    leave_type = db.session.get(LeaveType, leave_type_id)
    if leave_type is None:
        raise ApiError("Leave type not found.", 404)

    days, _balance, errors = validate_leave_window(
        user, leave_type, start, end, start.year
    )
    if errors:
        raise ApiError("Please check the leave request.", 422, errors)

    leave_request = LeaveRequest(
        user_id=user.id,
        leave_type_id=leave_type.id,
        start_date=start,
        end_date=end,
        days=days,
        reason=reason,
        status="pending",
    )
    db.session.add(leave_request)
    db.session.commit()

    return jsonify(leave_request.to_dict()), 201


@bp.get("/leave-requests/<int:request_id>")
@jwt_required()
def get_leave_request(request_id):
    leave_request = get_request_or_404(request_id, current_user())
    return jsonify(leave_request.to_dict())


@bp.post("/leave-requests/<int:request_id>/cancel")
@jwt_required()
def cancel_leave_request(request_id):
    user = current_user()
    leave_request = db.session.get(LeaveRequest, request_id)
    if leave_request is None:
        raise ApiError("Leave request not found.", 404)
    if leave_request.user_id != user.id:
        raise ApiError("Only the employee who applied can cancel this request.", 403)
    if leave_request.status not in ("pending", "approved"):
        raise ApiError("This leave request can no longer be cancelled.", 409)
    if leave_request.start_date <= date.today():
        raise ApiError(
            "Leave that has already started cannot be cancelled.", 409
        )

    if leave_request.status == "approved":
        balance = balance_for(
            leave_request.user,
            leave_request.leave_type,
            leave_request.start_date.year,
        )
        balance.used_days = max(0, balance.used_days - leave_request.days)

    leave_request.status = "cancelled"
    db.session.commit()
    return jsonify(leave_request.to_dict())


@bp.post("/leave-requests/<int:request_id>/review")
@jwt_required()
def review_leave_request(request_id):
    reviewer = current_user()
    if not reviewer.is_admin:
        raise ApiError("Admin access is required.", 403)

    data = json_body()
    validator = Validator(data)
    decision = validator.text("decision", required=True, max_length=20)
    note = validator.text("note", max_length=500)

    if decision not in ("approve", "reject"):
        validator.errors["decision"] = "Decision must be approve or reject."
    if decision == "reject" and not note:
        validator.errors["note"] = "Add a short note explaining the rejection."
    validator.raise_if_errors()

    leave_request = db.session.get(LeaveRequest, request_id)
    if leave_request is None:
        raise ApiError("Leave request not found.", 404)
    if leave_request.status != "pending":
        raise ApiError("Only pending requests can be reviewed.", 409)
    if leave_request.user_id == reviewer.id:
        raise ApiError("You cannot review your own leave request.", 403)

    if decision == "approve":
        errors = approve_request(leave_request, reviewer, note)
        if errors:
            raise ApiError("This request exceeds the available balance.", 422, errors)
    else:
        leave_request.status = "rejected"
        leave_request.reviewed_by_id = reviewer.id
        leave_request.review_note = note
        leave_request.reviewed_at = utcnow()

    db.session.commit()
    return jsonify(leave_request.to_dict())
