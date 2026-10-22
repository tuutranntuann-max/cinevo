from datetime import date, timedelta

from app.extensions import db
from app.models import Booking, Movie, MovieCancellation, Payment, Showtime
from app.timeutil import local_now


def test_admin_can_create_movie_and_make_it_available_in_public_catalog(client, auth):
    payload = {
        "title": "Phim mới Cinevo",
        "genre": "Khoa học viễn tưởng",
        "duration_minutes": 125,
        "age_rating": "T13",
        "rating": 8,
        "director": "Đạo diễn kiểm thử",
        "cast": "Diễn viên A, Diễn viên B",
        "release_date": "2026-12-01",
        "theatrical_end_date": "2027-01-15",
        "description": "Phim vừa được thêm từ bảng quản trị.",
        "status": "coming_soon",
    }
    assert client.post("/api/admin/movies", json=payload).status_code == 401
    created = client.post("/api/admin/movies", headers=auth("admin"), json=payload)
    assert created.status_code == 201
    movie_id = created.get_json()["id"]
    assert created.get_json()["cast"] == payload["cast"]
    assert created.get_json()["theatrical_end_date"] == payload["theatrical_end_date"]
    assert any(movie["id"] == movie_id for movie in client.get(
        "/api/admin/movies", headers=auth("admin")).get_json())
    public_movie = client.get(f"/api/movies/{movie_id}")
    assert public_movie.status_code == 200
    assert public_movie.get_json()["title"] == payload["title"]


def test_admin_can_edit_movie_metadata_and_premiere_status(client, auth):
    headers = auth("admin")
    created = client.post("/api/admin/movies", headers=headers, json={
        "title": "Phim cần cập nhật",
        "status": "coming_soon",
        "theatrical_end_date": "2027-02-15",
    })
    movie_id = created.get_json()["id"]
    payload = {
        "title": "Phim đã cập nhật",
        "genre": "Tâm lý",
        "duration_minutes": 132,
        "age_rating": "T16",
        "rating": 8.7,
        "director": "Tác giả kiểm thử",
        "cast": "Diễn viên kiểm thử, Nghệ sĩ thử nghiệm",
        "release_date": "2027-01-20",
        "description": "Nội dung phim sau khi chỉnh sửa.",
        "status": "now_showing",
    }

    assert client.patch(
        f"/api/admin/movies/{movie_id}/details",
        headers=auth("manager"),
        json=payload,
    ).status_code == 403
    response = client.patch(
        f"/api/admin/movies/{movie_id}/details",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    movie = response.get_json()
    assert movie["title"] == payload["title"]
    assert movie["genre"] == payload["genre"]
    assert movie["duration_minutes"] == payload["duration_minutes"]
    assert movie["age_rating"] == payload["age_rating"]
    assert movie["rating"] == payload["rating"]
    assert movie["director"] == payload["director"]
    assert movie["cast"] == payload["cast"]
    assert movie["release_date"] == payload["release_date"]
    assert movie["theatrical_end_date"] == "2027-02-15"
    assert movie["description"] == payload["description"]
    assert movie["status"] == payload["status"]


def test_restarting_premiere_clears_expired_end_date_and_reports_missing_schedule(client, auth):
    headers = auth("admin")
    created = client.post("/api/admin/movies", headers=headers, json={
        "title": "Phim bật lại công chiếu",
        "status": "coming_soon",
    })
    movie_id = created.get_json()["id"]

    ended = client.patch(
        f"/api/admin/movies/{movie_id}/status",
        headers=headers,
        json={"status": "ended"},
    )
    assert ended.status_code == 200
    assert ended.get_json()["theatrical_end_date"] == local_now().date().isoformat()

    restarted = client.patch(
        f"/api/admin/movies/{movie_id}/status",
        headers=headers,
        json={"status": "now_showing"},
    )
    assert restarted.status_code == 200
    assert restarted.get_json()["theatrical_end_date"] is None

    admin_movie = next(
        movie for movie in client.get("/api/admin/movies", headers=headers).get_json()
        if movie["id"] == movie_id
    )
    assert admin_movie["expired"] is False
    assert admin_movie["has_future_showtime"] is False
    assert admin_movie["display_status"] == "Chưa có suất chiếu sắp tới"
    assert movie_id not in [
        movie["id"] for movie in client.get("/api/movies?status=now_showing").get_json()
    ]


def test_adding_future_showtime_makes_restarted_movie_visible_to_customers(client, auth):
    headers = auth("admin")
    movie = client.post("/api/admin/movies", headers=headers, json={
        "title": "Phim chờ lịch chiếu",
        "status": "now_showing",
    }).get_json()
    cinema = client.get("/api/admin/cinemas", headers=headers).get_json()[0]
    room = next(
        room for room in client.get("/api/admin/rooms", headers=headers).get_json()
        if room["cinema_id"] == cinema["id"]
    )
    start_time = (local_now() + timedelta(days=10)).replace(
        hour=10, minute=0, second=0, microsecond=0,
    )
    scheduled = client.post("/api/admin/showtimes", headers=headers, json={
        "movie_id": movie["id"],
        "cinema_id": cinema["id"],
        "room_id": room["id"],
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
        "base_price": 90000,
    })

    assert scheduled.status_code == 201
    public_movies = client.get("/api/movies?status=now_showing").get_json()
    assert movie["id"] in [item["id"] for item in public_movies]
    admin_movie = next(
        item for item in client.get("/api/admin/movies", headers=headers).get_json()
        if item["id"] == movie["id"]
    )
    assert admin_movie["has_future_showtime"] is True
    assert admin_movie["display_status"] == "Đang chiếu"


def test_movie_metadata_edit_rejects_invalid_values_and_duplicate_title(client, auth, app):
    headers = auth("admin")
    existing = client.get("/api/admin/movies", headers=headers).get_json()[0]
    created = client.post("/api/admin/movies", headers=headers, json={
        "title": "Phim hợp lệ để sửa",
        "status": "coming_soon",
    })
    movie_id = created.get_json()["id"]
    payload = {
        "title": "Phim mới hợp lệ",
        "duration_minutes": 120,
        "age_rating": "T99",
        "rating": 7.5,
        "status": "coming_soon",
    }

    invalid_age = client.patch(
        f"/api/admin/movies/{movie_id}/details", headers=headers, json=payload,
    )
    assert invalid_age.status_code == 400

    payload["age_rating"] = "T13"
    payload["title"] = existing["title"]
    duplicate = client.patch(
        f"/api/admin/movies/{movie_id}/details", headers=headers, json=payload,
    )
    assert duplicate.status_code == 409

    payload["title"] = "Tên khác hợp lệ"
    payload["release_date"] = "2028-01-01"
    payload["theatrical_end_date"] = "2027-12-31"
    with app.app_context():
        movie = db.session.get(Movie, movie_id)
        movie.theatrical_end_date = date(2027, 12, 31)
        db.session.commit()
    invalid_dates = client.patch(
        f"/api/admin/movies/{movie_id}/details", headers=headers, json=payload,
    )
    assert invalid_dates.status_code == 400


def test_admin_can_cancel_and_restore_movie(client, auth):
    headers = auth("admin")
    movie = client.get("/api/admin/movies", headers=headers).get_json()[0]
    movie_id = movie["id"]

    assert client.patch(f"/api/admin/movies/{movie_id}/cancellation",
                        headers=auth("manager"), json={"cancelled": True}).status_code == 403
    cancelled = client.patch(f"/api/admin/movies/{movie_id}/cancellation",
                             headers=headers, json={"cancelled": True})
    assert cancelled.status_code == 200
    assert cancelled.get_json()["cancelled"] is True
    assert client.get("/api/movies", query_string={"q": movie["title"]}).get_json() == []
    assert client.get(f"/api/movies/{movie_id}").status_code == 404
    assert client.get(f"/api/showtimes?movie_id={movie_id}").get_json() == []

    admin_movie = next(item for item in client.get("/api/admin/movies", headers=headers).get_json()
                       if item["id"] == movie_id)
    assert admin_movie["cancelled"] is True
    assert admin_movie["display_status"] == "Đã hủy"

    restored = client.patch(f"/api/admin/movies/{movie_id}/cancellation",
                            headers=headers, json={"cancelled": False})
    assert restored.status_code == 200
    assert client.get(f"/api/movies/{movie_id}").status_code == 200


def test_cancellation_does_not_delete_existing_booking_history(client, auth, app):
    headers = auth("admin")
    with app.app_context():
        showtime = Showtime.query.filter(Showtime.start_time >= local_now()).first()
        movie_id, showtime_id = showtime.movie_id, showtime.id
        from app.models import Booking
        booking = Booking(code="CVKEEPHISTORY", user_id=1, showtime_id=showtime_id)
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    assert client.patch(f"/api/admin/movies/{movie_id}/cancellation",
                        headers=headers, json={"cancelled": True}).status_code == 200
    with app.app_context():
        from app.models import Booking
        assert db.session.get(Booking, booking_id) is not None


def test_cancelled_showtime_cannot_be_booked(client, auth, app):
    headers = auth("admin")
    with app.app_context():
        showtime = Showtime.query.filter(Showtime.start_time >= local_now()).first()
        movie_id, showtime_id = showtime.movie_id, showtime.id
        seat_id = showtime.room.seats[0].id

    assert client.patch(f"/api/admin/movies/{movie_id}/cancellation",
                        headers=headers, json={"cancelled": True}).status_code == 200
    response = client.post("/api/bookings", headers=auth("user"), json={
        "showtime_id": showtime_id, "seat_ids": [seat_id], "foods": [], "payment_method": "QR",
    })
    assert response.status_code == 409
    assert response.get_json()["code"] == "MOVIE_CANCELLED"


def test_admin_can_end_premiere_immediately_and_prevent_new_bookings(client, auth, app):
    headers = auth("admin")
    with app.app_context():
        showtime = Showtime.query.filter(Showtime.start_time >= local_now()).first()
        movie_id, showtime_id = showtime.movie_id, showtime.id
        seat_id = showtime.room.seats[0].id

    ended = client.patch(
        f"/api/admin/movies/{movie_id}/status",
        headers=headers,
        json={"status": "ended"},
    )

    assert ended.status_code == 200
    assert ended.get_json()["status"] == "ended"
    assert ended.get_json()["theatrical_end_date"] == local_now().date().isoformat()
    assert all(movie["id"] != movie_id for movie in client.get("/api/movies").get_json())
    assert all(showtime["id"] != showtime_id for showtime in client.get(
        "/api/showtimes", query_string={"movie_id": movie_id}).get_json())
    assert client.get(f"/api/showtimes/{showtime_id}/seats").status_code == 404

    booking = client.post("/api/bookings", headers=auth("user"), json={
        "showtime_id": showtime_id,
        "seat_ids": [seat_id],
        "foods": [],
        "payment_method": "QR",
    })
    assert booking.status_code == 409
    assert booking.get_json()["code"] == "MOVIE_ENDED"
    listed = next(movie for movie in client.get("/api/admin/movies", headers=headers).get_json()
                  if movie["id"] == movie_id)
    assert listed["display_status"] == "Đã kết thúc công chiếu"


def test_now_showing_movie_without_future_showtimes_is_hidden_as_missing_schedule(client, auth, app):
    with app.app_context():
        movie = Movie.query.filter_by(status="now_showing").first()
        movie_id = movie.id
        for showtime in Showtime.query.filter_by(movie_id=movie_id).all():
            showtime.start_time = local_now() - timedelta(days=1)
        db.session.commit()

    assert client.get(f"/api/movies/{movie_id}").status_code == 404
    assert all(movie["id"] != movie_id for movie in client.get(
        "/api/movies", query_string={"status": "now_showing"}).get_json())
    admin_movie = next(movie for movie in client.get(
        "/api/admin/movies", headers=auth("admin")).get_json() if movie["id"] == movie_id)
    assert admin_movie["expired"] is False
    assert admin_movie["has_future_showtime"] is False
    assert admin_movie["display_status"] == "Chưa có suất chiếu sắp tới"


def test_cancellation_requires_boolean_value(client, auth):
    response = client.patch("/api/admin/movies/1/cancellation", headers=auth("admin"),
                            json={"cancelled": "yes"})
    assert response.status_code == 400


def test_movie_delete_requires_cancellation_and_removes_cancelled_bookings(client, auth, app):
    headers = auth("admin")
    with app.app_context():
        showtime = Showtime.query.filter(Showtime.start_time >= local_now()).first()
        movie_id, showtime_id = showtime.movie_id, showtime.id
        booking = Booking(
            code="CANCELLED-DELETE",
            user_id=1,
            showtime_id=showtime_id,
            status="CANCELLED",
        )
        db.session.add(booking)
        db.session.flush()
        payment = Payment(
            booking_id=booking.id,
            method="QR",
            amount=90000,
            status="CANCELLED",
        )
        db.session.add(payment)
        db.session.commit()
        booking_id, payment_id = booking.id, payment.id

    listed = next(
        movie for movie in client.get("/api/admin/movies", headers=headers).get_json()
        if movie["id"] == movie_id
    )
    assert listed["booking_count"] == 1
    assert listed["cancelled_booking_count"] == 1
    assert listed["delete_allowed"] is True
    assert client.delete(f"/api/admin/movies/{movie_id}").status_code == 401

    deleted = client.delete(f"/api/admin/movies/{movie_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.get_json()["deleted_booking_count"] == 1
    with app.app_context():
        assert db.session.get(Movie, movie_id) is None
        assert db.session.get(Showtime, showtime_id) is None
        assert db.session.get(Booking, booking_id) is None
        assert db.session.get(Payment, payment_id) is None


def test_movie_delete_blocks_active_tickets_even_when_movie_is_cancelled(client, auth, app):
    headers = auth("admin")
    with app.app_context():
        showtime = Showtime.query.filter(Showtime.start_time >= local_now()).first()
        movie_id = showtime.movie_id
        booking = Booking(
            code="ACTIVE-DELETE",
            user_id=1,
            showtime_id=showtime.id,
            status="PAID",
        )
        db.session.add(booking)
        db.session.commit()
        booking_id = booking.id

    assert client.patch(
        f"/api/admin/movies/{movie_id}/cancellation",
        headers=headers,
        json={"cancelled": True},
    ).status_code == 200
    deleted = client.delete(f"/api/admin/movies/{movie_id}", headers=headers)
    assert deleted.status_code == 409
    with app.app_context():
        assert db.session.get(Movie, movie_id) is not None
        assert db.session.get(Booking, booking_id).status == "PAID"


def test_cancelled_movie_without_bookings_can_be_deleted(client, auth, app):
    headers = auth("admin")
    created = client.post("/api/admin/movies", headers=headers, json={
        "title": "Phim hủy để xóa",
        "status": "coming_soon",
    })
    assert created.status_code == 201
    movie_id = created.get_json()["id"]

    blocked = client.delete(f"/api/admin/movies/{movie_id}", headers=headers)
    assert blocked.status_code == 409

    cancelled = client.patch(
        f"/api/admin/movies/{movie_id}/cancellation",
        headers=headers,
        json={"cancelled": True},
    )
    assert cancelled.status_code == 200
    deleted = client.delete(f"/api/admin/movies/{movie_id}", headers=headers)
    assert deleted.status_code == 200
    with app.app_context():
        assert db.session.get(Movie, movie_id) is None
