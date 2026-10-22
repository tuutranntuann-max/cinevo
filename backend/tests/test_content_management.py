from io import BytesIO

from app.extensions import db
from app.models import (
    CinemaEvent, NewsArticle, Promotion, Role, ROLE_EMPLOYEE, STATUS_ACTIVE, User,
)


def test_news_management_is_available_to_staff_and_public_only_sees_active(
    client, auth
):
    payload = {
        "title": "Tin đoàn phim mới",
        "summary": "Thông tin buổi ra mắt phim và diễn viên.",
        "body": "Nội dung bài báo về đoàn phim.",
        "category": "Điện ảnh",
        "source": "Báo Cinevo",
        "active": True,
    }
    assert client.get("/api/content/manage/news").status_code == 401
    assert client.post("/api/content/manage/news", json=payload, headers=auth("user")).status_code == 403

    created = client.post("/api/content/manage/news", json=payload, headers=auth("manager"))
    assert created.status_code == 201
    article_id = created.get_json()["id"]
    public = client.get("/api/content/news").get_json()
    assert len(public) == 1
    assert public[0]["title"] == payload["title"]
    assert public[0]["source"] == payload["source"]

    hidden = client.post(
        "/api/content/manage/news",
        json={**payload, "title": "Bản nháp", "active": False},
        headers=auth("admin"),
    )
    assert hidden.status_code == 201
    scheduled = client.post(
        "/api/content/manage/news",
        json={**payload, "title": "Tin lên lịch", "published_at": "2099-01-01T00:00:00Z"},
        headers=auth("admin"),
    )
    assert scheduled.status_code == 201
    assert len(client.get("/api/content/news").get_json()) == 1

    updated = client.put(
        f"/api/content/manage/news/{article_id}",
        json={"title": "Tin đã chỉnh sửa"},
        headers=auth("admin"),
    )
    assert updated.status_code == 200
    assert updated.get_json()["title"] == "Tin đã chỉnh sửa"
    assert client.delete(
        f"/api/content/manage/news/{article_id}",
        headers=auth("manager"),
    ).status_code == 200
    assert client.get("/api/content/news").get_json() == []
    with client.application.app_context():
        assert NewsArticle.query.count() == 2


def test_staff_can_manage_event_posters_and_public_events(client, auth, app, tmp_path):
    app.config["CONTENT_UPLOAD_DIR"] = tmp_path / "content"
    uploaded = client.post(
        "/api/content/manage/media",
        headers=auth("manager"),
        data={"image": (BytesIO(b"\x89PNG\r\n\x1a\nmock-png-content"), "event.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    image_url = uploaded.get_json()["image_url"]
    image = client.get(image_url)
    assert image.status_code == 200
    assert image.data.startswith(b"\x89PNG\r\n\x1a\n")

    created = client.post("/api/content/manage/events", headers=auth("manager"), json={
        "title": "Tuần lễ phim Việt",
        "summary": "Ưu đãi và giao lưu cùng đoàn phim.",
        "body": "Chi tiết chương trình.",
        "image_url": image_url,
        "active": True,
    })
    assert created.status_code == 201
    event_id = created.get_json()["id"]
    assert client.get("/api/content/events").get_json()[0]["image_url"] == image_url

    invalid_dates = client.put(
        f"/api/content/manage/events/{event_id}",
        headers=auth("admin"),
        json={"starts_at": "2026-10-22T10:00", "ends_at": "2026-10-21T10:00"},
    )
    assert invalid_dates.status_code == 400
    updated = client.put(
        f"/api/content/manage/events/{event_id}",
        headers=auth("admin"),
        json={"active": False},
    )
    assert updated.status_code == 200
    assert client.get("/api/content/events").get_json() == []
    assert client.delete(
        f"/api/content/manage/events/{event_id}",
        headers=auth("manager"),
    ).status_code == 200
    with app.app_context():
        assert CinemaEvent.query.count() == 0


def test_staff_can_create_edit_delete_promotions_with_images(client, auth, app):
    image_url = "/api/content/media/content_example.png"
    created = client.post("/api/content/manage/promotions", headers=auth("manager"), json={
        "code": "MOVIE25",
        "description": "Ưu đãi thành viên mới.",
        "discount_percent": 25,
        "image_url": image_url,
        "active": True,
    })
    assert created.status_code == 201
    promotion_id = created.get_json()["id"]
    assert created.get_json()["image_url"] == image_url
    assert client.get("/api/promotions").get_json()[0]["code"] == "MOVIE25"

    duplicate = client.post("/api/content/manage/promotions", headers=auth("admin"), json={
        "code": "movie25",
        "discount_percent": 10,
    })
    assert duplicate.status_code == 409

    with app.app_context():
        employee = User(
            full_name="Nhân viên nội dung",
            email="content.employee@example.com",
            role=Role.query.filter_by(name=ROLE_EMPLOYEE).one(),
            status=STATUS_ACTIVE,
        )
        employee.set_password("EmployeePass123")
        db.session.add(employee)
        db.session.commit()
    employee_token = client.post("/api/auth/login", json={
        "email": "content.employee@example.com",
        "password": "EmployeePass123",
    }).get_json()["token"]
    updated = client.put(
        f"/api/content/manage/promotions/{promotion_id}",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"discount_percent": 35, "active": False, "image_url": None},
    )
    assert updated.status_code == 200
    assert updated.get_json()["discount_percent"] == 35
    assert all(item["code"] != "MOVIE25" for item in client.get("/api/promotions").get_json())
    assert client.delete(
        f"/api/content/manage/promotions/{promotion_id}",
        headers=auth("manager"),
    ).status_code == 200
    with client.application.app_context():
        assert Promotion.query.filter_by(code="MOVIE25").count() == 0


def test_media_upload_rejects_non_image_content(client, auth):
    response = client.post(
        "/api/content/manage/media",
        headers=auth("admin"),
        data={"image": (BytesIO(b"not an image"), "image.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
