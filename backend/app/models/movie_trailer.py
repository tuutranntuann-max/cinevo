"""Uploaded background trailer used by the homepage movie hero."""
from ..extensions import db
from ..timeutil import utc_now


class MovieTrailer(db.Model):
    __tablename__ = "movie_trailers"

    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), primary_key=True)
    extension = db.Column(db.String(10), nullable=False)
    file_name = db.Column(db.String(100), nullable=False)
    audio_file_name = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    movie = db.relationship("Movie", back_populates="trailer")
