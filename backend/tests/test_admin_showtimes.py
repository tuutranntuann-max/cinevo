from datetime import timedelta

import pytest

from app.extensions import db
from app.models import Booking, Movie, Room, Showtime
from app.timeutil import local_now


@pytest.mark.parametrize("url", ["/api/admin/showtimes", "/api/admin/cinemas", "/api/admin/rooms"])
def test_admin_showtime_support_endpoints_are_admin_only(client, auth, url):
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth("user")).status_code == 403
    assert client.get(url, headers=auth("manager")).status_code == 403
    assert client.get(url, headers=auth("admin")).status_code == 200


def test_admin_can_create_and_update_showtimes(client, auth):
    headers = auth("admin")
    movie = client.get("/api/admin/movies", headers=headers).get_json()[0]
    cinema = client.get("/api/admin/cinemas", headers=headers).get_json()[0]
    room = next(room for room in client.get("/api/admin/rooms", headers=headers).get_json()
                if room["cinema_id"] == cinema["id"])
    start_time = (local_now() + timedelta(days=10)).replace(second=0, microsecond=0)
    payload = {
        "movie_id": movie["id"],
        "cinema_id": cinema["id"],
        "room_id": room["id"],
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
        "base_price": 110000,
    }

    response = client.post("/api/admin/showtimes", headers=headers, json=payload)
    assert response.status_code == 201
    showtime_id = response.get_json()["id"]
    assert response.get_json()["base_price"] == 110000

    payload["base_price"] = 125000
    updated = client.put(f"/api/admin/showtimes/{showtime_id}", headers=headers, json=payload)
    assert updated.status_code == 200
    assert updated.get_json()["base_price"] == 125000
    assert any(row["id"] == showtime_id for row in client.get(
        "/api/admin/showtimes", headers=headers).get_json())


def test_admin_can_create_same_showtime_for_multiple_selected_rooms(client, auth):
    headers = auth("admin")
    movie = client.get("/api/admin/movies", headers=headers).get_json()[0]
    cinema = client.get("/api/admin/cinemas", headers=headers).get_json()[0]
    rooms = [
        room for room in client.get("/api/admin/rooms", headers=headers).get_json()
        if room["cinema_id"] == cinema["id"]
    ][:2]
    start_time = (local_now() + timedelta(days=10)).replace(
        hour=11, minute=0, second=0, microsecond=0,
    )
    payload = {
        "movie_id": movie["id"],
        "cinema_id": cinema["id"],
        "room_ids": [room["id"] for room in rooms],
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
        "base_price": 95000,
    }

    response = client.post("/api/admin/showtimes/bulk", headers=headers, json=payload)
    assert response.status_code == 201
    created = response.get_json()
    assert len(created) == 2
    assert {showtime["room_id"] for showtime in created} == {room["id"] for room in rooms}
    assert {showtime["start_time"] for showtime in created} == {start_time.isoformat()}

    repeated = client.post("/api/admin/showtimes/bulk", headers=headers, json=payload)
    assert repeated.status_code == 409
    listed = client.get("/api/admin/showtimes", headers=headers).get_json()
    assert sum(
        showtime["movie_id"] == movie["id"] and showtime["start_time"] == start_time.isoformat()
        for showtime in listed
    ) == 2


def test_bulk_showtime_requires_valid_rooms_before_creating_anything(client, auth):
    headers = auth("admin")
    movie = client.get("/api/admin/movies", headers=headers).get_json()[0]
    cinemas = client.get("/api/admin/cinemas", headers=headers).get_json()
    rooms = client.get("/api/admin/rooms", headers=headers).get_json()
    first_room = next(room for room in rooms if room["cinema_id"] == cinemas[0]["id"])
    other_cinema_room = next(room for room in rooms if room["cinema_id"] == cinemas[1]["id"])
    start_time = (local_now() + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
    payload = {
        "movie_id": movie["id"],
        "cinema_id": cinemas[0]["id"],
        "room_ids": [first_room["id"], other_cinema_room["id"]],
        "start_time": start_time,
        "base_price": 90000,
    }

    response = client.post("/api/admin/showtimes/bulk", headers=headers, json=payload)
    assert response.status_code == 400
    assert "chiếu" in response.get_json()["message"]
    assert all(
        not (
            showtime["movie_id"] == movie["id"]
            and showtime["start_time"] == start_time
            and showtime["room_id"] == first_room["id"]
        )
        for showtime in client.get("/api/admin/showtimes", headers=headers).get_json()
    )


def test_admin_showtime_rejects_past_time_and_room_from_another_cinema(client, auth):
    headers = auth("admin")
    movies = client.get("/api/admin/movies", headers=headers).get_json()
    cinemas = client.get("/api/admin/cinemas", headers=headers).get_json()
    rooms = client.get("/api/admin/rooms", headers=headers).get_json()
    past = (local_now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    payload = {
        "movie_id": movies[0]["id"], "cinema_id": cinemas[0]["id"],
        "room_id": next(room["id"] for room in rooms if room["cinema_id"] == cinemas[0]["id"]),
        "start_time": past, "base_price": 90000,
    }
    assert client.post("/api/admin/showtimes", headers=headers, json=payload).status_code == 400

    payload["start_time"] = (local_now() + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
    payload["cinema_id"] = cinemas[1]["id"]
    assert client.post("/api/admin/showtimes", headers=headers, json=payload).status_code == 400


def test_admin_showtime_rejects_overlapping_showtime_in_same_room(client, auth):
    headers = auth("admin")
    existing = client.get("/api/admin/showtimes", headers=headers).get_json()[0]
    payload = {
        "movie_id": existing["movie_id"],
        "cinema_id": existing["cinema_id"],
        "room_id": existing["room_id"],
        "start_time": (local_now() + timedelta(days=1)).replace(hour=10, minute=30, second=0)
        .strftime("%Y-%m-%dT%H:%M"),
        "base_price": 90000,
    }
    assert client.post("/api/admin/showtimes", headers=headers, json=payload).status_code == 409


def test_admin_cannot_change_schedule_for_showtime_with_booking(client, auth, app):
    headers = auth("admin")
    with app.app_context():
        showtime = Showtime.query.first()
        booking = Booking(code="CVTESTBOOKING", user_id=3, showtime_id=showtime.id)
        db.session.add(booking)
        db.session.commit()
        showtime_id = showtime.id
        original_movie_id = showtime.movie_id
        room_id = showtime.room_id

    with app.app_context():
        movie_ids = [movie.id for movie in Movie.query.order_by(Movie.id).all()]
        room_ids = [room.id for room in Room.query.order_by(Room.id).all()]
        new_movie_id = next(movie_id for movie_id in movie_ids if movie_id != original_movie_id)
        new_room_id = next(room_id_option for room_id_option in room_ids if room_id_option != room_id)
        room = db.session.get(Room, new_room_id)
        cinema_id = room.cinema_id

    start_time = (local_now() + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
    response = client.put(f"/api/admin/showtimes/{showtime_id}", headers=headers, json={
        "movie_id": new_movie_id, "cinema_id": cinema_id, "room_id": new_room_id,
        "start_time": start_time, "base_price": 90000,
    })
    assert response.status_code == 409


def test_manager_cannot_manage_admin_showtimes(client, auth):
    headers = auth("manager")
    assert client.post("/api/admin/showtimes", headers=headers, json={}).status_code == 403
    assert client.post("/api/admin/showtimes/bulk", headers=headers, json={}).status_code == 403
