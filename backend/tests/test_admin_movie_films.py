from datetime import timedelta
from io import BytesIO

from app.extensions import db
from app.models import Membership, Movie, Room, Showtime, User
from app.timeutil import local_now, utc_now


def _feature_film_bytes():
    return b"\x00\x00\x00\x18ftypisom" + b"feature-film-test"


def test_admin_uploads_film_and_active_member_can_watch_after_theatrical_run(
    client, auth, app, tmp_path
):
    app.config["FEATURE_FILM_UPLOAD_DIR"] = tmp_path / "films"
    created = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim kiểm thử xem trực tuyến",
        "status": "coming_soon",
    })
    assert created.status_code == 201
    movie_id = created.get_json()["id"]
    video = _feature_film_bytes()

    unauthorized = client.post(
        f"/api/admin/movies/{movie_id}/film",
        headers=auth("manager"),
        data={"film": (BytesIO(video), "feature.mp4")},
        content_type="multipart/form-data",
    )
    assert unauthorized.status_code == 403

    uploaded = client.post(
        f"/api/admin/movies/{movie_id}/film",
        headers=auth("admin"),
        data={"film": (BytesIO(video), "feature.mp4")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    film_url = uploaded.get_json()["film_url"]
    assert film_url.startswith(f"/api/movies/{movie_id}/film?format=mp4")
    assert client.get("/api/movies/watch").get_json() == []
    assert client.get(film_url).status_code == 404
    admin_movie = next(
        movie for movie in client.get("/api/admin/movies", headers=auth("admin")).get_json()
        if movie["id"] == movie_id
    )
    assert admin_movie["watch_ready"] is False

    with app.app_context():
        movie = db.session.get(Movie, movie_id)
        movie.status = "now_showing"
        db.session.add(Showtime(
            movie_id=movie_id,
            room_id=Room.query.first().id,
            start_time=local_now() - timedelta(days=1),
            base_price=90000,
        ))
        db.session.commit()

    watch_list = client.get("/api/movies/watch")
    assert watch_list.status_code == 200
    assert [movie["id"] for movie in watch_list.get_json()] == [movie_id]
    public_movie = client.get(f"/api/movies/watch/{movie_id}")
    assert public_movie.status_code == 200
    assert public_movie.get_json()["can_watch"] is False
    assert public_movie.get_json()["film_url"] is None
    assert client.get(film_url).status_code == 403
    admin_movie = next(
        movie for movie in client.get("/api/admin/movies", headers=auth("admin")).get_json()
        if movie["id"] == movie_id
    )
    assert admin_movie["watch_ready"] is True

    with app.app_context():
        user = User.query.filter_by(email="user@cinevo.vn").first()
        db.session.add(Membership(
            user_id=user.id,
            tier="SILVER",
            starts_at=utc_now(),
            expires_at=utc_now() + timedelta(days=30),
            status="ACTIVE",
            amount=99000,
            payment_ref="MEM-WATCH-TEST",
        ))
        db.session.commit()

    member_movie = client.get(f"/api/movies/watch/{movie_id}", headers=auth("user")).get_json()
    assert member_movie["can_watch"] is True
    assert member_movie["film_url"] != film_url
    response = client.get(member_movie["film_url"], headers={"Range": "bytes=0-7"})
    assert response.status_code == 206
    assert response.data == video[:8]
    assert response.mimetype == "video/mp4"

    deleted = client.delete(f"/api/admin/movies/{movie_id}/film", headers=auth("admin"))
    assert deleted.status_code == 200
    assert deleted.get_json()["film_url"] is None
    assert client.get("/api/movies/watch").get_json() == []


def test_ended_movie_with_uploaded_film_is_watchable_even_if_future_showtime_remains(
    client, auth, app, tmp_path
):
    app.config["FEATURE_FILM_UPLOAD_DIR"] = tmp_path / "films"
    created = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim kết thúc công chiếu ngay",
        "status": "coming_soon",
    })
    movie_id = created.get_json()["id"]
    uploaded = client.post(
        f"/api/admin/movies/{movie_id}/film",
        headers=auth("admin"),
        data={"film": (BytesIO(_feature_film_bytes()), "feature.mp4")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200

    with app.app_context():
        db.session.add(Showtime(
            movie_id=movie_id,
            room_id=Room.query.first().id,
            start_time=local_now() + timedelta(days=1),
            base_price=90000,
        ))
        db.session.commit()

    ended = client.patch(
        f"/api/admin/movies/{movie_id}/status",
        headers=auth("admin"),
        json={"status": "ended"},
    )
    assert ended.status_code == 200
    assert ended.get_json()["theatrical_end_date"] == local_now().date().isoformat()
    assert all(item["id"] != movie_id for item in client.get(
        "/api/showtimes", query_string={"movie_id": movie_id}).get_json())
    assert [item["id"] for item in client.get("/api/movies/watch").get_json()] == [movie_id]
    assert client.get(f"/api/movies/watch/{movie_id}").status_code == 200
    admin_movie = next(
        item for item in client.get("/api/admin/movies", headers=auth("admin")).get_json()
        if item["id"] == movie_id
    )
    assert admin_movie["watch_ready"] is True


def test_movie_watch_details_are_saved_shown_and_end_date_gates_watch_list(
    client, auth, app, tmp_path
):
    app.config["FEATURE_FILM_UPLOAD_DIR"] = tmp_path / "films"
    created = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim có thông tin trực tuyến",
    })
    movie_id = created.get_json()["id"]
    uploaded = client.post(
        f"/api/admin/movies/{movie_id}/film",
        headers=auth("admin"),
        data={"film": (BytesIO(_feature_film_bytes()), "feature.mp4")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200

    with app.app_context():
        movie = db.session.get(Movie, movie_id)
        movie.status = "now_showing"
        db.session.add(Showtime(
            movie_id=movie_id,
            room_id=Room.query.first().id,
            start_time=local_now() - timedelta(days=2),
            base_price=90000,
        ))
        db.session.commit()

    future_end_date = (local_now().date() + timedelta(days=2)).isoformat()
    details = {
        "description": "Mô tả đầy đủ của phim.",
        "director": "Đạo diễn kiểm thử",
        "release_date": "2026-01-10",
        "theatrical_end_date": future_end_date,
        "duration_minutes": 123,
    }
    saved = client.patch(
        f"/api/admin/movies/{movie_id}/watch-details",
        headers=auth("admin"),
        json=details,
    )
    assert saved.status_code == 200
    assert saved.get_json()["description"] == details["description"]
    assert saved.get_json()["director"] == details["director"]
    assert saved.get_json()["theatrical_end_date"] == future_end_date
    assert saved.get_json()["duration_minutes"] == 123
    assert all(item["id"] != movie_id for item in client.get("/api/movies/watch").get_json())
    admin_movie = next(
        item for item in client.get("/api/admin/movies", headers=auth("admin")).get_json()
        if item["id"] == movie_id
    )
    assert admin_movie["watch_ready"] is False
    assert admin_movie["display_status"] == "Chưa có suất chiếu sắp tới"

    details["theatrical_end_date"] = (local_now().date() - timedelta(days=1)).isoformat()
    saved = client.patch(
        f"/api/admin/movies/{movie_id}/watch-details",
        headers=auth("admin"),
        json=details,
    )
    assert saved.status_code == 200
    watchable = client.get(f"/api/movies/watch/{movie_id}")
    assert watchable.status_code == 200
    assert watchable.get_json()["description"] == details["description"]
    assert watchable.get_json()["director"] == details["director"]
    assert watchable.get_json()["release_date"] == details["release_date"]
    assert watchable.get_json()["theatrical_end_date"] == details["theatrical_end_date"]
    assert watchable.get_json()["duration_minutes"] == 123

    details["theatrical_end_date"] = "2025-12-01"
    details["release_date"] = "2026-01-10"
    invalid = client.patch(
        f"/api/admin/movies/{movie_id}/watch-details",
        headers=auth("admin"),
        json=details,
    )
    assert invalid.status_code == 400


def test_film_upload_rejects_invalid_file_and_only_supports_video_formats(
    client, auth
):
    created = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim kiểm thử định dạng",
    })
    movie_id = created.get_json()["id"]

    for filename, content in (
        ("feature.mov", _feature_film_bytes()),
        ("feature.mp4", b"not-a-video"),
    ):
        response = client.post(
            f"/api/admin/movies/{movie_id}/film",
            headers=auth("admin"),
            data={"film": (BytesIO(content), filename)},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400


def test_admin_can_add_and_replace_film_artwork_for_member_watch_page(
    client, auth, app, tmp_path
):
    app.config["FEATURE_FILM_UPLOAD_DIR"] = tmp_path / "films"
    created = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim kiểm thử ảnh xem trực tuyến",
    })
    movie_id = created.get_json()["id"]
    film = _feature_film_bytes()
    uploaded_film = client.post(
        f"/api/admin/movies/{movie_id}/film",
        headers=auth("admin"),
        data={"film": (BytesIO(film), "feature.mp4")},
        content_type="multipart/form-data",
    )
    assert uploaded_film.status_code == 200

    png = b"\x89PNG\r\n\x1a\n" + b"small-test-image"
    image_response = client.post(
        f"/api/admin/movies/{movie_id}/film-image",
        headers=auth("admin"),
        data={"image": (BytesIO(png), "cover.png")},
        content_type="multipart/form-data",
    )
    assert image_response.status_code == 200
    first_image_url = image_response.get_json()["film_image_url"]
    assert first_image_url.startswith(f"/api/movies/{movie_id}/film-image?format=png")

    with app.app_context():
        movie = db.session.get(Movie, movie_id)
        movie.status = "now_showing"
        db.session.add(Showtime(
            movie_id=movie_id,
            room_id=Room.query.first().id,
            start_time=local_now() - timedelta(days=1),
            base_price=90000,
        ))
        db.session.commit()

    assert client.get(first_image_url).status_code == 403
    with app.app_context():
        user = User.query.filter_by(email="user@cinevo.vn").first()
        db.session.add(Membership(
            user_id=user.id,
            tier="SILVER",
            starts_at=utc_now(),
            expires_at=utc_now() + timedelta(days=30),
            status="ACTIVE",
            amount=99000,
            payment_ref="MEM-ARTWORK-TEST",
        ))
        db.session.commit()

    member_movie = client.get(
        f"/api/movies/watch/{movie_id}", headers=auth("user")
    ).get_json()
    member_image_url = member_movie["film_image_url"]
    image = client.get(member_image_url)
    assert image.status_code == 200
    assert image.data == png
    assert image.mimetype == "image/png"

    replacement = b"\xff\xd8\xffreplacement-image"
    replaced = client.post(
        f"/api/admin/movies/{movie_id}/film-image",
        headers=auth("admin"),
        data={"image": (BytesIO(replacement), "cover.jpg")},
        content_type="multipart/form-data",
    )
    assert replaced.status_code == 200
    second_image_url = replaced.get_json()["film_image_url"]
    assert client.get(member_image_url).status_code == 404
    assert client.get(second_image_url).status_code == 403
    latest_member_movie = client.get(
        f"/api/movies/watch/{movie_id}", headers=auth("user")
    ).get_json()
    response = client.get(latest_member_movie["film_image_url"])
    assert response.status_code == 200
    assert response.data == replacement
    assert response.mimetype == "image/jpeg"
