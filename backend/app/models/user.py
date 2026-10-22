"""Model User + OtpCode."""
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..timeutil import iso_utc, utc_now

STATUS_PENDING = "PENDING"   # đã đăng ký, chưa xác thực OTP
STATUS_ACTIVE = "ACTIVE"
STATUS_LOCKED = "LOCKED"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(300))
    password_hash = db.Column(db.String(255), nullable=False)
    auth_version = db.Column(db.Integer, nullable=False, default=0)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    role = db.relationship("Role")

    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def to_dict(self):
        return {
            "id": self.id,
            "customer_code": f"CV{self.id:06d}",
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "avatar_url": self.avatar_url,
            "role": self.role.name if self.role else None,
            "status": self.status,
            "created_at": iso_utc(self.created_at),
        }


class OtpCode(db.Model):
    """One-time email code, separated by registration and login purpose."""
    __tablename__ = "otp_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(20), nullable=False, default="REGISTER")
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
