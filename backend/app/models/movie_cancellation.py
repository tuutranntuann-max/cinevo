"""Cancellation state for movies; separate table avoids changing existing movie rows."""
from ..extensions import db
from ..timeutil import utc_now


class MovieCancellation(db.Model):
    __tablename__ = "movie_cancellations"

    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), primary_key=True)
    previous_status = db.Column(db.String(20), nullable=False)
    cancelled_at = db.Column(db.DateTime, nullable=False, default=utc_now)

