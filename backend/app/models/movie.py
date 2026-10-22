"""Model Movie."""
from ..extensions import db


class Movie(db.Model):
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(120))                 # nhiều thể loại, ngăn cách bằng dấu phẩy
    duration_minutes = db.Column(db.Integer, default=120)
    age_rating = db.Column(db.String(10), default="T13")
    rating = db.Column(db.Float, default=0)           # điểm đánh giá 0-10
    director = db.Column(db.String(120))
    cast_members = db.Column(db.String(500))
    description = db.Column(db.Text)
    release_date = db.Column(db.Date)
    theatrical_end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="now_showing")   # now_showing | coming_soon
    poster_url = db.Column(db.String(300))            # nếu trống, frontend vẽ poster bằng màu
    title_logo_url = db.Column(db.String(300))
    title_logo_enabled = db.Column(db.Boolean, nullable=False, default=False)
    poster_color = db.Column(db.String(20), default="#7f1d1d")
    trailer = db.relationship("MovieTrailer", back_populates="movie", uselist=False, cascade="all, delete-orphan")
    film = db.relationship("MovieFilm", back_populates="movie", uselist=False, cascade="all, delete-orphan")
    subtitles = db.relationship("MovieSubtitle", back_populates="movie", cascade="all, delete-orphan")

    def to_dict(self):
        trailer_url = None
        audio_url = None
        film_url = None
        if self.trailer:
            if self.trailer.extension in {"mp4", "webm"}:
                trailer_url = f"/api/movies/{self.id}/trailer?format={self.trailer.extension}&v={self.trailer.file_name}"
            elif self.trailer.extension == "mp3":
                audio_url = f"/api/movies/{self.id}/audio?format=mp3&v={self.trailer.file_name}"
                trailer_url = audio_url
            if self.trailer.audio_file_name:
                audio_url = f"/api/movies/{self.id}/audio?format=mp3&v={self.trailer.audio_file_name}"
        if self.film:
            film_url = f"/api/movies/{self.id}/film?format={self.film.extension}&v={self.film.file_name}"
        film_image_url = None
        if self.film and self.film.image_file_name:
            film_image_url = (
                f"/api/movies/{self.id}/film-image?format={self.film.image_extension}"
                f"&v={self.film.image_file_name}"
            )
        return {
            "id": self.id, "title": self.title, "genre": self.genre,
            "genres": [g.strip() for g in (self.genre or "").split(",") if g.strip()],
            "duration_minutes": self.duration_minutes, "age_rating": self.age_rating,
            "rating": self.rating, "director": self.director,
            "cast": self.cast_members,
            "description": self.description,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "theatrical_end_date": self.theatrical_end_date.isoformat() if self.theatrical_end_date else None,
            "status": self.status, "poster_url": self.poster_url,
            "title_logo_url": self.title_logo_url,
            "title_logo_enabled": self.title_logo_enabled,
            "poster_color": self.poster_color,
            "trailer_url": trailer_url,
            "audio_url": audio_url,
            "film_url": film_url,
            "film_image_url": film_image_url,
        }
