"""Đăng ký / OTP / đăng nhập. Role khi tự đăng ký luôn là USER."""
import re
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, g, jsonify
from flask import request, send_from_directory
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import ROLE_USER, Role, STATUS_ACTIVE, STATUS_PENDING, User, log_activity
from ..services.auth_service import (auth_required, create_token, issue_otp, mask_email, verify_otp)
from ..services.email_service import OtpDeliveryError, is_email_delivery_configured
from ..services.rate_limit import email_key, ip_and_email_key, rate_limit
from ..services.validation import (EMAIL_RE, PHONE_RE, ApiError, clean_str, json_body)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
AVATAR_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def _valid_avatar_signature(image, extension):
    if extension in {"jpg", "jpeg"}:
        return image.startswith(b"\xff\xd8\xff")
    if extension == "png":
        return image.startswith(b"\x89PNG\r\n\x1a\n")
    return len(image) >= 12 and image[:4] == b"RIFF" and image[8:12] == b"WEBP"


def _remove_avatar_file(user_id, avatar_url):
    if not re.fullmatch(
        rf"/api/auth/avatars/avatar_{user_id}_[0-9a-f]{{32}}\.(?:jpg|jpeg|png|webp)",
        avatar_url or "",
    ):
        return
    file_name = avatar_url.rsplit("/", 1)[-1]
    try:
        (Path(current_app.config["AVATAR_UPLOAD_DIR"]) / file_name).unlink(missing_ok=True)
    except OSError:
        current_app.logger.exception("Không thể xóa ảnh đại diện cũ của người dùng %s.", user_id)


def _otp_hint_body(code):
    return {"otp_hint": code} if (
        current_app.config["OTP_DEBUG_HINT"] and not is_email_delivery_configured()
    ) else {}


def _issue_otp_or_error(user, purpose="REGISTER"):
    try:
        return issue_otp(user, purpose)
    except OtpDeliveryError as error:
        db.session.rollback()
        raise ApiError(str(error), 503, "OTP_DELIVERY_FAILED") from error


@bp.post("/register")
@rate_limit("register", 10, 3600)
def register():
    data = json_body()
    # LƯU Ý BẢO MẬT: cố tình KHÔNG đọc role/role_id/status từ client. Client không thể tự chọn MANAGER/ADMIN.
    full_name = clean_str(data.get("full_name"), "họ và tên", min_len=2, max_len=120, required=True)
    email = clean_str(data.get("email"), "email", max_len=160, required=True).lower()
    phone = clean_str(data.get("phone"), "số điện thoại", max_len=15, required=True)
    password = data.get("password")
    if not isinstance(password, str) or not (6 <= len(password) <= 128):
        raise ApiError("Mật khẩu cần từ 6 đến 128 ký tự.")
    if not EMAIL_RE.match(email):
        raise ApiError("Email không hợp lệ.")
    if not PHONE_RE.match(phone):
        raise ApiError("Số điện thoại không hợp lệ.")
    if password != data.get("confirm_password"):
        raise ApiError("Mật khẩu nhập lại không khớp.")
    if data.get("accept_terms") is not True:
        raise ApiError("Bạn cần đồng ý với điều khoản sử dụng.")

    user = User.query.filter_by(email=email).first()
    if user and user.status != STATUS_PENDING:
        raise ApiError("Email này đã được sử dụng.", 409, "EMAIL_EXISTS")
    if not user:   # tài khoản PENDING cũ được phép đăng ký lại (cập nhật thông tin)
        user = User(email=email, role=Role.query.filter_by(name=ROLE_USER).one())
        db.session.add(user)
    user.full_name, user.phone, user.status = full_name, phone, STATUS_PENDING
    user.set_password(password)
    db.session.flush()
    code = _issue_otp_or_error(user)
    db.session.commit()

    return jsonify({"message": "Đã gửi mã xác thực.", "email": email,
                    "masked_email": mask_email(email), **_otp_hint_body(code)}), 201


@bp.post("/verify-otp")
@rate_limit("otp-email", 5, 600, key=email_key)     # tối đa 5 lần thử / 10 phút / email
@rate_limit("otp-ip", 30, 600)
def verify():
    data = json_body()
    user = User.query.filter_by(email=clean_str(data.get("email"), "email", max_len=160).lower()).first()
    code = data.get("code")
    if not user or not isinstance(code, str) or not verify_otp(user, code, "REGISTER"):
        raise ApiError("Mã xác thực không đúng hoặc đã hết hạn.", 400, "OTP_INVALID")
    user.status = STATUS_ACTIVE
    log_activity(user.id, "REGISTER_VERIFIED", user.email)
    db.session.commit()
    return jsonify({"token": create_token(user), "user": user.to_dict()})


@bp.post("/resend-otp")
@rate_limit("otp-resend", 3, 600, key=email_key)
def resend():
    data = json_body()
    user = User.query.filter_by(email=clean_str(data.get("email"), "email", max_len=160).lower(),
                                status=STATUS_PENDING).first()
    if user:
        _issue_otp_or_error(user)
        db.session.commit()
    return jsonify({"message": "Nếu email hợp lệ, mã mới đã được gửi."})


@bp.post("/login")
@rate_limit("login", 10, 300, key=ip_and_email_key)   # tối đa 10 lần / 5 phút cho mỗi cặp IP + email
@rate_limit("login-ip", 60, 300)
def login():
    data = json_body()
    email = clean_str(data.get("email"), "email", max_len=160).lower()
    password = data.get("password")
    user = User.query.filter_by(email=email).first()
    if not user or not isinstance(password, str) or not user.check_password(password):
        raise ApiError("Email hoặc mật khẩu không đúng.", 401, "BAD_CREDENTIALS")
    if user.status == STATUS_PENDING:
        code = _issue_otp_or_error(user)
        db.session.commit()
        return jsonify({"message": "Tài khoản chưa xác thực. Vui lòng nhập mã OTP.", "code": "NOT_VERIFIED",
                        **_otp_hint_body(code)}), 403
    if user.status != STATUS_ACTIVE:
        raise ApiError("Tài khoản đã bị khóa.", 403, "LOCKED")
    log_activity(user.id, "LOGIN", user.email)
    db.session.commit()
    return jsonify({"token": create_token(user), "user": user.to_dict()})

@bp.get("/me")
@auth_required
def me():
    return jsonify({"user": g.current_user.to_dict()})


@bp.put("/me")
@auth_required
def update_me():
    data = json_body()
    user = g.current_user
    if "full_name" in data:
        user.full_name = clean_str(data["full_name"], "họ và tên", min_len=2, max_len=120, required=True)
    if "phone" in data:
        phone = clean_str(data["phone"], "số điện thoại", max_len=15, required=True)
        if not PHONE_RE.match(phone):
            raise ApiError("Số điện thoại không hợp lệ.")
        user.phone = phone
    db.session.commit()
    return jsonify({"user": user.to_dict()})


@bp.post("/me/avatar")
@auth_required
def upload_avatar():
    upload = request.files.get("image")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn ảnh đại diện.")
    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension == "jfif":
        extension = "jpg"
    if extension not in AVATAR_TYPES:
        raise ApiError("Ảnh đại diện chỉ hỗ trợ JPG, PNG hoặc WEBP.")
    image = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(image) > 5 * 1024 * 1024:
        raise ApiError("Ảnh đại diện không được vượt quá 5 MB.")
    if not _valid_avatar_signature(image, extension):
        raise ApiError("Nội dung tệp không phải ảnh hợp lệ.")

    directory = Path(current_app.config["AVATAR_UPLOAD_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    file_name = f"avatar_{g.current_user.id}_{uuid4().hex}.{extension}"
    target = directory / file_name
    temporary = directory / f".{file_name}.tmp"
    try:
        temporary.write_bytes(image)
        temporary.replace(target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu ảnh đại diện của người dùng %s.", g.current_user.id)
        raise ApiError("Không thể lưu ảnh đại diện. Vui lòng thử lại.", 500) from exc

    user = g.current_user
    old_avatar_url = user.avatar_url
    user.avatar_url = f"/api/auth/avatars/{file_name}"
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        target.unlink(missing_ok=True)
        raise
    _remove_avatar_file(user.id, old_avatar_url)
    return jsonify({"user": user.to_dict()})


@bp.delete("/me/avatar")
@auth_required
def delete_avatar():
    user = g.current_user
    old_avatar_url = user.avatar_url
    user.avatar_url = None
    db.session.commit()
    _remove_avatar_file(user.id, old_avatar_url)
    return jsonify({"user": user.to_dict()})


@bp.get("/avatars/<path:file_name>")
def serve_avatar(file_name):
    safe_name = secure_filename(file_name)
    if safe_name != file_name:
        raise ApiError("Không tìm thấy ảnh đại diện.", 404)
    match = re.fullmatch(r"avatar_\d+_[0-9a-f]{32}\.(jpg|jpeg|png|webp)", safe_name)
    if not match:
        raise ApiError("Không tìm thấy ảnh đại diện.", 404)
    return send_from_directory(
        current_app.config["AVATAR_UPLOAD_DIR"],
        safe_name,
        mimetype=AVATAR_TYPES[match.group(1)],
        conditional=True,
    )
