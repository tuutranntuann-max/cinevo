"""A signed-in user's rating and comment for a movie."""
from ..extensions import db
from ..timeutil import iso_utc, utc_now


class MovieReview(db.Model):
    __tablename__ = "movie_reviews"
    __table_args__ = (db.UniqueConstraint("movie_id", "user_id", name="uq_movie_review_user"),)

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    movie = db.relationship("Movie")
    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else "Người dùng",
            "rating": self.rating,
            "comment": self.comment,
            "created_at": iso_utc(self.created_at),
            "updated_at": iso_utc(self.updated_at),
        }
