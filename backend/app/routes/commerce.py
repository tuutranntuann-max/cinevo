"""Membership, pickup shop, QR settings, payment review, and temporary seat reservations."""
from datetime import timedelta
from secrets import token_hex

from flask import Blueprint, g, jsonify
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, OperationalError

from ..extensions import db
from ..models import (
    Booking, BookingSeat, Cinema, Membership, Payment, Product,
    ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER, Seat, SeatHold, Showtime,
    ShopOrder, ShopOrderItem, User, UserTrust, log_activity,
)
from ..services.auth_service import auth_required, roles_required
from ..services.commerce_config import get_commerce_settings, require_payment_configuration
from ..services.seat_reservations import ensure_booking_allowed, expire_seat_holds, seat_hold_duration
from ..services.seat_pairs import validate_double_seat_selection
from ..services.validation import ApiError, clean_int, clean_str, json_body
from ..timeutil import iso_utc, local_now, utc_now

bp = Blueprint("commerce", __name__, url_prefix="/api/commerce")
STAFF_ROLES = (ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE)
TIERS = {
    "SILVER": {"label": "Bạc", "daily_movies": 5, "food_discount": 10, "product_discount": 15},
    "GOLD": {"label": "Vàng", "daily_movies": 10, "food_discount": 20, "product_discount": 30},
    "DIAMOND": {"label": "Kim cương", "daily_movies": None, "food_discount": 45, "product_discount": 45},
}
def _settings():
    return get_commerce_settings()


def _profile_membership(user_id):
    now = utc_now()
    scheduled = Membership.query.filter_by(user_id=user_id, status="SCHEDULED").filter(
        Membership.starts_at <= now
    ).update({"status": "ACTIVE"}, synchronize_session=False)
    if scheduled:
        db.session.commit()
    return (
        Membership.query.filter_by(user_id=user_id, status="ACTIVE")
        .filter(Membership.starts_at <= now, Membership.expires_at > now)
        .order_by(Membership.expires_at.desc()).first()
    )


def _trust_dict(trust):
    return trust.to_dict() if trust else {
        "score": 100, "expired_holds": 0, "penalties": 0, "blocked_until": None,
    }


def _ensure_booking_allowed(user_id):
    if not ensure_booking_allowed(user_id):
        raise ApiError("Tài khoản tạm khóa đặt ghế do nhiều lần giữ ghế quá hạn. Vui lòng liên hệ hỗ trợ.", 429, "TRUST_BLOCKED")
    return db.session.get(UserTrust, user_id)


def _payment_row(kind, item_id, user_id, amount, ref, created_at, status):
    user = db.session.get(User, user_id)
    return {
        "kind": kind,
        "id": item_id,
        "user_id": user_id,
        "customer_name": user.full_name if user else "",
        "customer_email": user.email if user else "",
        "amount": amount,
        "transaction_ref": ref,
        "created_at": iso_utc(created_at),
        "status": status,
    }


def _expire_commerce_orders():
    cutoff = utc_now() - timedelta(minutes=15)
    expired_memberships = (
        Membership.query.filter_by(status="PENDING")
        .filter(Membership.created_at <= cutoff).all()
    )
    expired_orders = (
        ShopOrder.query.filter_by(status="PENDING")
        .filter(ShopOrder.created_at <= cutoff).all()
    )
    for item in expired_memberships:
        item.status = "EXPIRED"
    for order in expired_orders:
        order.status = "CANCELLED"
        for item in order.items:
            item.product.stock_quantity += item.quantity
    if expired_memberships or expired_orders:
        db.session.commit()


@bp.get("/settings")
def public_settings():
    _, values = _settings()
    return jsonify({
        "bank_name": values["bank_name"],
        "bank_bin": values["bank_bin"],
        "account_number": values["account_number"],
        "account_name": values["account_name"],
        "qr_image_url": values["qr_image_url"],
    })


@bp.get("/membership/plans")
def membership_plans():
    _, values = _settings()
    return jsonify([
        {
            **tier,
            "code": code,
            "duration_days": 30,
            "price": values["membership_prices"].get(code),
        }
        for code, tier in TIERS.items()
    ])


@bp.post("/membership/purchases")
@auth_required
def purchase_membership():
    data = json_body()
    tier = clean_str(data.get("tier"), "hạng thành viên", max_len=20, required=True).upper()
    if tier not in TIERS:
        raise ApiError("Hạng thành viên không hợp lệ.")
    require_payment_configuration()
    _, values = _settings()
    amount = values["membership_prices"].get(tier)
    if not isinstance(amount, int) or amount <= 0:
        raise ApiError("Gói này chưa được Admin thiết lập giá.", 409, "PLAN_UNAVAILABLE")
    ref = f"MEM-{g.current_user.id}-{token_hex(5).upper()}"
    purchase = Membership(
        user_id=g.current_user.id,
        tier=tier,
        amount=amount,
        payment_ref=ref,
        starts_at=utc_now(),
        expires_at=utc_now() + timedelta(days=30),
        status="PENDING",
    )
    db.session.add(purchase)
    db.session.commit()
    return jsonify({"membership": purchase.to_dict(), "payment_ref": ref, "amount": amount}), 201


@bp.get("/membership/mine")
@auth_required
def my_membership():
    _expire_commerce_orders()
    active = _profile_membership(g.current_user.id)
    history = (
        Membership.query.filter_by(user_id=g.current_user.id)
        .order_by(Membership.created_at.desc()).limit(50).all()
    )
    trust = db.session.get(UserTrust, g.current_user.id)
    return jsonify({
        "active": active.to_dict() if active else None,
        "history": [item.to_dict() for item in history],
        "trust": _trust_dict(trust),
    })


@bp.get("/shop/products")
def shop_products():
    return jsonify([
        product.to_dict()
        for product in Product.query.filter_by(active=True).filter(Product.stock_quantity > 0).order_by(Product.category, Product.name)
    ])


@bp.post("/shop/orders")
@auth_required
def create_shop_order():
    require_payment_configuration()
    data = json_body()
    items = data.get("items")
    if not isinstance(items, list) or not items or len(items) > 30:
        raise ApiError("Giỏ hàng không hợp lệ.")
    cinema_id = clean_int(data.get("pickup_cinema_id"), "rạp nhận hàng", lo=1)
    cinema = db.session.get(Cinema, cinema_id)
    if not cinema:
        raise ApiError("Rạp nhận hàng không hợp lệ.", 404)
    pickup = f"{cinema.name} · {cinema.city}"
    combined = {}
    for entry in items:
        if not isinstance(entry, dict):
            raise ApiError("Mặt hàng trong giỏ không hợp lệ.")
        product_id = clean_int(entry.get("product_id"), "sản phẩm", lo=1)
        quantity = clean_int(entry.get("quantity"), "số lượng", lo=1, hi=50)
        combined[product_id] = combined.get(product_id, 0) + quantity
        if combined[product_id] > 50:
            raise ApiError("Số lượng một mặt hàng không được vượt quá 50.")
    products = {p.id: p for p in Product.query.filter(Product.id.in_(combined)).all()}
    if len(products) != len(combined):
        raise ApiError("Không tìm thấy một số sản phẩm trong giỏ.", 404)
    subtotal = 0
    for product_id, quantity in combined.items():
        product = products[product_id]
        if not product.active or product.stock_quantity < quantity:
            raise ApiError(f"Sản phẩm '{product.name}' không đủ tồn kho.", 409, "OUT_OF_STOCK")
        subtotal += product.price * quantity
    active_membership = _profile_membership(g.current_user.id)
    discount_rate = 0
    if active_membership:
        discount_rate = TIERS[active_membership.tier]["product_discount"]
    discount = subtotal * discount_rate // 100
    order = ShopOrder(
        code=f"SHOP-{token_hex(5).upper()}",
        user_id=g.current_user.id,
        subtotal=subtotal,
        discount_amount=discount,
        total_amount=subtotal - discount,
        pickup_cinema=pickup,
        status="PENDING",
    )
    db.session.add(order)
    db.session.flush()
    for product_id, quantity in combined.items():
        product = products[product_id]
        stock_change = db.session.execute(
            update(Product)
            .where(
                Product.id == product_id,
                Product.active.is_(True),
                Product.stock_quantity >= quantity,
            )
            .values(stock_quantity=Product.stock_quantity - quantity)
        )
        if stock_change.rowcount != 1:
            db.session.rollback()
            raise ApiError(f"Sản phẩm '{product.name}' vừa hết hàng. Vui lòng làm mới giỏ hàng.", 409, "OUT_OF_STOCK")
        db.session.add(ShopOrderItem(
            order_id=order.id, product_id=product_id,
            quantity=quantity, unit_price=product.price,
        ))
    db.session.commit()
    return jsonify(order.to_dict()), 201


@bp.get("/shop/orders/mine")
@auth_required
def my_shop_orders():
    _expire_commerce_orders()
    rows = ShopOrder.query.filter_by(user_id=g.current_user.id).order_by(ShopOrder.created_at.desc()).limit(50)
    return jsonify([order.to_dict() for order in rows])


@bp.get("/admin/shop/orders")
@roles_required(*STAFF_ROLES)
def shop_orders_for_staff():
    rows = ShopOrder.query.order_by(ShopOrder.created_at.desc()).limit(200).all()
    return jsonify([
        {
            **order.to_dict(),
            "customer_name": order.user.full_name,
            "customer_email": order.user.email,
        }
        for order in rows
    ])


@bp.patch("/admin/shop/orders/<int:order_id>")
@roles_required(*STAFF_ROLES)
def update_shop_order(order_id):
    order = db.session.get(ShopOrder, order_id)
    if not order:
        raise ApiError("Không tìm thấy đơn Shop.", 404)
    status = json_body().get("status")
    if status == "COLLECTED" and order.status == "READY_FOR_PICKUP":
        order.status = "COLLECTED"
    elif status == "CANCELLED" and order.status in ("PENDING", "READY_FOR_PICKUP"):
        order.status = "CANCELLED"
        for item in order.items:
            item.product.stock_quantity += item.quantity
    else:
        raise ApiError("Trạng thái đơn hàng không thể chuyển đổi.", 409)
    log_activity(g.current_user.id, "SHOP_ORDER_UPDATED", f"{order.code} -> {order.status}")
    db.session.commit()
    return jsonify(order.to_dict())


@bp.post("/seat-holds")
@auth_required
def reserve_seats():
    now = expire_seat_holds()
    trust = _ensure_booking_allowed(g.current_user.id)
    data = json_body()
    showtime_id = clean_int(data.get("showtime_id"), "suất chiếu", lo=1)
    seat_ids = data.get("seat_ids")
    if not isinstance(seat_ids, list) or len(seat_ids) > 8:
        raise ApiError("Danh sách ghế không hợp lệ.")
    seat_ids = [clean_int(value, "ghế", lo=1) for value in seat_ids]
    if len(set(seat_ids)) != len(seat_ids):
        raise ApiError("Danh sách ghế bị trùng.")
    showtime = db.session.get(Showtime, showtime_id)
    if not showtime:
        raise ApiError("Suất chiếu không tồn tại.", 404)
    if showtime.start_time < local_now():
        raise ApiError("Suất chiếu đã bắt đầu.")
    SeatHold.query.filter(
        SeatHold.user_id == g.current_user.id,
        SeatHold.showtime_id != showtime_id,
    ).delete(synchronize_session=False)
    existing_user_holds = SeatHold.query.filter_by(user_id=g.current_user.id, showtime_id=showtime_id).all()
    keep = set(seat_ids)
    for hold in existing_user_holds:
        if hold.seat_id not in keep:
            db.session.delete(hold)
    if not seat_ids:
        db.session.commit()
        return jsonify({"holds": [], "expires_at": None, "trust": _trust_dict(trust)})
    seats = Seat.query.filter(Seat.id.in_(seat_ids), Seat.room_id == showtime.room_id).all()
    if len(seats) != len(seat_ids):
        raise ApiError("Một số ghế không thuộc phòng chiếu này.")
    if not validate_double_seat_selection(seats, seat_ids):
        raise ApiError("Ghế đôi cần được giữ cùng cả hai ghế liền nhau.", 400, "DOUBLE_SEAT_PAIR_REQUIRED")
    booked = {row.seat_id for row in BookingSeat.query.filter_by(showtime_id=showtime_id).all()}
    other_holds = SeatHold.query.filter(
        SeatHold.showtime_id == showtime_id,
        SeatHold.seat_id.in_(seat_ids),
        SeatHold.user_id != g.current_user.id,
        SeatHold.expires_at > now,
    ).first()
    if booked.intersection(seat_ids) or other_holds:
        raise ApiError("Một số ghế vừa được đặt hoặc đang được người khác giữ.", 409, "SEAT_TAKEN")
    existing_seat_ids = {hold.seat_id for hold in existing_user_holds}
    expires_at = min((hold.expires_at for hold in existing_user_holds), default=now + seat_hold_duration())
    for seat_id in seat_ids:
        if seat_id not in existing_seat_ids:
            db.session.add(SeatHold(
                user_id=g.current_user.id,
                showtime_id=showtime_id,
                seat_id=seat_id,
                expires_at=expires_at,
            ))
    try:
        db.session.commit()
    except (IntegrityError, OperationalError) as exc:
        db.session.rollback()
        if isinstance(exc, OperationalError) and "locked" not in str(exc).lower():
            raise
        raise ApiError("Một số ghế vừa được người khác giữ. Vui lòng tải lại sơ đồ ghế.", 409, "SEAT_TAKEN") from exc
    rows = SeatHold.query.filter_by(user_id=g.current_user.id, showtime_id=showtime_id).all()
    return jsonify({
        "holds": [row.to_dict() for row in rows],
        "expires_at": iso_utc(min(row.expires_at for row in rows)) if rows else None,
        "trust": _trust_dict(trust),
    })


@bp.delete("/seat-holds/<int:showtime_id>")
@auth_required
def release_seats(showtime_id):
    SeatHold.query.filter_by(user_id=g.current_user.id, showtime_id=showtime_id).delete()
    db.session.commit()
    return jsonify({"released": True})


@bp.get("/seat-holds/<int:showtime_id>")
def show_holds(showtime_id):
    expire_seat_holds()
    rows = SeatHold.query.filter_by(showtime_id=showtime_id).filter(SeatHold.expires_at > utc_now()).all()
    return jsonify([{"seat_id": row.seat_id, "expires_at": iso_utc(row.expires_at)} for row in rows])


@bp.get("/seat-holds/my/<int:showtime_id>")
@auth_required
def my_seat_holds(showtime_id):
    expire_seat_holds()
    rows = (
        SeatHold.query.filter_by(showtime_id=showtime_id, user_id=g.current_user.id)
        .filter(SeatHold.expires_at > utc_now()).all()
    )
    return jsonify([row.to_dict() for row in rows])


@bp.get("/admin/settings")
@roles_required(*STAFF_ROLES)
def admin_settings():
    _, values = _settings()
    return jsonify(values)


@bp.patch("/admin/settings")
@roles_required(ROLE_ADMIN)
def update_admin_settings():
    data = json_body()
    row, values = _settings()
    string_fields = ("bank_name", "bank_bin", "account_number", "account_name", "qr_image_url")
    for field in string_fields:
        if field in data:
            value = clean_str(data[field], field, max_len=300) or ""
            if field == "bank_bin" and value and (len(value) != 6 or not value.isdigit()):
                raise ApiError("Mã BIN ngân hàng phải gồm đúng 6 chữ số.")
            if field == "qr_image_url" and value and not (
                value.startswith("/api/content/media/") or value.startswith("https://")
            ):
                raise ApiError("Ảnh QR phải được tải lên Cinevo hoặc dùng liên kết HTTPS.")
            values[field] = value
    if "membership_prices" in data:
        prices = data["membership_prices"]
        if not isinstance(prices, dict):
            raise ApiError("Bảng giá thành viên không hợp lệ.")
        for tier in TIERS:
            if tier in prices:
                value = prices[tier]
                if value is not None:
                    value = clean_int(value, f"giá {tier}", lo=1, hi=1_000_000_000)
                values["membership_prices"][tier] = value
    row.values = values
    log_activity(g.current_user.id, "COMMERCE_SETTINGS_UPDATED", "Cập nhật thanh toán và gói thành viên")
    db.session.commit()
    return jsonify(values)


@bp.get("/admin/pending")
@roles_required(*STAFF_ROLES)
def pending_payments():
    expire_seat_holds()
    _expire_commerce_orders()
    rows = []
    for payment in Payment.query.filter_by(status="PENDING").order_by(Payment.id).all():
        booking = payment.booking
        rows.append(_payment_row("BOOKING", payment.id, booking.user_id, payment.amount, booking.code, booking.created_at, payment.status))
    for membership in Membership.query.filter_by(status="PENDING").order_by(Membership.id).all():
        rows.append(_payment_row("MEMBERSHIP", membership.id, membership.user_id, membership.amount, membership.payment_ref, membership.created_at, membership.status))
    for order in ShopOrder.query.filter_by(status="PENDING").order_by(ShopOrder.id).all():
        rows.append(_payment_row("SHOP", order.id, order.user_id, order.total_amount, order.code, order.created_at, order.status))
    return jsonify(sorted(rows, key=lambda row: row["created_at"] or "", reverse=True))


@bp.get("/admin/history")
@roles_required(*STAFF_ROLES)
def transaction_history():
    rows = []
    for payment in Payment.query.order_by(Payment.id.desc()).limit(100).all():
        booking = payment.booking
        rows.append(_payment_row(
            "BOOKING", payment.id, booking.user_id, payment.amount, booking.code, booking.created_at, payment.status,
        ))
    for membership in Membership.query.order_by(Membership.id.desc()).limit(100).all():
        rows.append(_payment_row(
            "MEMBERSHIP", membership.id, membership.user_id, membership.amount,
            membership.payment_ref, membership.created_at, membership.status,
        ))
    for order in ShopOrder.query.order_by(ShopOrder.id.desc()).limit(100).all():
        rows.append(_payment_row(
            "SHOP", order.id, order.user_id, order.total_amount, order.code, order.created_at, order.status,
        ))
    return jsonify(sorted(rows, key=lambda row: row["created_at"] or "", reverse=True)[:200])


def _approve_payment(kind, item_id, approved):
    if kind == "BOOKING":
        payment = db.session.get(Payment, item_id)
        if not payment or payment.status != "PENDING":
            raise ApiError("Giao dịch không tồn tại hoặc đã được xử lý.", 404)
        payment.status = "PAID" if approved else "REJECTED"
        payment.paid_at = utc_now() if approved else None
        payment.booking.status = "PAID" if approved else "CANCELLED"
        if not approved:
            BookingSeat.query.filter_by(booking_id=payment.booking_id).delete()
    elif kind == "MEMBERSHIP":
        purchase = db.session.get(Membership, item_id)
        if not purchase or purchase.status != "PENDING":
            raise ApiError("Giao dịch không tồn tại hoặc đã được xử lý.", 404)
        if approved:
            active = _profile_membership(purchase.user_id)
            now = utc_now()
            purchase.starts_at = max(now, active.expires_at if active else now)
            purchase.expires_at = purchase.starts_at + timedelta(days=30)
            purchase.status = "SCHEDULED" if purchase.starts_at > now else "ACTIVE"
        else:
            purchase.status = "REJECTED"
    elif kind == "SHOP":
        order = db.session.get(ShopOrder, item_id)
        if not order or order.status != "PENDING":
            raise ApiError("Giao dịch không tồn tại hoặc đã được xử lý.", 404)
        order.status = "READY_FOR_PICKUP" if approved else "REJECTED"
        if not approved:
            for item in order.items:
                item.product.stock_quantity += item.quantity
    else:
        raise ApiError("Loại giao dịch không hợp lệ.")


@bp.post("/admin/approve")
@roles_required(*STAFF_ROLES)
def approve_payments():
    data = json_body()
    items = data.get("items")
    approved = data.get("approved", True)
    if not isinstance(approved, bool) or not isinstance(items, list) or not items or len(items) > 100:
        raise ApiError("Danh sách xác nhận không hợp lệ.")
    for item in items:
        if not isinstance(item, dict):
            raise ApiError("Giao dịch không hợp lệ.")
        item_id = clean_int(item.get("id"), "giao dịch", lo=1)
        kind = clean_str(item.get("kind"), "loại giao dịch", max_len=20, required=True).upper()
        _approve_payment(kind, item_id, approved)
    log_activity(g.current_user.id, "PAYMENTS_REVIEWED", f"{len(items)} giao dịch")
    db.session.commit()
    return jsonify({"updated": len(items), "approved": approved})


@bp.get("/trust")
@auth_required
def my_trust():
    trust = db.session.get(UserTrust, g.current_user.id)
    return jsonify(trust.to_dict() if trust else {
        "score": 100, "expired_holds": 0, "penalties": 0, "blocked_until": None,
    })
