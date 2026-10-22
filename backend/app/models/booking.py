"""Model Booking, BookingSeat, BookingFood."""
from ..extensions import db
from .seat_hold import SEAT_HOLD_DURATION
from ..timeutil import iso_utc, local_now, utc_now


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, index=True)          # CV10260001
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    showtime_id = db.Column(db.Integer, db.ForeignKey("showtimes.id"), nullable=False)
    seat_amount = db.Column(db.Integer, default=0)
    food_amount = db.Column(db.Integer, default=0)
    discount_amount = db.Column(db.Integer, nullable=False, default=0)
    promo_code = db.Column(db.String(30))
    total_amount = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="PENDING")              # PENDING | PAID | CANCELLED
    created_at = db.Column(db.DateTime, default=utc_now)

    user = db.relationship("User")
    showtime = db.relationship("Showtime")
    seats = db.relationship("BookingSeat", back_populates="booking", cascade="all, delete-orphan")
    foods = db.relationship("BookingFood", back_populates="booking", cascade="all, delete-orphan")
    payment = db.relationship("Payment", back_populates="booking", uselist=False)

    def to_dict(self):
        st = self.showtime
        seat_labels = sorted(bs.seat.label for bs in self.seats)
        return {
            "id": self.id, "code": self.code, "status": self.status,
            "movie": {"id": st.movie.id, "title": st.movie.title,
                      "poster_color": st.movie.poster_color, "poster_url": st.movie.poster_url,
                      "director": st.movie.director, "cast_members": st.movie.cast_members,
                      "duration_minutes": st.movie.duration_minutes},
            "cinema": st.room.cinema.name, "city": st.room.cinema.city,
            "room": st.room.name, "start_time": st.start_time.isoformat(),
            "is_upcoming": st.start_time >= local_now(),
            "seats": seat_labels,
            "foods": [{"name": bf.food.name, "quantity": bf.quantity, "unit_price": bf.unit_price}
                      for bf in self.foods],
            "seat_amount": self.seat_amount, "food_amount": self.food_amount,
            "subtotal_amount": self.seat_amount + self.food_amount,
            "discount_amount": self.discount_amount,
            "promo_code": self.promo_code,
            "total_amount": self.total_amount,
            "payment": self.payment.to_dict() if self.payment else None,
            "user": {"id": self.user.id, "full_name": self.user.full_name, "email": self.user.email},
            "created_at": iso_utc(self.created_at),
            "hold_expires_at": iso_utc(self.created_at + SEAT_HOLD_DURATION) if self.status == "PENDING" else None,
            "qr_payload": f"CINEVO|{self.code}|{st.id}|{','.join(seat_labels)}",
        }


class BookingSeat(db.Model):
    """Ghế đã đặt. UNIQUE(showtime_id, seat_id) chặn đặt trùng ghế ở tầng database."""
    __tablename__ = "booking_seats"
    __table_args__ = (db.UniqueConstraint("showtime_id", "seat_id", name="uq_showtime_seat"),)

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    showtime_id = db.Column(db.Integer, db.ForeignKey("showtimes.id"), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id"), nullable=False)
    price = db.Column(db.Integer, nullable=False)

    booking = db.relationship("Booking", back_populates="seats")
    seat = db.relationship("Seat")


class BookingFood(db.Model):
    __tablename__ = "booking_foods"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey("foods.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Integer, nullable=False)

    booking = db.relationship("Booking", back_populates="foods")
    food = db.relationship("Food")
