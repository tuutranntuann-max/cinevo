"""Model ActivityLog (nhật ký hoạt động cho trang Admin)."""
from ..extensions import db
from ..timeutil import iso_utc, utc_now


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.String(250))
    created_at = db.Column(db.DateTime, default=utc_now)

    user = db.relationship("User")

    def to_dict(self):
        return {"id": self.id, "user": self.user.email if self.user else "-",
                "action": self.action, "detail": self.detail,
                "created_at": iso_utc(self.created_at)}


def log_activity(user_id, action, detail=""):
    db.session.add(ActivityLog(user_id=user_id, action=action, detail=detail))
