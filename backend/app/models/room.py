"""Model Room (phòng chiếu)."""
from ..extensions import db


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    cinema_id = db.Column(db.Integer, db.ForeignKey("cinemas.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)          # "Phòng 01"
    room_type = db.Column(db.String(20), default="2D")       # 2D | 3D | IMAX
    total_rows = db.Column(db.Integer, default=8)
    total_cols = db.Column(db.Integer, default=10)

    cinema = db.relationship("Cinema", back_populates="rooms")
    seats = db.relationship("Seat", back_populates="room", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "cinema_id": self.cinema_id,
                "cinema": self.cinema.name if self.cinema else None,
                "name": self.name, "room_type": self.room_type,
                "total_rows": self.total_rows, "total_cols": self.total_cols}
