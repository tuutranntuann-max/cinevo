"""Admin-issued, one-time password reset codes for employee and manager accounts."""
from ..extensions import db
from ..timeutil import iso_utc, utc_now


class StaffPasswordResetRequest(db.Model):
    __tablename__ = "staff_password_reset_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="PENDING", index=True)
    code_hash = db.Column(db.String(64), unique=True)
    expires_at = db.Column(db.DateTime)
    requested_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    issued_at = db.Column(db.DateTime)
    issued_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User", foreign_keys=[user_id])
    issued_by = db.relationship("User", foreign_keys=[issued_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.user.full_name if self.user else "",
            "email": self.user.email if self.user else "",
            "role": self.user.role.name if self.user and self.user.role else "",
            "status": self.status,
            "expires_at": iso_utc(self.expires_at),
            "requested_at": iso_utc(self.requested_at),
        }
