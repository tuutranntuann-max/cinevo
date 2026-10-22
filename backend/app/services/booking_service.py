"""Logic tạo Booking. Giá luôn được TÍNH LẠI ở server, không tin giá từ client."""
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, OperationalError

from ..extensions import db
from ..timeutil import local_now
from ..models import (Booking, BookingFood, BookingSeat, Food, Membership, Movie, MovieCancellation, Payment,
                      PAYMENT_METHODS, Promotion, Seat, SeatHold, Showtime, log_activity)
from .seat_reservations import ensure_booking_allowed, expire_seat_holds
from .commerce_config import require_payment_configuration
from .seat_pairs import validate_double_seat_selection


class BookingError(Exception):
    def __init__(self, message, status=400, code="BOOKING_ERROR"):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code


def taken_seat_ids(showtime_id: int) -> set:
    rows = BookingSeat.query.filter_by(showtime_id=showtime_id).all()
    return {r.seat_id for r in rows}


def create_booking(user, showtime_id, seat_ids, foods, method, promo_code="") -> Booking:
    try:
        return _create_booking(user, showtime_id, seat_ids, foods, method, promo_code)
    except IntegrityError as e:
        db.session.rollback()
        if "booking_seats.showtime_id, booking_seats.seat_id" not in str(e):
            raise
        raise BookingError("Một số ghế vừa có người đặt. Vui lòng chọn ghế khác.", 409, "SEAT_TAKEN") from e
    except OperationalError as e:
        db.session.rollback()
        if "locked" not in str(e).lower():
            raise
        raise BookingError("Đang có người khác đặt ghế. Vui lòng chọn ghế khác.", 409, "SEAT_TAKEN") from e


def _create_booking(user, showtime_id, seat_ids, foods, method, promo_code="") -> Booking:
    now = expire_seat_holds()
    if not ensure_booking_allowed(user.id, now):
        raise BookingError("Tài khoản tạm khóa đặt ghế do nhiều lần giữ ghế quá hạn. Vui lòng liên hệ hỗ trợ.",
                           429, "TRUST_BLOCKED")
    showtime = db.session.get(Showtime, showtime_id)
    if not showtime:
        raise BookingError("Suất chiếu không tồn tại.", 404)
    if db.session.get(MovieCancellation, showtime.movie_id):
        raise BookingError("Phim đã bị hủy và không nhận đặt vé.", 409, "MOVIE_CANCELLED")
    movie = db.session.get(Movie, showtime.movie_id)
    if movie.status == "ended":
        raise BookingError("Phim đã kết thúc công chiếu và không nhận đặt vé.", 409, "MOVIE_ENDED")
    if showtime.start_time < local_now():
        raise BookingError("Suất chiếu đã bắt đầu.")
    membership = (
        Membership.query.filter_by(user_id=user.id, status="ACTIVE")
        .filter(Membership.expires_at > now)
        .order_by(Membership.expires_at.desc()).first()
    )
    if membership:
        limits = {"SILVER": 5, "GOLD": 10, "DIAMOND": None}
        daily_limit = limits.get(membership.tier)
        if daily_limit is not None:
            day_start = showtime.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            booked_today = (
                db.session.query(Booking.showtime_id)
                .join(Showtime, Booking.showtime_id == Showtime.id)
                .filter(
                    Booking.user_id == user.id,
                    Booking.status.in_(("PENDING", "PAID")),
                    Showtime.start_time >= day_start,
                    Showtime.start_time < day_end,
                ).distinct().count()
            )
            if booked_today >= daily_limit:
                raise BookingError(f"Gói {membership.tier} giới hạn {daily_limit} phim mỗi ngày.",
                                   409, "MEMBERSHIP_DAILY_LIMIT")
    if method not in PAYMENT_METHODS:
        raise BookingError("Phương thức thanh toán không hợp lệ.")
    if method != "QR":
        raise BookingError("Hiện tại chỉ hỗ trợ thanh toán chuyển khoản QR.")
    require_payment_configuration()
    if not seat_ids or len(set(seat_ids)) != len(seat_ids) or len(seat_ids) > 8:
        raise BookingError("Vui lòng chọn từ 1 đến 8 ghế.")
    promotion = None
    if promo_code:
        promotion = Promotion.query.filter(
            func.upper(Promotion.code) == promo_code.upper(),
            Promotion.active.is_(True),
        ).first()
        if not promotion:
            raise BookingError("Mã giảm giá không hợp lệ hoặc đã hết hiệu lực.", 400, "PROMOTION_INVALID")

    seats = Seat.query.filter(Seat.id.in_(seat_ids), Seat.room_id == showtime.room_id).all()
    if len(seats) != len(seat_ids):
        raise BookingError("Ghế không thuộc phòng chiếu này.")
    if not validate_double_seat_selection(seats, seat_ids):
        raise BookingError("Ghế đôi cần được đặt cùng cả hai ghế liền nhau.", 400, "DOUBLE_SEAT_PAIR_REQUIRED")
    own_holds = {
        hold.seat_id
        for hold in SeatHold.query.filter_by(user_id=user.id, showtime_id=showtime_id)
        .filter(SeatHold.expires_at > now).all()
    }
    if not set(seat_ids).issubset(own_holds):
        raise BookingError("Thời gian giữ ghế đã hết. Vui lòng chọn lại ghế.", 409, "HOLD_EXPIRED")
    if taken_seat_ids(showtime_id) & set(seat_ids):
        raise BookingError("Một số ghế vừa có người đặt. Vui lòng chọn ghế khác.", 409, "SEAT_TAKEN")
    other_hold = SeatHold.query.filter(
        SeatHold.showtime_id == showtime_id,
        SeatHold.seat_id.in_(seat_ids),
        SeatHold.user_id != user.id,
        SeatHold.expires_at > now,
    ).first()
    if other_hold:
        raise BookingError("Một số ghế đang được người khác giữ. Vui lòng chọn ghế khác.", 409, "SEAT_TAKEN")

    booking = Booking(user_id=user.id, showtime_id=showtime_id, status="PENDING")
    db.session.add(booking)
    db.session.flush()

    seat_total = 0
    for seat in seats:
        price = seat.price_for(showtime)
        seat_total += price
        db.session.add(BookingSeat(booking_id=booking.id, showtime_id=showtime_id,
                                   seat_id=seat.id, price=price))

    food_total = 0
    food_discount = {"SILVER": 10, "GOLD": 20, "DIAMOND": 45}.get(membership.tier, 0) if membership else 0
    for item in foods or []:
        if not isinstance(item, dict):
            raise BookingError("Combo đồ ăn không hợp lệ.")
        try:
            food_id, qty = int(item.get("food_id")), int(item.get("quantity", 0))
        except (TypeError, ValueError):
            raise BookingError("Combo đồ ăn không hợp lệ.")
        food = db.session.get(Food, food_id)
        if not food or not food.available or not (0 < qty <= 20):
            raise BookingError("Combo đồ ăn không hợp lệ.")
        discounted_price = food.price * (100 - food_discount) // 100
        food_total += discounted_price * qty
        db.session.add(BookingFood(booking_id=booking.id, food_id=food.id,
                                   quantity=qty, unit_price=discounted_price))

    booking.seat_amount, booking.food_amount = seat_total, food_total
    subtotal = seat_total + food_total
    booking.promo_code = promotion.code if promotion else None
    booking.discount_amount = subtotal * promotion.discount_percent // 100 if promotion else 0
    booking.total_amount = subtotal - booking.discount_amount
    booking.code = f"CV{local_now():%m%y}{booking.id:04d}"       # ví dụ CV10260001

    SeatHold.query.filter(
        SeatHold.user_id == user.id,
        SeatHold.showtime_id == showtime_id,
        SeatHold.seat_id.in_(seat_ids),
    ).delete(synchronize_session=False)
    db.session.add(Payment(booking_id=booking.id, method=method, amount=booking.total_amount,
                           status="PENDING", transaction_ref=booking.code, paid_at=None))
    log_activity(user.id, "BOOKING_CREATED", f"{booking.code} - {booking.total_amount}đ")
    db.session.commit()
    return booking
