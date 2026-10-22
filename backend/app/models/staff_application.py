"""Staff applications and one-time administrator-issued account invitations."""
from ..extensions import db
from ..services.staff_privacy import decrypt_staff_data
from ..timeutil import iso_utc, utc_now


class StaffApplication(db.Model):
    __tablename__ = "staff_applications"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    citizen_id_ciphertext = db.Column(db.String(255), nullable=False)
    citizen_id_digest = db.Column(db.String(64), nullable=False, index=True)
    address_ciphertext = db.Column(db.String(600), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    occupation = db.Column(db.String(100), nullable=False)
    privacy_accepted = db.Column(db.Boolean, nullable=False, default=False)
    requested_role = db.Column(db.String(20), nullable=False)
    approved_role = db.Column(db.String(20))
    status = db.Column(db.String(20), nullable=False, default="PENDING", index=True)
    invite_hash = db.Column(db.String(64), unique=True)
    invite_expires_at = db.Column(db.DateTime)
    invited_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User")

    @property
    def citizen_id(self):
        return decrypt_staff_data(self.citizen_id_ciphertext)

    @property
    def address(self):
        return decrypt_staff_data(self.address_ciphertext)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "citizen_id": self.citizen_id,
            "address": self.address,
            "gender": self.gender,
            "occupation": self.occupation,
            "privacy_accepted": self.privacy_accepted,
            "requested_role": self.requested_role,
            "approved_role": self.approved_role,
            "status": self.status,
            "user_id": self.user_id,
            "invite_expires_at": iso_utc(self.invite_expires_at),
            "created_at": iso_utc(self.created_at),
        }
