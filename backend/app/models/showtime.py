"""Model Showtime (suất chiếu)."""
from ..extensions import db


class Showtime(db.Model):
    __tablename__ = "showtimes"

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, index=True)   # giờ địa phương (naive)
    base_price = db.Column(db.Integer, default=90000)

    movie = db.relationship("Movie")
    room = db.relationship("Room")

    def to_dict(self):
        cinema = self.room.cinema
        return {
            "id": self.id,
            "start_time": self.start_time.isoformat(),
            "base_price": self.base_price,
            "movie": {k: getattr(self.movie, k) for k in
                      ("id", "title", "poster_url", "poster_color", "duration_minutes", "genre", "age_rating")},
            "cinema": cinema.to_dict(),
            "room": {"id": self.room.id, "name": self.room.name, "room_type": self.room.room_type},
        }
