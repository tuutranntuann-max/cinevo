"""Editorial news posts about films, actors, and the cinema industry."""
from ..extensions import db
from ..timeutil import iso_utc, utc_now


class NewsArticle(db.Model):
    __tablename__ = "news_articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(500), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(60), nullable=False, default="Tin điện ảnh")
    source = db.Column(db.String(200))
    image_url = db.Column(db.String(500))
    active = db.Column(db.Boolean, nullable=False, default=True)
    published_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    created_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "category": self.category,
            "source": self.source,
            "image_url": self.image_url,
            "active": self.active,
            "published_at": iso_utc(self.published_at),
            "created_at": iso_utc(self.created_at),
            "created_by": self.created_by.full_name if self.created_by else None,
        }
