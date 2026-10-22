"""Staff applications, administrator approval, and single-use account invitations."""
import hashlib
import re
import secrets
from datetime import timedelta

from flask import Blueprint, g, jsonify

from ..extensions import db
from ..models import (
    ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER, STATUS_ACTIVE,
    Role, StaffApplication, StaffPasswordResetRequest, User,
)
from ..services.auth_service import create_token, roles_required
from ..services.rate_limit import email_key, rate_limit
from ..services.staff_privacy import encrypt_staff_data, staff_data_digest
from ..services.validation import ApiError, EMAIL_RE, PHONE_RE, clean_str, json_body
from ..timeutil import utc_now

bp = Blueprint("staff_accounts", __name__, url_prefix="/api/staff-accounts")
admin_only = roles_required(ROLE_ADMIN)
INVITE_LIFETIME = timedelta(days=7)
GENDERS = {"Nam", "Nữ", "Khác"}
ROLES = {ROLE_EMPLOYEE, ROLE_MANAGER}
RESET_CODE_LIFETIME = timedelta(minutes=30)
STAFF_ROLES = (ROLE_EMPLOYEE, ROLE_MANAGER)


def _invite_digest(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@bp.post("/applications")
@rate_limit("staff-application", 5, 3600)
def submit_application():
    data = json_body()
    full_name = clean_str(data.get("full_name"), "họ và tên", min_len=2, max_len=120, required=True)
    email = clean_str(data.get("email"), "email", max_len=160, required=True).lower()
    phone = clean_str(data.get("phone"), "số điện thoại", max_len=15, required=True)
    citizen_id = clean_str(data.get("citizen_id"), "CCCD", min_len=12, max_len=12, required=True)
    address = clean_str(data.get("address"), "địa chỉ", min_len=5, max_len=300, required=True)
    gender = clean_str(data.get("gender"), "giới tính", max_len=20, required=True)
    occupation = clean_str(data.get("occupation"), "nghề nghiệp/tình trạng học tập", min_len=2, max_len=100, required=True)
    requested_role = clean_str(data.get("requested_role"), "vị trí", max_len=20, required=True).upper()
    if data.get("accept_privacy") is not True:
        raise ApiError("Bạn cần đồng ý cung cấp thông tin để Admin xét duyệt hồ sơ.")

    if not EMAIL_RE.fullmatch(email):
        raise ApiError("Email không hợp lệ.")
    if not PHONE_RE.fullmatch(phone):
        raise ApiError("Số điện thoại không hợp lệ.")
    if not citizen_id.isdigit():
        raise ApiError("CCCD phải gồm đúng 12 chữ số.")
    if gender not in GENDERS:
        raise ApiError("Vui lòng chọn giới tính hợp lệ.")
    if requested_role not in ROLES:
        raise ApiError("Vị trí đăng ký không hợp lệ.")
    if User.query.filter_by(email=email).first():
        raise ApiError("Email này đã gắn với một tài khoản.", 409, "EMAIL_EXISTS")

    application = StaffApplication.query.filter_by(email=email).first()
    if application and application.status != "REJECTED":
        raise ApiError("Hồ sơ với email này đã được gửi hoặc đã được duyệt.", 409, "APPLICATION_EXISTS")
    citizen_id_digest = staff_data_digest(citizen_id)
    duplicate_id = StaffApplication.query.filter(
        StaffApplication.citizen_id_digest == citizen_id_digest,
        StaffApplication.email != email,
        StaffApplication.status != "REJECTED",
    ).first()
    if duplicate_id:
        raise ApiError("CCCD này đã được sử dụng trong một hồ sơ khác.", 409, "CITIZEN_ID_EXISTS")

    if application is None:
        application = StaffApplication(email=email)
        db.session.add(application)
    application.full_name = full_name
    application.phone = phone
    application.citizen_id_ciphertext = encrypt_staff_data(citizen_id)
    application.citizen_id_digest = citizen_id_digest
    application.address_ciphertext = encrypt_staff_data(address)
    application.gender = gender
    application.occupation = occupation
    application.privacy_accepted = True
    application.requested_role = requested_role
    application.approved_role = None
    application.status = "PENDING"
    application.invite_hash = None
    application.invite_expires_at = None
    application.invited_at = None
    application.user_id = None
    db.session.commit()
    return jsonify({
        "message": "Đã gửi hồ sơ. Vui lòng chờ Admin duyệt và cấp mã mời.",
        "application_id": application.id,
    }), 201


@bp.get("/applications")
@admin_only
def list_applications():
    applications = StaffApplication.query.order_by(
        StaffApplication.created_at.desc()
    ).limit(300).all()
    return jsonify({
        "applications": [application.to_dict() for application in applications],
        "pending_count": sum(application.status == "PENDING" for application in applications),
    })


@bp.get("/applications/count")
@admin_only
def count_applications():
    return jsonify({
        "pending_count": StaffApplication.query.filter_by(status="PENDING").count(),
    })


@bp.post("/applications/<int:application_id>/approve")
@admin_only
def approve_application(application_id):
    application = db.session.get(StaffApplication, application_id)
    if not application:
        raise ApiError("Không tìm thấy hồ sơ.", 404)
    if application.status != "PENDING":
        raise ApiError("Hồ sơ này không còn ở trạng thái chờ duyệt.", 409)
    data = json_body()
    role_name = clean_str(
        data.get("role", application.requested_role),
        "vị trí được duyệt",
        max_len=20,
        required=True,
    ).upper()
    if role_name not in ROLES:
        raise ApiError("Vị trí được duyệt không hợp lệ.")
    if not Role.query.filter_by(name=role_name).first():
        raise ApiError("Vai trò chưa được khởi tạo trên hệ thống.", 500)

    code = secrets.token_hex(16).upper()
    now = utc_now()
    application.approved_role = role_name
    application.status = "INVITED"
    application.invite_hash = _invite_digest(code)
    application.invite_expires_at = now + INVITE_LIFETIME
    application.invited_at = now
    db.session.commit()
    return jsonify({
        "application": application.to_dict(),
        "invite_code": code,
        "message": "Mã chỉ hiển thị lần này. Hãy gửi trực tiếp cho người đăng ký.",
    })


@bp.post("/applications/<int:application_id>/reject")
@admin_only
def reject_application(application_id):
    application = db.session.get(StaffApplication, application_id)
    if not application:
        raise ApiError("Không tìm thấy hồ sơ.", 404)
    if application.status != "PENDING":
        raise ApiError("Chỉ có thể từ chối hồ sơ đang chờ duyệt.", 409)
    application.status = "REJECTED"
    db.session.commit()
    return jsonify({"application": application.to_dict()})


@bp.post("/applications/<int:application_id>/invite")
@admin_only
def reissue_invitation(application_id):
    application = db.session.get(StaffApplication, application_id)
    if not application:
        raise ApiError("Không tìm thấy hồ sơ.", 404)
    if application.status != "INVITED" or application.user_id is not None:
        raise ApiError("Chỉ có thể cấp lại mã cho hồ sơ đã duyệt nhưng chưa kích hoạt.", 409)
    code = secrets.token_hex(16).upper()
    application.invite_hash = _invite_digest(code)
    application.invite_expires_at = utc_now() + INVITE_LIFETIME
    application.invited_at = utc_now()
    db.session.commit()
    return jsonify({
        "application": application.to_dict(),
        "invite_code": code,
        "message": "Mã mới chỉ hiển thị lần này; mã cũ đã mất hiệu lực.",
    })


@bp.post("/complete")
@rate_limit("staff-invite-complete", 5, 900)
def complete_invitation():
    data = json_body()
    email = clean_str(data.get("email"), "email", max_len=160, required=True).lower()
    code = clean_str(data.get("invite_code"), "mã mời", min_len=32, max_len=32, required=True).upper()
    password = data.get("password")
    if not EMAIL_RE.fullmatch(email):
        raise ApiError("Email không hợp lệ.")
    if not isinstance(password, str) or not (8 <= len(password) <= 128):
        raise ApiError("Mật khẩu cần từ 8 đến 128 ký tự.")
    if password != data.get("confirm_password"):
        raise ApiError("Mật khẩu nhập lại không khớp.")

    application = StaffApplication.query.filter_by(
        email=email,
        invite_hash=_invite_digest(code),
        status="INVITED",
    ).first()
    if not application or not application.invite_expires_at or application.invite_expires_at <= utc_now():
        raise ApiError("Email hoặc mã mời không hợp lệ, đã hết hạn hoặc đã được sử dụng.", 400, "INVITE_INVALID")
    if User.query.filter_by(email=email).first():
        raise ApiError("Email này đã được sử dụng.", 409, "EMAIL_EXISTS")

    role = Role.query.filter_by(name=application.approved_role).first()
    if not role:
        raise ApiError("Vai trò của hồ sơ không còn khả dụng.", 500)
    user = User(
        full_name=application.full_name,
        email=application.email,
        phone=application.phone,
        role=role,
        status=STATUS_ACTIVE,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    application.user_id = user.id
    application.status = "ACTIVE"
    application.invite_hash = None
    application.invite_expires_at = None
    db.session.commit()
    return jsonify({
        "token": create_token(user),
        "user": user.to_dict(),
        "message": "Tài khoản đã được kích hoạt.",
    }), 201


@bp.post("/password-resets")
@rate_limit("staff-reset-request-ip", 10, 3600)
@rate_limit("staff-reset-request-email", 3, 3600, key=email_key)
def request_password_reset():
    data = json_body()
    email = clean_str(data.get("email"), "email", max_len=160, required=True).lower()
    if not EMAIL_RE.fullmatch(email):
        raise ApiError("Email không hợp lệ.")

    user = User.query.filter_by(email=email, status=STATUS_ACTIVE).first()
    if user and user.role and user.role.name in STAFF_ROLES:
        StaffPasswordResetRequest.query.filter(
            StaffPasswordResetRequest.user_id == user.id,
            StaffPasswordResetRequest.status.in_(("PENDING", "ISSUED")),
        ).update(
            {"status": "SUPERSEDED", "code_hash": None},
            synchronize_session=False,
        )
        db.session.add(StaffPasswordResetRequest(user_id=user.id))
        db.session.commit()

    return jsonify({
        "message": "Nếu email thuộc tài khoản nhân viên/quản lý hợp lệ, yêu cầu sẽ được gửi tới Admin xem xét.",
    }), 202


@bp.get("/password-resets")
@admin_only
def list_password_reset_requests():
    requests = (
        StaffPasswordResetRequest.query
        .filter(StaffPasswordResetRequest.status.in_(("PENDING", "ISSUED")))
        .order_by(StaffPasswordResetRequest.requested_at.desc())
        .limit(300)
        .all()
    )
    return jsonify({
        "requests": [reset.to_dict() for reset in requests],
        "pending_count": sum(reset.status == "PENDING" for reset in requests),
    })


@bp.get("/password-resets/count")
@admin_only
def count_password_reset_requests():
    return jsonify({
        "pending_count": StaffPasswordResetRequest.query.filter_by(status="PENDING").count(),
    })


@bp.post("/password-resets/<int:reset_id>/issue")
@admin_only
def issue_password_reset_code(reset_id):
    reset = db.session.get(StaffPasswordResetRequest, reset_id)
    if not reset or reset.status not in {"PENDING", "ISSUED"}:
        raise ApiError("Không tìm thấy yêu cầu đặt lại mật khẩu đang chờ xử lý.", 404)
    user = reset.user
    if not user or user.status != STATUS_ACTIVE or not user.role or user.role.name not in STAFF_ROLES:
        reset.status = "SUPERSEDED"
        reset.code_hash = None
        db.session.commit()
        raise ApiError("Tài khoản không còn đủ điều kiện đặt lại mật khẩu.", 409)

    code = f"{secrets.randbelow(100_000_000):08d}"
    reset.status = "ISSUED"
    reset.code_hash = _invite_digest(code)
    reset.expires_at = utc_now() + RESET_CODE_LIFETIME
    reset.issued_at = utc_now()
    reset.issued_by_id = g.current_user.id
    db.session.commit()
    return jsonify({
        "request": reset.to_dict(),
        "reset_code": code,
        "message": "Mã chỉ hiển thị lần này. Hãy gửi riêng cho nhân viên; mã hết hạn sau 30 phút.",
    })


@bp.post("/password-resets/complete")
@rate_limit("staff-reset-complete-ip", 20, 900)
@rate_limit("staff-reset-complete-email", 5, 900, key=email_key)
def complete_staff_password_reset():
    data = json_body()
    email = clean_str(data.get("email"), "email", max_len=160, required=True).lower()
    code = clean_str(data.get("reset_code"), "mã đặt lại", min_len=8, max_len=8, required=True)
    password = data.get("password")
    if not EMAIL_RE.fullmatch(email):
        raise ApiError("Email không hợp lệ.")
    if not code.isdigit():
        raise ApiError("Mã đặt lại không hợp lệ.")
    if not isinstance(password, str) or not (8 <= len(password) <= 128):
        raise ApiError("Mật khẩu cần từ 8 đến 128 ký tự.")
    if password != data.get("confirm_password"):
        raise ApiError("Mật khẩu nhập lại không khớp.")

    reset = (
        StaffPasswordResetRequest.query
        .join(User, StaffPasswordResetRequest.user_id == User.id)
        .filter(
            User.email == email,
            User.status == STATUS_ACTIVE,
            StaffPasswordResetRequest.status == "ISSUED",
            StaffPasswordResetRequest.code_hash == _invite_digest(code),
            StaffPasswordResetRequest.expires_at > utc_now(),
        )
        .order_by(StaffPasswordResetRequest.issued_at.desc())
        .first()
    )
    if not reset or not reset.user.role or reset.user.role.name not in STAFF_ROLES:
        raise ApiError("Email hoặc mã không hợp lệ, đã hết hạn hoặc đã được sử dụng.", 400, "RESET_CODE_INVALID")

    consumed = StaffPasswordResetRequest.query.filter_by(
        id=reset.id,
        status="ISSUED",
        code_hash=_invite_digest(code),
    ).filter(
        StaffPasswordResetRequest.expires_at > utc_now(),
    ).update(
        {"status": "USED", "code_hash": None},
        synchronize_session=False,
    )
    if consumed != 1:
        db.session.rollback()
        raise ApiError("Email hoặc mã không hợp lệ, đã hết hạn hoặc đã được sử dụng.", 400, "RESET_CODE_INVALID")

    reset.user.set_password(password)
    reset.user.auth_version += 1
    StaffPasswordResetRequest.query.filter(
        StaffPasswordResetRequest.user_id == reset.user_id,
        StaffPasswordResetRequest.id != reset.id,
        StaffPasswordResetRequest.status.in_(("PENDING", "ISSUED")),
    ).update(
        {"status": "SUPERSEDED", "code_hash": None},
        synchronize_session=False,
    )
    db.session.commit()
    return jsonify({"message": "Đã đổi mật khẩu. Đăng nhập bằng mật khẩu mới."})
