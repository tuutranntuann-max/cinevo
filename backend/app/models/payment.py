"""Model Payment (giai đoạn khung: thanh toán giả lập)."""
from ..extensions import db
from ..timeutil import iso_utc, utc_now

PAYMENT_METHODS = ("QR", "EWALLET", "BANK")


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="PAID")
    transaction_ref = db.Column(db.String(60))
    paid_at = db.Column(db.DateTime, default=utc_now)

    booking = db.relationship("Booking", back_populates="payment")

    def to_dict(self):
        return {"id": self.id, "booking_id": self.booking_id,
                "booking_code": self.booking.code if self.booking else None,
                "method": self.method, "amount": self.amount, "status": self.status,
                "transaction_ref": self.transaction_ref,
                "paid_at": iso_utc(self.paid_at)}
