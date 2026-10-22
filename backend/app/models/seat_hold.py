from datetime import timedelta

from ..extensions import db
from ..timeutil import iso_utc, utc_now


SEAT_HOLD_DURATION = timedelta(minutes=10)


class SeatHold(db.Model):
    __tablename__ = "seat_holds"
    __table_args__ = (
        db.UniqueConstraint("showtime_id", "seat_id", name="uq_hold_showtime_seat"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    showtime_id = db.Column(db.Integer, db.ForeignKey("showtimes.id"), nullable=False, index=True)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "showtime_id": self.showtime_id,
            "seat_id": self.seat_id,
            "expires_at": iso_utc(self.expires_at),
        }


class UserTrust(db.Model):
    __tablename__ = "user_trust"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    score = db.Column(db.Integer, nullable=False, default=100)
    expired_holds = db.Column(db.Integer, nullable=False, default=0)
    penalties = db.Column(db.Integer, nullable=False, default=0)
    blocked_until = db.Column(db.DateTime)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "score": self.score,
            "expired_holds": self.expired_holds,
            "penalties": self.penalties,
            "blocked_until": iso_utc(self.blocked_until),
        }
