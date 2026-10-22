"""API cho MANAGER (quản lý rạp). Admin cũng được truy cập. Giai đoạn khung: chủ yếu đọc dữ liệu."""
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Booking, BookingSeat, Cinema, Food, Movie, Product, Room, Seat, SeatHold, Showtime,
    ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER,
)
from ..services.auth_service import roles_required
from ..services.seat_pairs import validate_double_seat_selection
from ..services.validation import clean_int, clean_str, ApiError, json_body, int_arg
from ..timeutil import utc_now

MOVIE_STATUSES = ("now_showing", "coming_soon")
bp = Blueprint("manager", __name__, url_prefix="/api/manager")
staff = roles_required(ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN)


@bp.get("/dashboard")
@staff
def dashboard():
    revenue = (db.session.query(func.coalesce(func.sum(Booking.total_amount), 0))
               .filter(Booking.status == "PAID").scalar())
    return jsonify({"stats": [
        {"label": "Phim", "value": Movie.query.count()},
        {"label": "Rạp", "value": Cinema.query.count()},
        {"label": "Suất chiếu", "value": Showtime.query.count()},
        {"label": "Vé đã bán", "value": Booking.query.filter_by(status="PAID").count()},
        {"label": "Doanh thu (đ)", "value": f"{revenue:,}".replace(",", ".")},
    ]})


@bp.get("/movies")
@staff
def movies():
    return jsonify([m.to_dict() for m in Movie.query.filter(Movie.status != "draft").all()])


@bp.post("/movies")
@staff
def create_movie():
    """Mẫu thêm phim. TODO: validate đầy đủ ở giai đoạn nghiệp vụ."""
    d = json_body()
    status = d.get("status", "coming_soon")
    if status not in MOVIE_STATUSES:
        raise ApiError("Trạng thái phim không hợp lệ.")
    movie = Movie(title=clean_str(d.get("title"), "tên phim", max_len=200, required=True),
                  genre=clean_str(d.get("genre"), "thể loại", max_len=120) or None,
                  duration_minutes=clean_int(d.get("duration_minutes", 120), "thời lượng", lo=1, hi=600),
                  description=clean_str(d.get("description"), "mô tả", max_len=5000) or None, status=status)
    db.session.add(movie)
    db.session.commit()
    return jsonify(movie.to_dict()), 201


@bp.get("/cinemas")
@staff
def cinemas():
    return jsonify([c.to_dict() for c in Cinema.query.all()])


@bp.get("/rooms")
@staff
def rooms():
    return jsonify([r.to_dict() for r in Room.query.all()])


@bp.get("/seats")
@staff
def seats():
    q = Seat.query
    if (rid := int_arg("room_id")) is not None:
        q = q.filter_by(room_id=rid)
    return jsonify([s.to_dict() for s in q.limit(200).all()])


@bp.patch("/seats/type")
@roles_required(ROLE_MANAGER, ROLE_ADMIN)
def update_seat_type():
    data = json_body()
    seat_ids = data.get("seat_ids")
    if not isinstance(seat_ids, list) or not seat_ids or len(seat_ids) > 200:
        raise ApiError("Hãy chọn ghế cần cập nhật.")
    seat_ids = [clean_int(seat_id, "ghế", lo=1) for seat_id in seat_ids]
    if len(set(seat_ids)) != len(seat_ids):
        raise ApiError("Danh sách ghế bị trùng.")
    seat_type = clean_str(data.get("type"), "loại ghế", max_len=20, required=True).upper()
    if seat_type not in {"STANDARD", "VIP", "DOUBLE"}:
        raise ApiError("Loại ghế phải là Thường, VIP hoặc ghế đôi.")

    seats = Seat.query.filter(Seat.id.in_(seat_ids)).order_by(
        Seat.room_id, Seat.row_label, Seat.number,
    ).all()
    if len(seats) != len(seat_ids) or len({seat.room_id for seat in seats}) != 1:
        raise ApiError("Các ghế phải tồn tại và cùng thuộc một phòng.")
    selected = set(seat_ids)
    for seat in seats:
        if seat.seat_type == "DOUBLE" and seat_type != "DOUBLE":
            partner_number = seat.number + 1 if seat.number % 2 else seat.number - 1
            partner = Seat.query.filter_by(
                room_id=seat.room_id,
                row_label=seat.row_label,
                number=partner_number,
            ).first()
            if partner and partner.id not in selected:
                raise ApiError("Hãy chọn cả hai ghế của cặp đôi để đổi loại.")

    if seat_type == "DOUBLE":
        if len(seats) % 2:
            raise ApiError("Ghế đôi cần được chọn theo từng cặp hai ghế liền nhau.")
        if any(
            left.room_id != right.room_id
            or left.row_label != right.row_label
            or left.number % 2 != 1
            or right.number != left.number + 1
            for left, right in zip(seats[::2], seats[1::2])
        ):
            raise ApiError("Mỗi cặp ghế đôi phải cùng hàng và gồm hai số liền nhau, bắt đầu từ ghế lẻ.")

    if BookingSeat.query.filter(BookingSeat.seat_id.in_(seat_ids)).first():
        raise ApiError("Không thể đổi loại ghế đã được sử dụng trong giao dịch đặt vé.")
    if SeatHold.query.filter(
        SeatHold.seat_id.in_(seat_ids),
        SeatHold.expires_at > utc_now(),
    ).first():
        raise ApiError("Không thể đổi loại ghế đang được khách giữ.")

    for seat in seats:
        seat.seat_type = seat_type
    db.session.commit()
    return jsonify({"seats": [seat.to_dict() for seat in seats]})


@bp.get("/showtimes")
@staff
def showtimes():
    rows = Showtime.query.order_by(Showtime.start_time).limit(100).all()
    return jsonify([{"id": s.id, "movie": s.movie.title, "cinema": s.room.cinema.name, "room": s.room.name,
                     "start_time": s.start_time.isoformat(), "base_price": s.base_price} for s in rows])


@bp.get("/bookings")
@staff
def bookings():
    rows = Booking.query.order_by(Booking.created_at.desc()).limit(100).all()
    return jsonify([{"code": b.code, "customer": b.user.full_name, "movie": b.showtime.movie.title,
                     "start_time": b.showtime.start_time.isoformat(), "seats": ", ".join(sorted(s.seat.label for s in b.seats)),
                     "total_amount": b.total_amount, "status": b.status} for b in rows])


@bp.get("/foods")
@staff
def foods():
    return jsonify([f.to_dict() for f in Food.query.all()])


@bp.get("/products")
@staff
def products():
    return jsonify([product.to_dict() for product in Product.query.order_by(Product.id).all()])


@bp.post("/products")
@staff
def create_product():
    data = json_body()
    product = Product(
        name=clean_str(data.get("name"), "tên sản phẩm", max_len=100, required=True),
        category=clean_str(data.get("category", "Khác"), "danh mục", max_len=60, required=True),
        description=clean_str(data.get("description"), "mô tả", max_len=200) or None,
        price=clean_int(data.get("price"), "giá", lo=0, hi=1_000_000_000),
        stock_quantity=clean_int(data.get("stock_quantity"), "tồn kho", lo=0, hi=1_000_000_000),
        active=_manager_bool(data, "active", True),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201


@bp.put("/products/<int:product_id>")
@staff
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        raise ApiError("Không tìm thấy sản phẩm.", 404)
    data = json_body()
    if "name" in data:
        product.name = clean_str(data["name"], "tên sản phẩm", max_len=100, required=True)
    if "category" in data:
        product.category = clean_str(data["category"], "danh mục", max_len=60, required=True)
    if "description" in data:
        product.description = clean_str(data["description"], "mô tả", max_len=200) or None
    if "price" in data:
        product.price = clean_int(data["price"], "giá", lo=0, hi=1_000_000_000)
    if "stock_quantity" in data:
        product.stock_quantity = clean_int(data["stock_quantity"], "tồn kho", lo=0, hi=1_000_000_000)
    if "active" in data:
        product.active = _manager_bool(data, "active")
    db.session.commit()
    return jsonify(product.to_dict())


def _manager_bool(data, key, default=None):
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ApiError(f"{key} không hợp lệ.")
    return value


@bp.get("/report")
@staff
def report():
    """Doanh thu theo phim."""
    rows = (db.session.query(Movie.title, func.count(Booking.id), func.coalesce(func.sum(Booking.total_amount), 0))
            .join(Showtime, Showtime.movie_id == Movie.id).join(Booking, Booking.showtime_id == Showtime.id)
            .filter(Booking.status == "PAID")
            .group_by(Movie.title).all())
    return jsonify([{"movie": t, "bookings": n, "revenue": int(r)} for t, n, r in rows])
