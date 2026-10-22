"""API combo đồ ăn và đặt vé. Đặt vé / xem vé yêu cầu đăng nhập."""
from flask import Blueprint, g, jsonify

from ..models import Booking, Food
from ..services.auth_service import auth_required
from ..services.booking_service import BookingError, create_booking
from ..services.seat_reservations import expire_seat_holds
from ..services.validation import ApiError, clean_int, clean_str, json_body

bp = Blueprint("bookings", __name__, url_prefix="/api")


@bp.get("/foods")
def foods():
    return jsonify([f.to_dict() for f in Food.query.filter_by(available=True).order_by(Food.price).all()])


@bp.post("/bookings")
@auth_required
def make_booking():
    data = json_body()
    seat_ids, foods = data.get("seat_ids") or [], data.get("foods") or []
    if not isinstance(seat_ids, list) or not isinstance(foods, list) or len(foods) > 20:
        raise ApiError("Dữ liệu đặt vé không hợp lệ.")
    showtime_id = clean_int(data.get("showtime_id"), "Suất chiếu", lo=1)
    seat_ids = [clean_int(s, "Ghế", lo=1) for s in seat_ids]
    try:
        booking = create_booking(g.current_user, showtime_id, seat_ids, foods,
                                 clean_str(data.get("payment_method"), "phương thức thanh toán", max_len=20),
                                 clean_str(data.get("promo_code"), "mã giảm giá", max_len=30))
    except BookingError as e:
        return jsonify({"message": e.message, "code": e.code}), e.status
    return jsonify(booking.to_dict()), 201


@bp.get("/bookings/my")
@auth_required
def my_bookings():
    expire_seat_holds()
    rows = (Booking.query.filter_by(user_id=g.current_user.id)
            .order_by(Booking.created_at.desc()).all())
    return jsonify([b.to_dict() for b in rows])


@bp.get("/bookings/<code>")
@auth_required
def booking_detail(code):
    expire_seat_holds()
    booking = Booking.query.filter_by(code=code[:20]).first()
    is_staff = g.current_user.role.name in ("MANAGER", "ADMIN")
    if not booking or (booking.user_id != g.current_user.id and not is_staff):
        return jsonify({"message": "Không tìm thấy vé."}), 404
    return jsonify(booking.to_dict())
