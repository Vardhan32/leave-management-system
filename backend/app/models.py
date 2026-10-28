from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

ROLES = ("employee", "admin")
LEAVE_STATUSES = ("pending", "approved", "rejected", "cancelled")

LEAVE_TYPE_DEFAULTS = (
    {
        "code": "CASUAL",
        "name": "Casual Leave",
        "default_days": 12,
        "description": "Short personal errands and planned time away.",
        "sort_order": 1,
    },
    {
        "code": "SICK",
        "name": "Sick Leave",
        "default_days": 10,
        "description": "Illness, recovery, and medical appointments.",
        "sort_order": 2,
    },
    {
        "code": "EARNED",
        "name": "Earned Leave",
        "default_days": 15,
        "description": "Planned holidays and longer breaks.",
        "sort_order": 3,
    },
)


def utcnow():
    """Naive UTC timestamp, stored the same way on SQLite and MySQL."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    department = db.Column(db.String(80))
    job_title = db.Column(db.String(120))
    joined_on = db.Column(db.Date)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    balances = db.relationship(
        "LeaveBalance", back_populates="user", cascade="all, delete-orphan"
    )
    requests = db.relationship(
        "LeaveRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="LeaveRequest.user_id",
    )

    @property
    def is_admin(self):
        return self.role == "admin"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "job_title": self.job_title,
            "joined_on": self.joined_on.isoformat() if self.joined_on else None,
            "created_at": self.created_at.isoformat(),
        }


class LeaveType(db.Model):
    __tablename__ = "leave_types"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(80), nullable=False)
    default_days = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "default_days": self.default_days,
            "description": self.description,
        }


class LeaveBalance(db.Model):
    __tablename__ = "leave_balances"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "leave_type_id", "year", name="uq_balance_user_type_year"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id = db.Column(
        db.Integer, db.ForeignKey("leave_types.id"), nullable=False, index=True
    )
    year = db.Column(db.Integer, nullable=False, index=True)
    allocated_days = db.Column(db.Integer, nullable=False, default=0)
    used_days = db.Column(db.Integer, nullable=False, default=0)

    user = db.relationship("User", back_populates="balances")
    leave_type = db.relationship("LeaveType")

    @property
    def remaining_days(self):
        return max(self.allocated_days - self.used_days, 0)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "year": self.year,
            "leave_type": self.leave_type.to_dict(),
            "allocated_days": self.allocated_days,
            "used_days": self.used_days,
            "remaining_days": self.remaining_days,
        }


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    __table_args__ = (
        db.Index("ix_leave_requests_user_status", "user_id", "status"),
        db.Index("ix_leave_requests_dates", "start_date", "end_date"),
        db.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="ck_leave_requests_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id = db.Column(
        db.Integer, db.ForeignKey("leave_types.id"), nullable=False, index=True
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    reviewed_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at = db.Column(db.DateTime)
    review_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    user = db.relationship("User", back_populates="requests", foreign_keys=[user_id])
    leave_type = db.relationship("LeaveType")
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "employee": self.user.to_dict(),
            "leave_type": self.leave_type.to_dict(),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days": self.days,
            "reason": self.reason,
            "status": self.status,
            "reviewed_by": (
                {"id": self.reviewed_by.id, "name": self.reviewed_by.name}
                if self.reviewed_by
                else None
            ),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_note": self.review_note,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
