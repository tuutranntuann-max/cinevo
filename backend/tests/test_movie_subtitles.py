from datetime import timedelta
from io import BytesIO

from app.extensions import db
from app.models import Membership, Movie, User
from app.timeutil import local_now, utc_now


def _film_bytes():
    return b"\x00\x00\x00\x18ftypisom" + b"subtitle-film-test"


def test_movie_subtitles_support_srt_conversion_vtt_urls_and_member_playback(
    client, auth, app, tmp_path
):
    app.config["FEATURE_FILM_UPLOAD_DIR"] = tmp_path / "films"
    created = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim có phụ đề riêng",
    })
    movie_id = created.get_json()["id"]
    uploaded_film = client.post(
        f"/api/admin/movies/{movie_id}/film",
        headers=auth("admin"),
        data={"film": (BytesIO(_film_bytes()), "feature.mp4")},
        content_type="multipart/form-data",
    )
    assert uploaded_film.status_code == 200

    srt = b"1\r\n00:00:01,000 --> 00:00:02,000\r\nXin chao\r\n"
    denied = client.post(
        f"/api/admin/movies/{movie_id}/subtitles",
        headers=auth("manager"),
        data={"subtitle": (BytesIO(srt), "vi.srt"), "language": "vi"},
        content_type="multipart/form-data",
    )
    assert denied.status_code == 403

    uploaded = client.post(
        f"/api/admin/movies/{movie_id}/subtitles",
        headers=auth("admin"),
        data={
            "subtitle": (BytesIO(srt), "vi.srt"),
            "language": "vi",
            "label": "Tiếng Việt",
        },
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    uploaded_track = uploaded.get_json()
    assert uploaded_track["format"] == "vtt"

    linked = client.post(
        f"/api/admin/movies/{movie_id}/subtitles/url",
        headers=auth("admin"),
        json={
            "url": "https://captions.example/film-en.vtt?version=1",
            "language": "en",
            "label": "English",
        },
    )
    assert linked.status_code == 201
    assert linked.get_json()["format"] == "url"
    invalid_url = client.post(
        f"/api/admin/movies/{movie_id}/subtitles/url",
        headers=auth("admin"),
        json={"url": "http://localhost/private.vtt", "language": "vi"},
    )
    assert invalid_url.status_code == 400

    with app.app_context():
        movie = db.session.get(Movie, movie_id)
        movie.status = "ended"
        movie.theatrical_end_date = local_now().date() - timedelta(days=1)
        user = User.query.filter_by(email="user@cinevo.vn").first()
        db.session.add(Membership(
            user_id=user.id,
            tier="SILVER",
            starts_at=utc_now(),
            expires_at=utc_now() + timedelta(days=30),
            status="ACTIVE",
            amount=99000,
            payment_ref="SUBTITLE-TEST",
        ))
        db.session.commit()

    no_membership = client.get(f"/api/movies/watch/{movie_id}").get_json()
    assert no_membership["can_watch"] is False
    assert no_membership["subtitles"] == []

    member_movie = client.get(
        f"/api/movies/watch/{movie_id}", headers=auth("user")
    ).get_json()
    assert member_movie["can_watch"] is True
    assert [track["language"] for track in member_movie["subtitles"]] == ["vi", "en"]
    vtt_response = client.get(member_movie["subtitles"][0]["url"])
    assert vtt_response.status_code == 200
    assert vtt_response.mimetype == "text/vtt"
    assert vtt_response.data.startswith(b"WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000")

    admin_movies = client.get("/api/admin/movies", headers=auth("admin")).get_json()
    admin_movie = next(item for item in admin_movies if item["id"] == movie_id)
    assert len(admin_movie["subtitle_tracks"]) == 2
    removed = client.delete(
        f"/api/admin/movies/{movie_id}/subtitles/{uploaded_track['id']}",
        headers=auth("admin"),
    )
    assert removed.status_code == 200
    refreshed = client.get(
        f"/api/movies/watch/{movie_id}", headers=auth("user")
    ).get_json()
    assert [track["language"] for track in refreshed["subtitles"]] == ["en"]
