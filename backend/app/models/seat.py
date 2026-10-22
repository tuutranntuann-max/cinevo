"""Model Seat (ghế trong phòng chiếu)."""
from ..extensions import db

SEAT_STANDARD = "STANDARD"
SEAT_VIP = "VIP"
VIP_SURCHARGE = 20000   # phụ thu ghế VIP (VNĐ)


class Seat(db.Model):
    __tablename__ = "seats"
    __table_args__ = (db.UniqueConstraint("room_id", "row_label", "number"),)

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    row_label = db.Column(db.String(2), nullable=False)      # A, B, C...
    number = db.Column(db.Integer, nullable=False)
    seat_type = db.Column(db.String(20), default=SEAT_STANDARD)

    room = db.relationship("Room", back_populates="seats")

    @property
    def label(self):
        return f"{self.row_label}{self.number}"

    def price_for(self, showtime) -> int:
        return showtime.base_price + (VIP_SURCHARGE if self.seat_type == SEAT_VIP else 0)

    def to_dict(self):
        return {"id": self.id, "room_id": self.room_id, "label": self.label,
                "row": self.row_label, "number": self.number, "type": self.seat_type}
