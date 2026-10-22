"""Tạo/kiểm tra JWT, decorator phân quyền, và logic OTP giả lập."""
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from ..extensions import db
from ..models import OtpCode, User, STATUS_ACTIVE
from ..timeutil import utc_now
from .email_service import OtpDeliveryError, deliver_otp, is_email_delivery_configured


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role.name,
        "ver": user.auth_version,
        "exp": datetime.now(timezone.utc) + timedelta(hours=current_app.config["JWT_EXPIRES_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def current_user_from_request():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        data = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    user = db.session.get(User, int(data["sub"]))
    return user if (
        user
        and user.status == STATUS_ACTIVE
        and data.get("ver", 0) == user.auth_version
    ) else None


def auth_required(fn):
    """Yêu cầu đăng nhập. Người dùng hiện tại nằm ở g.current_user."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user_from_request()
        if not user:
            return jsonify({"message": "Vui lòng đăng nhập.", "code": "UNAUTHORIZED"}), 401
        g.current_user = user
        return fn(*args, **kwargs)
    return wrapper


def roles_required(*roles):
    """Yêu cầu đăng nhập VÀ có một trong các role. Kiểm tra luôn ở backend, không tin frontend."""
    def decorator(fn):
        @wraps(fn)
        @auth_required
        def wrapper(*args, **kwargs):
            if g.current_user.role.name not in roles:
                return jsonify({"message": "Bạn không có quyền truy cập.", "code": "FORBIDDEN"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def issue_otp(user: User, purpose: str = "REGISTER") -> str:
    """Create a one-time registration code and deliver it to the user's email."""
    email_configured = is_email_delivery_configured()
    code = (
        f"{secrets.randbelow(10**6):06d}"
        if email_configured
        else current_app.config["MOCK_OTP_CODE"] or f"{secrets.randbelow(10**6):06d}"
    )
    OtpCode.query.filter_by(user_id=user.id, purpose=purpose, used=False).update({"used": True})
    db.session.add(OtpCode(
        user_id=user.id,
        code=code,
        purpose=purpose,
        expires_at=utc_now() + timedelta(minutes=10),
    ))
    deliver_otp(user.email, code)
    return code


def verify_otp(user: User, code: str, purpose: str = "REGISTER") -> bool:
    otp = (OtpCode.query.filter_by(user_id=user.id, code=code, purpose=purpose, used=False)
           .order_by(OtpCode.id.desc()).first())
    if not otp or otp.expires_at < utc_now():
        return False
    otp.used = True
    return True


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}"
