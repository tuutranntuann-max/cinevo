from io import BytesIO

import pytest


PNG = b"\x89PNG\r\n\x1a\n" + b"title-logo-test"


@pytest.fixture
def admin_movie(client, auth):
    response = client.post("/api/admin/movies", headers=auth("admin"), json={
        "title": "Phim kiểm thử logo", "genre": "Phiêu lưu",
        "duration_minutes": 100, "age_rating": "T13", "rating": 8,
        "status": "coming_soon",
    })
    assert response.status_code == 201
    return response.get_json()


def test_admin_can_upload_replace_toggle_and_remove_per_movie_title_logo(
    client, auth, admin_movie, app, tmp_path
):
    app.config["POSTER_UPLOAD_DIR"] = tmp_path / "posters"
    endpoint = f"/api/admin/movies/{admin_movie['id']}/title-logo"
    denied = client.post(
        endpoint,
        headers=auth("manager"),
        data={"logo": (BytesIO(PNG), "logo.png")},
        content_type="multipart/form-data",
    )
    assert denied.status_code == 403

    first = client.post(
        endpoint,
        headers=auth("admin"),
        data={"logo": (BytesIO(PNG), "logo.png")},
        content_type="multipart/form-data",
    )
    assert first.status_code == 200
    first_movie = first.get_json()
    assert first_movie["title_logo_enabled"] is True
    assert client.get(first_movie["title_logo_url"]).data == PNG
    public_movie = client.get(f"/api/movies/{admin_movie['id']}").get_json()
    assert public_movie["title_logo_url"] == first_movie["title_logo_url"]
    assert public_movie["title_logo_enabled"] is True

    text_mode = client.patch(endpoint, headers=auth("admin"), json={"enabled": False})
    assert text_mode.status_code == 200
    assert text_mode.get_json()["title_logo_enabled"] is False

    second = client.post(
        endpoint,
        headers=auth("admin"),
        data={"logo": (BytesIO(PNG + b"-replacement"), "replacement.png")},
        content_type="multipart/form-data",
    )
    assert second.status_code == 200
    second_movie = second.get_json()
    assert second_movie["title_logo_enabled"] is True
    assert second_movie["title_logo_url"] != first_movie["title_logo_url"]
    assert client.get(first_movie["title_logo_url"]).status_code == 404

    removed = client.delete(endpoint, headers=auth("admin"))
    assert removed.status_code == 200
    assert removed.get_json()["title_logo_url"] is None
    assert removed.get_json()["title_logo_enabled"] is False
    assert client.get(second_movie["title_logo_url"]).status_code == 404


def test_title_logo_upload_rejects_invalid_images_and_cannot_be_enabled_without_image(
    client, auth, admin_movie
):
    endpoint = f"/api/admin/movies/{admin_movie['id']}/title-logo"
    invalid = client.post(
        endpoint,
        headers=auth("admin"),
        data={"logo": (BytesIO(b"not-an-image"), "logo.png")},
        content_type="multipart/form-data",
    )
    assert invalid.status_code == 400
    assert client.patch(endpoint, headers=auth("admin"), json={"enabled": True}).status_code == 400
