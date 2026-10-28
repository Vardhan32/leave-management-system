from datetime import date

from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token, jwt_required

from ..extensions import db
from ..models import User
from ..services import balances_for, ensure_leave_types
from ..utils import EMAIL_RE, ApiError, Validator, current_user, json_body

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    data = json_body()
    validator = Validator(data)

    name = validator.text("name", required=True, max_length=100)
    email = validator.text("email", required=True, max_length=255)
    password = data.get("password")
    department = validator.text("department", max_length=80)
    job_title = validator.text("job_title", max_length=120)

    if email and not EMAIL_RE.match(email):
        validator.errors["email"] = "Enter a valid email address."
    if not isinstance(password, str) or len(password) < 8:
        validator.errors["password"] = "Password must be at least 8 characters."
    elif len(password) > 128:
        validator.errors["password"] = "Password must be under 128 characters."

    validator.raise_if_errors()

    email = email.lower()
    if User.query.filter_by(email=email).first():
        raise ApiError("An account with this email already exists.", 409)

    user = User(
        name=name,
        email=email,
        role="employee",
        department=department,
        job_title=job_title,
        joined_on=date.today(),
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    ensure_leave_types()
    balances_for(user, date.today().year)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify(user=user.to_dict(), access_token=token), 201


@bp.post("/login")
def login():
    data = json_body()
    validator = Validator(data)
    email = validator.text("email", required=True, max_length=255)
    password = data.get("password")

    if not password:
        validator.errors["password"] = "Password is required."
    validator.raise_if_errors()

    user = User.query.filter_by(email=email.lower(), is_active=True).first()
    if user is None or not user.check_password(str(password)):
        raise ApiError("Incorrect email or password.", 401)

    token = create_access_token(identity=str(user.id))
    return jsonify(user=user.to_dict(), access_token=token)


@bp.get("/me")
@jwt_required()
def me():
    return jsonify(user=current_user().to_dict())
