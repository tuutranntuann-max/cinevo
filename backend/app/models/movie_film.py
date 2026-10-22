"""Full-length movie video uploaded for on-demand viewing."""
from ..extensions import db
from ..timeutil import utc_now


class MovieFilm(db.Model):
    __tablename__ = "movie_films"

    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), primary_key=True)
    extension = db.Column(db.String(10), nullable=False)
    file_name = db.Column(db.String(100), nullable=False)
    image_extension = db.Column(db.String(10))
    image_file_name = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    movie = db.relationship("Movie", back_populates="film")
