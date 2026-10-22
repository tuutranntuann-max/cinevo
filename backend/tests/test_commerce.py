"""Kiểm thử gói thành viên, duyệt thanh toán, shop và uy tín giữ ghế."""
from datetime import timedelta

from app.extensions import db
from app.models import Booking, CommerceSettings, Membership, Payment, Product, SeatHold, Showtime, User
from app.models.seat_hold import SEAT_HOLD_DURATION
from app.timeutil import utc_now


def _hold_and_book(client, auth, showtime_id, seat_id, foods=None):
    with client.application.app_context():
        settings = db.session.get(CommerceSettings, 1)
        if settings is None:
            settings = CommerceSettings(id=1, values={})
            db.session.add(settings)
        settings.values = {
            "bank_name": "Ngân hàng kiểm thử",
            "bank_bin": "970000",
            "account_number": "123456789",
            "account_name": "CINEVO",
            "qr_image_url": "/api/content/media/test-qr.png",
            "membership_prices": {"SILVER": 99000, "GOLD": 199000, "DIAMOND": 399000},
        }
        db.session.commit()
    hold = client.post(
        "/api/commerce/seat-holds",
        headers=auth,
        json={"showtime_id": showtime_id, "seat_ids": [seat_id]},
    )
    assert hold.status_code == 200
    return client.post(
        "/api/bookings",
        headers=auth,
        json={"showtime_id": showtime_id, "seat_ids": [seat_id], "foods": foods or [], "payment_method": "QR"},
    )


def test_checkout_is_blocked_until_bank_account_is_configured(client, auth, seat_info):
    showtime_id, seats = seat_info
    held = client.post(
        "/api/commerce/seat-holds",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": [seats[0]["id"]]},
    )
    assert held.status_code == 200
    response = client.post(
        "/api/bookings",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": [seats[0]["id"]], "payment_method": "QR"},
    )
    assert response.status_code == 503
    assert response.get_json()["code"] == "PAYMENT_NOT_CONFIGURED"


def test_seat_hold_duration_is_ten_minutes(client, auth, seat_info, app):
    showtime_id, seats = seat_info
    before = utc_now()
    response = client.post(
        "/api/commerce/seat-holds",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": [seats[0]["id"]]},
    )
    assert response.status_code == 200
    with app.app_context():
        expires_at = SeatHold.query.filter_by(showtime_id=showtime_id).one().expires_at
    assert SEAT_HOLD_DURATION == timedelta(minutes=10)
    assert before + SEAT_HOLD_DURATION <= expires_at <= utc_now() + SEAT_HOLD_DURATION


def test_vietqr_checkout_does_not_require_uploaded_qr(client, auth, seat_info, app):
    showtime_id, seats = seat_info
    with app.app_context():
        settings = db.session.get(CommerceSettings, 1)
        if settings is None:
            settings = CommerceSettings(id=1, values={})
            db.session.add(settings)
        settings.values = {
            "bank_name": "MBBank",
            "bank_bin": "970422",
            "account_number": "123456789",
            "account_name": "CINEVO",
            "qr_image_url": "",
        }
        db.session.commit()

    hold = client.post(
        "/api/commerce/seat-holds",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": [seats[0]["id"]]},
    )
    assert hold.status_code == 200
    booking = client.post(
        "/api/bookings",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": [seats[0]["id"]], "payment_method": "QR"},
    )
    assert booking.status_code == 201


def test_qr_booking_requires_staff_approval(client, auth, seat_info):
    showtime_id, seats = seat_info
    created = _hold_and_book(client, auth("user"), showtime_id, seats[0]["id"])
    assert created.status_code == 201
    booking = created.get_json()
    assert booking["status"] == "PENDING"
    assert booking["payment"]["status"] == "PENDING"
    assert booking["payment"]["transaction_ref"] == booking["code"]

    pending = client.get("/api/commerce/admin/pending", headers=auth("manager")).get_json()
    assert any(row["kind"] == "BOOKING" and row["transaction_ref"] == booking["code"] for row in pending)
    confirmed = client.post(
        "/api/commerce/admin/approve",
        headers=auth("manager"),
        json={"items": [{"kind": "BOOKING", "id": booking["payment"]["id"]}]},
    )
    assert confirmed.status_code == 200
    result = client.get(f"/api/bookings/{booking['code']}", headers=auth("user")).get_json()
    assert result["status"] == "PAID"
    assert result["payment"]["status"] == "PAID"


def test_admin_configured_membership_activates_after_approval(client, auth):
    updated = client.patch(
        "/api/commerce/admin/settings",
        headers=auth("admin"),
        json={
            "bank_name": "Ngân hàng Demo",
            "bank_bin": "970000",
            "account_number": "123456789",
            "account_name": "CINEVO",
            "qr_image_url": "/api/content/media/test-qr.png",
            "membership_prices": {"SILVER": 19001, "GOLD": 50001, "DIAMOND": 120001},
        },
    )
    assert updated.status_code == 200
    plans = client.get("/api/commerce/membership/plans").get_json()
    assert next(plan for plan in plans if plan["code"] == "SILVER")["price"] == 19001
    assert client.get("/api/commerce/settings").get_json()["account_number"] == "123456789"

    purchase = client.post(
        "/api/commerce/membership/purchases",
        headers=auth("user"),
        json={"tier": "SILVER"},
    )
    assert purchase.status_code == 201
    data = purchase.get_json()
    assert data["membership"]["status"] == "PENDING"
    assert data["payment_ref"] == data["membership"]["payment_ref"]
    pending = client.get("/api/commerce/admin/pending", headers=auth("manager")).get_json()
    assert any(row["kind"] == "MEMBERSHIP" and row["transaction_ref"] == data["payment_ref"] for row in pending)

    approved = client.post(
        "/api/commerce/admin/approve",
        headers=auth("manager"),
        json={"items": [{"kind": "MEMBERSHIP", "id": data["membership"]["id"]}]},
    )
    assert approved.status_code == 200
    active = client.get("/api/commerce/membership/mine", headers=auth("user")).get_json()["active"]
    assert active["tier"] == "SILVER" and active["status"] == "ACTIVE"


def test_admin_rejects_invalid_bank_bin(client, auth):
    response = client.patch(
        "/api/commerce/admin/settings",
        headers=auth("admin"),
        json={"bank_bin": "not-a-bin"},
    )
    assert response.status_code == 400


def test_member_discounts_food_and_shop_and_stock_is_restored_on_rejection(app, client, auth, seat_info):
    showtime_id, seats = seat_info
    with app.app_context():
        user = User.query.filter_by(email="user@cinevo.vn").first()
        db.session.add(Membership(
            user_id=user.id,
            tier="SILVER",
            starts_at=utc_now(),
            expires_at=utc_now() + timedelta(days=30),
            status="ACTIVE",
            amount=99000,
            payment_ref="MEM-TEST-SILVER",
        ))
        db.session.commit()

    ticket_response = _hold_and_book(
        client,
        auth("user"),
        showtime_id,
        seats[0]["id"],
        [{"food_id": 2, "quantity": 1}],
    )
    assert ticket_response.status_code == 201
    ticket = ticket_response.get_json()
    assert ticket["food_amount"] == 89100

    product_response = client.post(
        "/api/admin/products",
        headers=auth("admin"),
        json={
            "name": "Kính 3D",
            "category": "Kính 3D",
            "description": "Kính xem phim 3D",
            "price": 100000,
            "stock_quantity": 5,
            "active": True,
        },
    )
    assert product_response.status_code == 201
    product_id = product_response.get_json()["id"]
    order_response = client.post(
        "/api/commerce/shop/orders",
        headers=auth("user"),
        json={"pickup_cinema_id": 1, "items": [{"product_id": product_id, "quantity": 2}]},
    )
    assert order_response.status_code == 201
    order = order_response.get_json()
    assert order["subtotal"] == 200000
    assert order["discount_amount"] == 30000
    with app.app_context():
        assert db.session.get(Product, product_id).stock_quantity == 3
    rejected = client.post(
        "/api/commerce/admin/approve",
        headers=auth("manager"),
        json={"approved": False, "items": [{"kind": "SHOP", "id": order["id"]}]},
    )
    assert rejected.status_code == 200
    with app.app_context():
        assert db.session.get(Product, product_id).stock_quantity == 5

    order_response = client.post(
        "/api/commerce/shop/orders",
        headers=auth("user"),
        json={"pickup_cinema_id": 1, "items": [{"product_id": product_id, "quantity": 1}]},
    )
    order = order_response.get_json()
    paid = client.post(
        "/api/commerce/admin/approve",
        headers=auth("manager"),
        json={"items": [{"kind": "SHOP", "id": order["id"]}]},
    )
    assert paid.status_code == 200
    collected = client.patch(
        f"/api/commerce/admin/shop/orders/{order['id']}",
        headers=auth("manager"),
        json={"status": "COLLECTED"},
    )
    assert collected.status_code == 200
    assert collected.get_json()["status"] == "COLLECTED"


def test_staff_can_manage_shop_inventory_but_customers_cannot(client, auth):
    assert client.get("/api/manager/products", headers=auth("user")).status_code == 403
    created = client.post(
        "/api/manager/products",
        headers=auth("manager"),
        json={"name": "Dụng cụ", "category": "Vật tư", "price": 1000, "stock_quantity": 4, "active": True},
    )
    assert created.status_code == 201
    product_id = created.get_json()["id"]
    updated = client.put(
        f"/api/manager/products/{product_id}",
        headers=auth("manager"),
        json={"stock_quantity": 7},
    )
    assert updated.status_code == 200
    assert updated.get_json()["stock_quantity"] == 7


def test_three_expired_hold_cycles_reduce_reputation(client, auth, seat_info):
    showtime_id, seats = seat_info
    for _ in range(3):
        held = client.post(
            "/api/commerce/seat-holds",
            headers=auth("user"),
            json={"showtime_id": showtime_id, "seat_ids": [seats[0]["id"]]},
        )
        assert held.status_code == 200
        with client.application.app_context():
            reservation = SeatHold.query.filter_by(showtime_id=showtime_id).first()
            reservation.expires_at = utc_now() - timedelta(seconds=1)
            db.session.commit()
        assert client.get(f"/api/commerce/seat-holds/{showtime_id}").status_code == 200

    trust = client.get("/api/commerce/trust", headers=auth("user")).get_json()
    assert trust["expired_holds"] == 3
    assert trust["penalties"] == 1
    assert trust["score"] == 99


def test_nine_expired_hold_cycles_block_new_reservations(client, auth, seat_info):
    showtime_id, seats = seat_info
    for _ in range(9):
        held = client.post(
            "/api/commerce/seat-holds",
            headers=auth("user"),
            json={"showtime_id": showtime_id, "seat_ids": [seats[0]["id"]]},
        )
        assert held.status_code == 200
        with client.application.app_context():
            reservation = SeatHold.query.filter_by(showtime_id=showtime_id).first()
            reservation.expires_at = utc_now() - timedelta(seconds=1)
            db.session.commit()
        client.get(f"/api/commerce/seat-holds/{showtime_id}")

    trust = client.get("/api/commerce/trust", headers=auth("user")).get_json()
    assert trust["penalties"] == 3
    assert trust["score"] == 97
    assert trust["blocked_until"] is not None
    blocked = client.post(
        "/api/commerce/seat-holds",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": [seats[1]["id"]]},
    )
    assert blocked.status_code == 429
    assert blocked.get_json()["code"] == "TRUST_BLOCKED"


def test_silver_daily_limit_is_enforced_by_distinct_showtimes(app, client, auth, seat_info):
    showtime_id, seats = seat_info
    with app.app_context():
        user = User.query.filter_by(email="user@cinevo.vn").first()
        target = db.session.get(Showtime, showtime_id)
        showtimes = Showtime.query.filter(
            Showtime.start_time >= target.start_time.replace(hour=0, minute=0, second=0, microsecond=0),
            Showtime.start_time < target.start_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
        ).limit(5).all()
        assert len(showtimes) == 5
        db.session.add(Membership(
            user_id=user.id,
            tier="SILVER",
            starts_at=utc_now(),
            expires_at=utc_now() + timedelta(days=30),
            status="ACTIVE",
            amount=99000,
            payment_ref="MEM-DAILY-LIMIT",
        ))
        for index, showtime in enumerate(showtimes):
            db.session.add(Booking(
                user_id=user.id,
                showtime_id=showtime.id,
                code=f"DAILY-{index}",
                status="PAID",
                total_amount=90000,
            ))
        db.session.commit()
    response = _hold_and_book(client, auth("user"), showtime_id, seats[0]["id"])
    assert response.status_code == 409
    assert response.get_json()["code"] == "MEMBERSHIP_DAILY_LIMIT"


def test_pending_booking_expires_and_releases_seats(app, client, auth, seat_info):
    showtime_id, seats = seat_info
    created = _hold_and_book(client, auth("user"), showtime_id, seats[0]["id"]).get_json()
    with app.app_context():
        payment_id = created["payment"]["id"]
        payment = db.session.get(Payment, payment_id)
        payment.booking.created_at = utc_now() - timedelta(minutes=9)
        db.session.commit()
    detail_response = client.get(f"/api/bookings/{created['code']}", headers=auth("user"))
    detail = detail_response.get_json()
    assert detail["status"] == "PENDING"
    assert detail["hold_expires_at"] is not None
    with app.app_context():
        payment = db.session.get(Payment, payment_id)
        payment.booking.created_at = utc_now() - timedelta(minutes=11)
        db.session.commit()
    detail = client.get(f"/api/bookings/{created['code']}", headers=auth("user")).get_json()
    assert detail["status"] == "CANCELLED"
    assert detail["hold_expires_at"] is None
    assert detail["payment"]["status"] == "EXPIRED"
    seat_map = client.get(f"/api/showtimes/{showtime_id}/seats").get_json()
    assert next(seat for seat in seat_map["seats"] if seat["id"] == seats[0]["id"])["booked"] is False
