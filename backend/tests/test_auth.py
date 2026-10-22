"""Tài khoản: đăng ký, OTP, đăng nhập, chống nâng quyền, validate."""
from io import BytesIO
import re
import smtplib

from tests.conftest import ACCOUNTS


def test_register_always_creates_user_role_even_if_client_sends_role(client, register_payload):
    r = client.post("/api/auth/register", json={**register_payload, "role": "ADMIN", "role_id": 3, "status": "ACTIVE"})
    assert r.status_code == 201
    code = r.get_json()["otp_hint"]
    v = client.post("/api/auth/verify-otp", json={"email": register_payload["email"], "code": code}).get_json()
    assert v["user"]["role"] == "USER" and v["user"]["status"] == "ACTIVE"


def test_pending_account_cannot_login_until_verified(client, register_payload):
    client.post("/api/auth/register", json=register_payload)
    r = client.post("/api/auth/login", json={"email": register_payload["email"], "password": "abc123"})
    assert r.status_code == 403 and r.get_json()["code"] == "NOT_VERIFIED"


def test_customer_login_uses_email_and_password_without_otp(client):
    login = client.post("/api/auth/login", json={
        "email": ACCOUNTS["user"][0],
        "password": ACCOUNTS["user"][1],
    })
    assert login.status_code == 200
    assert "otp_hint" not in login.get_json()
    assert login.get_json()["user"]["role"] == "USER"
    assert client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {login.get_json()['token']}",
    }).status_code == 200

    assert client.post("/api/auth/login/verify-otp", json={
        "email": ACCOUNTS["user"][0], "code": "123456",
    }).status_code == 404


def test_staff_login_uses_password_without_otp(client):
    response = client.post("/api/auth/login", json={
        "email": ACCOUNTS["admin"][0],
        "password": ACCOUNTS["admin"][1],
    })
    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "ADMIN"


def test_registration_delivers_real_email_and_hides_code_from_response(
    client, app, monkeypatch,
):
    from app.services import email_service

    sent_messages = []

    class FakeSmtpServer:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def login(self, username, password):
            assert username == "cinevoshop@gmail.com"
            assert password == "test-app-password"

        def send_message(self, message):
            sent_messages.append(message)

    app.config.update({
        "SMTP_USERNAME": "cinevoshop@gmail.com",
        "SMTP_PASSWORD": "test-app-password",
        "SMTP_FROM_EMAIL": "cinevoshop@gmail.com",
        "OTP_DEBUG_HINT": True,
    })
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", lambda *args, **kwargs: FakeSmtpServer())

    from tests.conftest import REGISTER

    response = client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 201
    assert "otp_hint" not in response.get_json()
    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["From"] == "cinevoshop@gmail.com"
    assert message["To"] == REGISTER["email"]
    code = re.search(r"\b(\d{6})\b", message.get_content()).group(1)
    verified = client.post("/api/auth/verify-otp", json={
        "email": REGISTER["email"],
        "code": code,
    }).status_code == 200
    assert verified


def test_smtp_failure_is_reported_without_creating_an_otp(client, app, monkeypatch):
    from app.models import User
    from app.services import email_service

    class FailedSmtpServer:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def login(self, *_args):
            raise smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    app.config.update({
        "SMTP_USERNAME": "cinevo@example.com",
        "SMTP_PASSWORD": "bad-app-password",
        "SMTP_FROM_EMAIL": "cinevo@example.com",
    })
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", lambda *args, **kwargs: FailedSmtpServer())

    from tests.conftest import REGISTER

    response = client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 503
    assert response.get_json()["code"] == "OTP_DELIVERY_FAILED"
    with app.app_context():
        user = User.query.filter_by(email=REGISTER["email"]).first()
        assert user is None


def test_production_registration_requires_configured_email(tmp_path):
    from tests.conftest import make_app

    app = make_app(
        tmp_path,
        IS_PRODUCTION=True,
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="",
        MOCK_OTP_CODE="",
        OTP_DEBUG_HINT=False,
    )
    from tests.conftest import REGISTER

    response = app.test_client().post("/api/auth/register", json=REGISTER)
    assert response.status_code == 503
    assert response.get_json()["code"] == "OTP_DELIVERY_FAILED"


def test_registration_reports_missing_gmail_app_password(client, app):
    from tests.conftest import REGISTER

    app.config.update({
        "SMTP_USERNAME": "cinevoshop@gmail.com",
        "SMTP_PASSWORD": "",
        "SMTP_FROM_EMAIL": "cinevoshop@gmail.com",
    })
    response = client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 503
    assert response.get_json()["code"] == "OTP_DELIVERY_FAILED"
    assert "App Password" in response.get_json()["message"]


def test_duplicate_email_rejected(client, register_payload):
    r = client.post("/api/auth/register", json={**register_payload, "email": ACCOUNTS["user"][0]})
    assert r.status_code == 409 and r.get_json()["code"] == "EMAIL_EXISTS"


def test_wrong_password_and_unknown_user_give_same_error(client):
    a = client.post("/api/auth/login", json={"email": "user@cinevo.vn", "password": "sai"})
    b = client.post("/api/auth/login", json={"email": "khong@co.vn", "password": "sai"})
    assert a.status_code == b.status_code == 401 and a.get_json() == b.get_json()


def test_wrong_otp_rejected(client, register_payload):
    client.post("/api/auth/register", json=register_payload)
    r = client.post("/api/auth/verify-otp", json={"email": register_payload["email"], "code": "000000"})
    assert r.status_code == 400


def test_user_cannot_change_own_role_via_profile(client, auth):
    r = client.put("/api/auth/me", json={"role": "ADMIN", "full_name": "Zed"}, headers=auth("user"))
    assert r.get_json()["user"]["role"] == "USER"


def test_user_can_upload_replace_and_remove_avatar(client, auth, app, tmp_path):
    app.config["AVATAR_UPLOAD_DIR"] = tmp_path / "avatars"
    png = b"\x89PNG\r\n\x1a\n" + b"avatar-image"
    uploaded = client.post(
        "/api/auth/me/avatar",
        headers=auth("user"),
        data={"image": (BytesIO(png), "avatar.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    user = uploaded.get_json()["user"]
    assert user["avatar_url"].startswith("/api/auth/avatars/avatar_")
    avatar_response = client.get(user["avatar_url"])
    assert avatar_response.status_code == 200
    assert avatar_response.data == png
    avatar_response.close()
    assert client.get("/api/auth/me", headers=auth("user")).get_json()["user"]["avatar_url"] == user["avatar_url"]

    replacement = b"\xff\xd8\xffreplacement"
    replaced = client.post(
        "/api/auth/me/avatar",
        headers=auth("user"),
        data={"image": (BytesIO(replacement), "new-avatar.jpg")},
        content_type="multipart/form-data",
    )
    assert replaced.status_code == 200
    replacement_url = replaced.get_json()["user"]["avatar_url"]
    assert replacement_url != user["avatar_url"]
    assert client.get(user["avatar_url"]).status_code == 404
    assert client.get(replacement_url).data == replacement

    deleted = client.delete("/api/auth/me/avatar", headers=auth("user"))
    assert deleted.status_code == 200
    assert deleted.get_json()["user"]["avatar_url"] is None
    assert client.get(replacement_url).status_code == 404


def test_avatar_upload_requires_auth_and_valid_image(client, auth, app, tmp_path):
    app.config["AVATAR_UPLOAD_DIR"] = tmp_path / "avatars"
    assert client.post(
        "/api/auth/me/avatar",
        data={"image": (BytesIO(b"\x89PNG\r\n\x1a\nimage"), "avatar.png")},
        content_type="multipart/form-data",
    ).status_code == 401
    invalid = client.post(
        "/api/auth/me/avatar",
        headers=auth("user"),
        data={"image": (BytesIO(b"not an image"), "avatar.png")},
        content_type="multipart/form-data",
    )
    assert invalid.status_code == 400


def test_password_is_hashed(app):
    from app.models import User
    with app.app_context():
        u = User.query.filter_by(email="user@cinevo.vn").one()
        assert u.password_hash != "User@123" and u.password_hash.startswith(("scrypt:", "pbkdf2:"))


def test_locked_user_token_stops_working(client, auth):
    uid = client.get("/api/auth/me", headers=auth("user")).get_json()["user"]["id"]
    assert client.patch(f"/api/admin/users/{uid}/status", json={"status": "LOCKED"}, headers=auth("admin")).status_code == 200
    assert client.get("/api/auth/me", headers=auth("user")).status_code == 401


def test_public_promotions_only_returns_active_codes(client, app):
    from app.extensions import db
    from app.models import Promotion

    with app.app_context():
        db.session.add(Promotion(
            code="HIDDEN99",
            description="Ưu đãi không hoạt động",
            discount_percent=99,
            active=False,
        ))
        db.session.commit()

    response = client.get("/api/promotions")
    assert response.status_code == 200
    promotions = response.get_json()
    assert {promotion["code"] for promotion in promotions} == {"CINEVO10", "WEEKEND15"}
    assert all(promotion["active"] for promotion in promotions)
