from datetime import timedelta

from ..extensions import db
from ..models import Booking, BookingSeat, SeatHold, UserTrust
from ..models.seat_hold import SEAT_HOLD_DURATION
from ..timeutil import utc_now


HOLD_DURATION = SEAT_HOLD_DURATION
REPUTATION_LOCK_DURATION = timedelta(hours=24)


def expire_seat_holds(now=None):
    now = now or utc_now()
    expired = SeatHold.query.filter(SeatHold.expires_at <= now).all()
    expired_cycles = {(hold.user_id, hold.showtime_id, hold.expires_at) for hold in expired}
    for hold in expired:
        db.session.delete(hold)
    for user_id, _showtime_id, _expires_at in expired_cycles:
        _record_expired_hold(user_id, now)

    expired_bookings = (
        Booking.query.filter_by(status="PENDING")
        .filter(Booking.created_at <= now - HOLD_DURATION).all()
    )
    for booking in expired_bookings:
        booking.status = "CANCELLED"
        if booking.payment:
            booking.payment.status = "EXPIRED"
        BookingSeat.query.filter_by(booking_id=booking.id).delete()
        _record_expired_hold(booking.user_id, now)

    if expired or expired_bookings:
        db.session.commit()
    return now


def _record_expired_hold(user_id, now):
    trust = db.session.get(UserTrust, user_id)
    if trust is None:
        trust = UserTrust(user_id=user_id)
        db.session.add(trust)
        db.session.flush()
    trust.expired_holds += 1
    if trust.expired_holds % 3 == 0:
        trust.score = max(0, trust.score - 1)
        trust.penalties += 1
        if trust.penalties >= 3:
            trust.blocked_until = now + REPUTATION_LOCK_DURATION


def ensure_booking_allowed(user_id, now=None):
    now = now or utc_now()
    trust = db.session.get(UserTrust, user_id)
    if trust and trust.blocked_until and trust.blocked_until > now:
        return False
    return True


def seat_hold_duration():
    return HOLD_DURATION
