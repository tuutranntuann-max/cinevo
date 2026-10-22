from app.extensions import db
from app.models import CommerceSettings


def test_manager_configures_and_customer_books_double_seats(client, auth, seat_info, app):
    showtime_id, _ = seat_info
    room_seats = client.get(f"/api/showtimes/{showtime_id}/seats").get_json()["seats"]
    pair = next(
        (left, right)
        for left in room_seats
        for right in room_seats
        if left["row"] == right["row"]
        and left["number"] % 2 == 1
        and right["number"] == left["number"] + 1
        and not left["booked"] and not right["booked"]
        and not left["held"] and not right["held"]
    )
    pair_ids = [seat["id"] for seat in pair]

    configured = client.patch(
        "/api/manager/seats/type",
        headers=auth("manager"),
        json={"seat_ids": pair_ids, "type": "DOUBLE"},
    )
    assert configured.status_code == 200
    assert [seat["type"] for seat in configured.get_json()["seats"]] == ["DOUBLE", "DOUBLE"]

    invalid_hold = client.post(
        "/api/commerce/seat-holds",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": pair_ids[:1]},
    )
    assert invalid_hold.status_code == 400
    assert invalid_hold.get_json()["code"] == "DOUBLE_SEAT_PAIR_REQUIRED"
    held = client.post(
        "/api/commerce/seat-holds",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": pair_ids},
    )
    assert held.status_code == 200
    assert len(held.get_json()["holds"]) == 2

    with app.app_context():
        settings = db.session.get(CommerceSettings, 1)
        if settings is None:
            settings = CommerceSettings(id=1, values={})
            db.session.add(settings)
        settings.values = {
            "bank_name": "MBBank",
            "bank_bin": "970422",
            "account_number": "123456789",
            "qr_image_url": "/api/content/media/test-qr.png",
            "membership_prices": {},
        }
        db.session.commit()

    incomplete_booking = client.post(
        "/api/bookings",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": pair_ids[:1], "payment_method": "QR"},
    )
    assert incomplete_booking.status_code == 400
    assert incomplete_booking.get_json()["code"] == "DOUBLE_SEAT_PAIR_REQUIRED"

    booked = client.post(
        "/api/bookings",
        headers=auth("user"),
        json={"showtime_id": showtime_id, "seat_ids": pair_ids, "payment_method": "QR"},
    )
    assert booked.status_code == 201
    assert len(booked.get_json()["seats"]) == 2
    assert booked.get_json()["seat_amount"] == sum(seat["price"] for seat in pair)


def test_double_seat_configuration_requires_adjacent_pairs(client, auth, seat_info):
    showtime_id, _ = seat_info
    seats = client.get(f"/api/showtimes/{showtime_id}/seats").get_json()["seats"]
    row = seats[0]["row"]
    row_seats = [seat for seat in seats if seat["row"] == row]
    invalid_pair = [row_seats[0]["id"], row_seats[2]["id"]]
    response = client.patch(
        "/api/manager/seats/type",
        headers=auth("manager"),
        json={"seat_ids": invalid_pair, "type": "DOUBLE"},
    )
    assert response.status_code == 400


def test_only_managers_and_admins_can_configure_double_seats(client, auth):
    assert client.patch(
        "/api/manager/seats/type",
        headers=auth("user"),
        json={"seat_ids": [1, 2], "type": "DOUBLE"},
    ).status_code == 403
