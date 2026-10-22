from io import BytesIO

import pytest


@pytest.fixture
def trailer_movie(client, auth):
    response = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim kiểm thử trailer", "genre": "Hành động",
        "duration_minutes": 110, "age_rating": "T13", "rating": 8,
        "status": "coming_soon",
    })
    assert response.status_code == 201
    return response.get_json()


def test_admin_can_upload_and_remove_public_movie_trailer(client, auth, trailer_movie, app, tmp_path):
    app.config["TRAILER_UPLOAD_DIR"] = tmp_path / "trailers"
    video = b"\x00\x00\x00\x18ftypisom" + b"test-video"

    denied = client.post(
        f"/api/admin/movies/{trailer_movie['id']}/trailer",
        headers=auth("manager"),
        data={"trailer": (BytesIO(video), "trailer.mp4")},
        content_type="multipart/form-data",
    )
    assert denied.status_code == 403

    uploaded = client.post(
        f"/api/admin/movies/{trailer_movie['id']}/trailer",
        headers=auth("admin"),
        data={"trailer": (BytesIO(video), "trailer.mp4")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    trailer_url = uploaded.get_json()["trailer_url"]
    assert trailer_url.startswith(f"/api/movies/{trailer_movie['id']}/trailer?format=mp4")

    public_movie = client.get(f"/api/movies/{trailer_movie['id']}").get_json()
    assert public_movie["trailer_url"] == trailer_url
    response = client.get(trailer_url)
    assert response.status_code == 200
    assert response.data == video
    assert response.mimetype == "video/mp4"

    deleted = client.delete(f"/api/admin/movies/{trailer_movie['id']}/trailer",
                            headers=auth("admin"))
    assert deleted.status_code == 200
    assert deleted.get_json()["trailer_url"] is None
    assert client.get(trailer_url).status_code == 404


def test_admin_can_upload_and_play_mp3_trailer(client, auth, trailer_movie, app, tmp_path):
    app.config["TRAILER_UPLOAD_DIR"] = tmp_path / "trailers"
    audio = b"ID3\x04\x00\x00" + b"\x00" * 4 + b"audio-test"
    uploaded = client.post(
        f"/api/admin/movies/{trailer_movie['id']}/audio",
        headers=auth("admin"),
        data={"audio": (BytesIO(audio), "theme.mp3")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    audio_url = uploaded.get_json()["audio_url"]
    assert "/audio?format=mp3" in audio_url
    response = client.get(audio_url)
    assert response.status_code == 200
    assert response.mimetype == "audio/mpeg"
    assert response.data == audio


def test_movie_can_keep_mp4_and_mp3_together(client, auth, trailer_movie, app, tmp_path):
    app.config["TRAILER_UPLOAD_DIR"] = tmp_path / "trailers"
    video = b"\x00\x00\x00\x18ftypisom" + b"test-video"
    audio = b"ID3\x04\x00\x00" + b"\x00" * 4 + b"audio-test"
    movie_id = trailer_movie["id"]

    audio_upload = client.post(
        f"/api/admin/movies/{movie_id}/audio",
        headers=auth("admin"),
        data={"audio": (BytesIO(audio), "music.mp3")},
        content_type="multipart/form-data",
    )
    assert audio_upload.status_code == 200
    audio_url = audio_upload.get_json()["audio_url"]

    video_upload = client.post(
        f"/api/admin/movies/{movie_id}/trailer",
        headers=auth("admin"),
        data={"trailer": (BytesIO(video), "trailer.mp4")},
        content_type="multipart/form-data",
    )
    assert video_upload.status_code == 200
    data = video_upload.get_json()
    assert "format=mp4" in data["trailer_url"]
    assert data["audio_url"] == audio_url
    assert client.get(data["trailer_url"]).data == video
    assert client.get(data["audio_url"]).data == audio

    video_deleted = client.delete(f"/api/admin/movies/{movie_id}/trailer", headers=auth("admin"))
    assert video_deleted.status_code == 200
    assert video_deleted.get_json()["trailer_url"] == audio_url
    assert video_deleted.get_json()["audio_url"] == audio_url
    assert client.get(audio_url).data == audio


def test_replacing_video_preserves_audio_and_removing_audio_preserves_video(
    client, auth, trailer_movie, app, tmp_path
):
    app.config["TRAILER_UPLOAD_DIR"] = tmp_path / "trailers"
    video = b"\x00\x00\x00\x18ftypisom" + b"test-video"
    audio = b"ID3\x04\x00\x00" + b"\x00" * 4 + b"audio-test"
    movie_id = trailer_movie["id"]

    first_video = client.post(
        f"/api/admin/movies/{movie_id}/trailer", headers=auth("admin"),
        data={"trailer": (BytesIO(video), "one.mp4")}, content_type="multipart/form-data",
    ).get_json()
    audio_upload = client.post(
        f"/api/admin/movies/{movie_id}/audio", headers=auth("admin"),
        data={"audio": (BytesIO(audio), "music.mp3")}, content_type="multipart/form-data",
    )
    assert audio_upload.status_code == 200
    assert audio_upload.get_json()["trailer_url"] == first_video["trailer_url"]

    removed = client.delete(f"/api/admin/movies/{movie_id}/audio", headers=auth("admin"))
    assert removed.status_code == 200
    assert removed.get_json()["trailer_url"] == first_video["trailer_url"]
    assert removed.get_json()["audio_url"] is None
    assert client.get(first_video["trailer_url"]).data == video


@pytest.mark.parametrize(("filename", "contents"), [
    ("clip.mov", b"not-a-video"),
    ("clip.mp4", b"not-a-video"),
    ("clip.webm", b"not-a-video"),
])
def test_trailer_upload_rejects_unsupported_or_invalid_video(client, auth, trailer_movie, filename, contents):
    response = client.post(
        f"/api/admin/movies/{trailer_movie['id']}/trailer",
        headers=auth("admin"),
        data={"trailer": (BytesIO(contents), filename)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
