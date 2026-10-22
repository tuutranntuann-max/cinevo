from io import BytesIO


PNG = b"\x89PNG\r\n\x1a\n" + b"appearance-test"
MP4 = b"\x00\x00\x00\x18ftypisom" + b"appearance-video"


def test_appearance_settings_are_admin_only_and_persist(client, auth):
    assert client.get("/api/admin/appearance").status_code == 401
    assert client.get("/api/admin/appearance", headers=auth("manager")).status_code == 403

    defaults = client.get("/api/movies/appearance")
    assert defaults.status_code == 200
    assert defaults.get_json()["accent_color"] == "#e11d2e"
    assert defaults.get_json()["title_motion"] == "bob"
    assert defaults.get_json()["title_size"] == 78
    assert defaults.get_json()["welcome_enabled"] is True
    assert defaults.get_json()["welcome_title"] == "Chào mừng đến với CINEVO"
    assert defaults.get_json()["footer_company_name"] == "CINEVO"
    assert defaults.get_json()["footer_tax_code"] == "0335823036"
    assert defaults.get_json()["footer_email"] == "tuutranntuann@gmail.com"
    assert len(defaults.get_json()["footer_partners"]) == 15

    saved = client.patch("/api/admin/appearance", headers=auth("admin"), json={
        "accent_color": "#1a2b3c",
        "page_color": "#101010",
        "surface_color": "#202020",
        "overlay_opacity": 0.6,
        "title_size": 85,
        "title_font": "serif",
        "title_frame": "speech",
        "title_preset": "glow",
        "title_motion": "sway",
    })
    assert saved.status_code == 200
    public_settings = client.get("/api/movies/appearance").get_json()
    assert public_settings["accent_color"] == "#1a2b3c"
    assert public_settings["title_font"] == "serif"
    assert public_settings["title_size"] == 85
    assert public_settings["title_frame"] == "speech"
    assert public_settings["title_preset"] == "glow"
    assert public_settings["title_motion"] == "sway"
    assert client.patch("/api/admin/appearance", headers=auth("admin"), json={
        "footer_company_name": "Công ty Cinevo",
        "footer_tax_code": "0123456789",
        "footer_email": "contact@cinevo.vn",
        "footer_license": "Đơn vị cấp phép",
        "footer_registered": "01/01/2020",
        "footer_address": "TP. Hồ Chí Minh",
        "footer_version": "v2.0",
        "footer_commerce_notice": "",
        "footer_show_upcoming": False,
        "footer_partners_enabled": False,
        "footer_links": [{"label": "Liên hệ", "url": "/contact"}],
        "footer_partners": [{
            "name": "Đối tác A",
            "logo_url": "https://example.com/logo.png",
            "url": "https://example.com",
        }],
    }).status_code == 200
    footer = client.get("/api/movies/appearance").get_json()
    assert footer["footer_company_name"] == "Công ty Cinevo"
    assert footer["footer_tax_code"] == "0123456789"
    assert footer["footer_email"] == "contact@cinevo.vn"
    assert footer["footer_show_upcoming"] is False
    assert footer["footer_partners_enabled"] is False
    assert footer["footer_links"] == [{"label": "Liên hệ", "url": "/contact"}]
    assert footer["footer_partners"] == [{
        "name": "Đối tác A",
        "logo_url": "https://example.com/logo.png",
        "url": "https://example.com",
    }]
    welcome = client.patch("/api/admin/appearance", headers=auth("admin"), json={
        "welcome_enabled": False,
        "welcome_title": "Cinevo xin chào",
        "welcome_description": "Chọn phim và đặt vé tại Cinevo.",
        "welcome_button_text": "Khám phá ngay",
    })
    assert welcome.status_code == 200
    public_welcome = client.get("/api/movies/appearance").get_json()
    assert public_welcome["welcome_enabled"] is False
    assert public_welcome["welcome_title"] == "Cinevo xin chào"
    assert public_welcome["welcome_description"] == "Chọn phim và đặt vé tại Cinevo."
    assert public_welcome["welcome_button_text"] == "Khám phá ngay"
    assert client.patch(
        "/api/admin/appearance",
        headers=auth("admin"),
        json={"accent_color": "red"},
    ).status_code == 400
    assert client.patch(
        "/api/admin/appearance",
        headers=auth("admin"),
        json={"title_motion": "unexpected"},
    ).status_code == 400
    assert client.patch(
        "/api/admin/appearance",
        headers=auth("admin"),
        json={"title_size": 101},
    ).status_code == 400
    assert client.patch(
        "/api/admin/appearance",
        headers=auth("admin"),
        json={"footer_partners": [{"name": "Đối tác", "logo_url": "javascript:alert(1)"}]},
    ).status_code == 400
    assert client.patch(
        "/api/admin/appearance",
        headers=auth("admin"),
        json={"footer_show_upcoming": "false"},
    ).status_code == 400
    assert client.patch(
        "/api/admin/appearance",
        headers=auth("admin"),
        json={"welcome_enabled": "false"},
    ).status_code == 400
    assert client.patch(
        "/api/admin/appearance",
        headers=auth("admin"),
        json={"welcome_button_text": ""},
    ).status_code == 400
    assert client.patch(
        "/api/admin/appearance",
        headers=auth("admin"),
        json={"footer_email": "not-an-email"},
    ).status_code == 400
    blanked = client.patch("/api/admin/appearance", headers=auth("admin"), json={
        "footer_tax_code": "",
        "footer_email": "",
    })
    assert blanked.status_code == 200
    assert blanked.get_json()["footer_tax_code"] == "0335823036"
    assert blanked.get_json()["footer_email"] == "tuutranntuann@gmail.com"


def test_admin_can_upload_and_remove_site_appearance_media(client, auth, app, tmp_path):
    app.config["APPEARANCE_UPLOAD_DIR"] = tmp_path / "appearance"
    denied = client.post(
        "/api/admin/appearance/site/media",
        headers=auth("manager"),
        data={"media": (BytesIO(PNG), "background.png")},
        content_type="multipart/form-data",
    )
    assert denied.status_code == 403

    uploaded = client.post(
        "/api/admin/appearance/site/media",
        headers=auth("admin"),
        data={"media": (BytesIO(PNG), "background.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    media_url = uploaded.get_json()["site_media_url"]
    public_settings = client.get("/api/movies/appearance").get_json()
    assert public_settings["site_media_url"] == media_url
    media = client.get(media_url)
    assert media.status_code == 200
    assert media.mimetype == "image/png"
    assert media.data == PNG

    removed = client.delete("/api/admin/appearance/site/media", headers=auth("admin"))
    assert removed.status_code == 200
    assert "site_media_url" not in removed.get_json()
    assert client.get(media_url).status_code == 404


def test_admin_can_upload_banner_video(client, auth, app, tmp_path):
    app.config["APPEARANCE_UPLOAD_DIR"] = tmp_path / "appearance"
    uploaded = client.post(
        "/api/admin/appearance/banner/media",
        headers=auth("admin"),
        data={"media": (BytesIO(MP4), "banner.mp4")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    appearance = client.get("/api/movies/appearance").get_json()
    assert appearance["banner_media_type"] == "video"
    assert client.get(appearance["banner_media_url"]).data == MP4


def test_admin_can_upload_and_remove_welcome_background(client, auth, app, tmp_path):
    app.config["APPEARANCE_UPLOAD_DIR"] = tmp_path / "appearance"
    uploaded = client.post(
        "/api/admin/appearance/welcome/media",
        headers=auth("admin"),
        data={"media": (BytesIO(PNG), "welcome.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    media_url = uploaded.get_json()["welcome_media_url"]
    public_settings = client.get("/api/movies/appearance").get_json()
    assert public_settings["welcome_media_url"] == media_url
    assert client.get(media_url).data == PNG

    video = client.post(
        "/api/admin/appearance/welcome/media",
        headers=auth("admin"),
        data={"media": (BytesIO(MP4), "welcome.mp4")},
        content_type="multipart/form-data",
    )
    assert video.status_code == 200
    video_url = video.get_json()["welcome_media_url"]
    assert video.get_json()["welcome_media_type"] == "video"
    assert client.get(video_url).mimetype == "video/mp4"
    assert client.get(video_url).data == MP4

    removed = client.delete("/api/admin/appearance/welcome/media", headers=auth("admin"))
    assert removed.status_code == 200
    assert "welcome_media_url" not in removed.get_json()
    assert client.get(video_url).status_code == 404


def test_admin_can_upload_and_remove_public_logo(client, auth, app, tmp_path):
    app.config["APPEARANCE_UPLOAD_DIR"] = tmp_path / "appearance"
    denied = client.post(
        "/api/admin/appearance/logo/media",
        headers=auth("manager"),
        data={"media": (BytesIO(PNG), "logo.png")},
        content_type="multipart/form-data",
    )
    assert denied.status_code == 403

    uploaded = client.post(
        "/api/admin/appearance/logo/media",
        headers=auth("admin"),
        data={"media": (BytesIO(PNG), "logo.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    logo_url = uploaded.get_json()["logo_media_url"]
    assert client.get("/api/movies/appearance").get_json()["logo_media_url"] == logo_url
    logo = client.get(logo_url)
    assert logo.status_code == 200
    assert logo.mimetype == "image/png"
    assert logo.data == PNG

    rejected_video = client.post(
        "/api/admin/appearance/logo/media",
        headers=auth("admin"),
        data={"media": (BytesIO(MP4), "logo.mp4")},
        content_type="multipart/form-data",
    )
    assert rejected_video.status_code == 400

    removed = client.delete("/api/admin/appearance/logo/media", headers=auth("admin"))
    assert removed.status_code == 200
    assert "logo_media_url" not in removed.get_json()
    assert client.get(logo_url).status_code == 404
