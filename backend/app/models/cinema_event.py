"""Customer-facing cinema campaigns and event posters."""
from ..extensions import db
from ..timeutil import iso_utc, utc_now


class CinemaEvent(db.Model):
    __tablename__ = "cinema_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(500), nullable=False)
    body = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    starts_at = db.Column(db.DateTime)
    ends_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    created_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "image_url": self.image_url,
            "starts_at": iso_utc(self.starts_at),
            "ends_at": iso_utc(self.ends_at),
            "active": self.active,
            "created_at": iso_utc(self.created_at),
            "created_by": self.created_by.full_name if self.created_by else None,
        }
