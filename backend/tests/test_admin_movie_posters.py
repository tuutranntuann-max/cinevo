from io import BytesIO
import json

import pytest


@pytest.fixture
def admin_movie(client, auth):
    response = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim kiểm thử poster", "genre": "Hành động",
        "duration_minutes": 120, "age_rating": "T13", "rating": 8,
        "status": "coming_soon",
    })
    assert response.status_code == 201
    return response.get_json()


def test_admin_can_create_movie_for_showtime_form(client, auth):
    response = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim mới", "genre": "Phiêu lưu", "duration_minutes": 105,
        "age_rating": "P", "rating": 9, "status": "coming_soon",
    })
    assert response.status_code == 201
    assert response.get_json()["title"] == "Phim mới"
    assert response.get_json()["id"] in [movie["id"] for movie in client.get("/api/admin/movies", headers=auth("admin")).get_json()]


def test_movie_poster_upload_is_admin_only_and_publicly_visible(client, auth, admin_movie, app, tmp_path):
    app.config["POSTER_UPLOAD_DIR"] = tmp_path / "posters"
    image_data = b"\x89PNG\r\n\x1a\n" + b"test-image"
    upload = client.post(
        f"/api/admin/movies/{admin_movie['id']}/poster",
        headers=auth("admin"),
        data={"poster": (BytesIO(image_data), "poster.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200
    movie = upload.get_json()
    assert movie["poster_url"].startswith(f"/api/movies/{admin_movie['id']}/poster?")
    assert client.get(movie["poster_url"]).data == image_data
    assert client.post(
        f"/api/admin/movies/{admin_movie['id']}/poster",
        headers=auth("manager"),
        data={"poster": (BytesIO(image_data), "poster.png")},
        content_type="multipart/form-data",
    ).status_code == 403


def test_movie_poster_upload_accepts_jfif_extension(client, auth, admin_movie, app, tmp_path):
    app.config["POSTER_UPLOAD_DIR"] = tmp_path / "posters"
    image_data = b"\xff\xd8\xff" + b"test-image"
    upload = client.post(
        f"/api/admin/movies/{admin_movie['id']}/poster",
        headers=auth("admin"),
        data={"poster": (BytesIO(image_data), "poster.jfif")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200
    movie = upload.get_json()
    assert "format=jpg" in movie["poster_url"]
    assert client.get(movie["poster_url"]).data == image_data


def test_replacing_movie_poster_uses_new_file_and_invalidates_old_url(
    client, auth, admin_movie, app, tmp_path
):
    app.config["POSTER_UPLOAD_DIR"] = tmp_path / "posters"
    endpoint = f"/api/admin/movies/{admin_movie['id']}/poster"
    first_image = b"\x89PNG\r\n\x1a\nfirst-image"
    first_upload = client.post(
        endpoint,
        headers=auth("admin"),
        data={"poster": (BytesIO(first_image), "first.png")},
        content_type="multipart/form-data",
    )
    assert first_upload.status_code == 200
    first_url = first_upload.get_json()["poster_url"]

    second_image = b"\x89PNG\r\n\x1a\nsecond-image"
    second_upload = client.post(
        endpoint,
        headers=auth("admin"),
        data={"poster": (BytesIO(second_image), "second.png")},
        content_type="multipart/form-data",
    )
    assert second_upload.status_code == 200
    second_url = second_upload.get_json()["poster_url"]

    assert second_url != first_url
    assert client.get(second_url).data == second_image
    assert client.get(first_url).status_code == 404


@pytest.mark.parametrize(("filename", "contents"), [
    ("poster.svg", b"<svg></svg>"),
    ("poster.png", b"not-an-image"),
])
def test_movie_poster_upload_rejects_unsupported_files(client, auth, admin_movie, filename, contents):
    response = client.post(
        f"/api/admin/movies/{admin_movie['id']}/poster",
        headers=auth("admin"),
        data={"poster": (BytesIO(contents), filename)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.content


def test_tmdb_search_auto_downloads_exact_title_match(client, auth, admin_movie, app, tmp_path, monkeypatch):
    from app.services import tmdb

    app.config["TMDB_API_KEY"] = "test-tmdb-key"
    app.config["POSTER_UPLOAD_DIR"] = tmp_path / "posters"
    image = b"\x89PNG\r\n\x1a\nposter-content"
    responses = [
        FakeResponse(json.dumps({"results": [{
            "id": 123,
            "title": admin_movie["title"],
            "original_title": admin_movie["title"],
            "release_date": "2025-01-01",
            "overview": "Test film",
            "poster_path": "/test-poster.png",
        }]}).encode()),
        FakeResponse(image),
    ]
    requested_urls = []

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        assert timeout == 10
        return responses.pop(0)

    monkeypatch.setattr(tmdb, "urlopen", fake_urlopen)
    response = client.post(
        f"/api/admin/movies/{admin_movie['id']}/poster/search",
        headers=auth("admin"),
        json={},
    )

    assert response.status_code == 200
    result = response.get_json()
    assert result["auto_applied"] is True
    assert result["matched_title"] == admin_movie["title"]
    assert result["movie"]["poster_url"].startswith(f"/api/movies/{admin_movie['id']}/poster?")
    assert client.get(result["movie"]["poster_url"]).data == image
    assert len(requested_urls) == 2
    assert "test-tmdb-key" in requested_urls[0]
    assert requested_urls[1] == "https://image.tmdb.org/t/p/w500/test-poster.png"


def test_tmdb_search_requires_admin_and_manual_choice_for_non_exact_match(
    client, auth, admin_movie, app, monkeypatch
):
    from app.services import tmdb

    app.config["TMDB_API_KEY"] = "test-tmdb-key"
    response_content = json.dumps({"results": [{
        "id": 456,
        "title": "A Similar Movie",
        "original_title": "A Similar Movie",
        "release_date": "2024-01-01",
        "overview": "Similar title, not an exact match.",
        "poster_path": "/similar.jpg",
    }]}).encode()
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        return FakeResponse(response_content)

    monkeypatch.setattr(tmdb, "urlopen", fake_urlopen)
    endpoint = f"/api/admin/movies/{admin_movie['id']}/poster/search"
    assert client.post(endpoint, headers=auth("manager"), json={}).status_code == 403

    response = client.post(endpoint, headers=auth("admin"), json={})
    assert response.status_code == 200
    result = response.get_json()
    assert result["auto_applied"] is False
    assert result["movie"] is None
    assert result["candidates"][0]["title"] == "A Similar Movie"
    assert result["candidates"][0]["preview_url"].endswith("/w342/similar.jpg")
    assert len(calls) == 1

    invalid_path = client.post(
        f"/api/admin/movies/{admin_movie['id']}/poster/tmdb",
        headers=auth("admin"),
        json={"poster_path": "https://evil.invalid/poster.png"},
    )
    assert invalid_path.status_code == 400


def test_tmdb_poster_search_explains_missing_api_key(client, auth, admin_movie, app):
    app.config["TMDB_API_KEY"] = ""
    response = client.post(
        f"/api/admin/movies/{admin_movie['id']}/poster/search",
        headers=auth("admin"),
        json={},
    )
    assert response.status_code == 503
    assert "TMDB_API_KEY" in response.get_json()["message"]
