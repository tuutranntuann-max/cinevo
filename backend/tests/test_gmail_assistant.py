from urllib.parse import parse_qs, urlparse

from app.extensions import db
from app.models import GmailAssistantSettings, GmailOAuthCredential, User
from app.services import gmail_oauth
from app.services import email_service
from app.services.email_service import OtpDeliveryError


def test_gmail_assistant_status_requires_admin(client, auth):
    assert client.get("/api/admin/gmail-assistant/status").status_code == 401
    assert client.get(
        "/api/admin/gmail-assistant/status", headers=auth("user")
    ).status_code == 403


def test_authorization_is_disabled_until_oauth_client_is_configured(client, auth, app):
    app.config["GMAIL_OAUTH_CLIENT_ID"] = ""
    app.config["GMAIL_OAUTH_CLIENT_SECRET"] = ""

    response = client.post(
        "/api/admin/gmail-assistant/authorize", headers=auth("admin"), json={}
    )

    assert response.status_code == 503
    assert response.get_json()["code"] == "GMAIL_OAUTH_NOT_CONFIGURED"


def test_admin_can_store_credentials_encrypted_without_returning_secrets(
    client, auth, app
):
    response = client.put(
        "/api/admin/gmail-assistant/settings",
        headers=auth("admin"),
        json={
            "oauth_client_id": "client-id-value",
            "oauth_client_secret": "oauth-secret-value",
            "oauth_redirect_uri": "http://127.0.0.1:5000/api/admin/gmail-assistant/callback",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 465,
            "smtp_username": "cinevoshop@gmail.com",
            "smtp_password": "smtp-app-password-value",
            "smtp_from_email": "cinevoshop@gmail.com",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["configured"] is True
    assert response.get_json()["smtp_configured"] is True
    assert "oauth-secret-value" not in response.get_data(as_text=True)
    assert "smtp-app-password-value" not in response.get_data(as_text=True)
    status = client.get(
        "/api/admin/gmail-assistant/status", headers=auth("admin")
    )
    assert status.status_code == 200
    assert "oauth-secret-value" not in status.get_data(as_text=True)
    assert "smtp-app-password-value" not in status.get_data(as_text=True)
    with app.app_context():
        row = db.session.get(GmailAssistantSettings, 1)
        assert "oauth-secret-value" not in row.encrypted_settings
        assert "smtp-app-password-value" not in row.encrypted_settings
        decrypted = gmail_oauth._decrypt_tokens(row.encrypted_settings)
        assert decrypted["oauth_client_secret"] == "oauth-secret-value"
        assert decrypted["smtp_password"] == "smtp-app-password-value"


def test_admin_settings_reject_non_gmail_smtp_hosts(client, auth):
    response = client.put(
        "/api/admin/gmail-assistant/settings",
        headers=auth("admin"),
        json={"smtp_host": "127.0.0.1"},
    )

    assert response.status_code == 400


def test_oauth_callback_encrypts_tokens_and_connects_sender(
    client, auth, app, monkeypatch
):
    app.config["GMAIL_OAUTH_CLIENT_ID"] = "test-client-id"
    app.config["GMAIL_OAUTH_CLIENT_SECRET"] = "test-client-secret"
    monkeypatch.setattr(
        gmail_oauth,
        "_exchange_code",
        lambda _code: {
            "access_token": "access-token-test",
            "refresh_token": "refresh-token-test",
            "scope": f"openid email {gmail_oauth.GMAIL_SEND_SCOPE}",
            "expires_in": 3600,
        },
    )
    monkeypatch.setattr(
        gmail_oauth,
        "_fetch_google_email",
        lambda _access_token: "cinevoshop@gmail.com",
    )

    authorized = client.post(
        "/api/admin/gmail-assistant/authorize", headers=auth("admin"), json={}
    )
    assert authorized.status_code == 200
    authorization_url = authorized.get_json()["authorization_url"]
    query = parse_qs(urlparse(authorization_url).query)
    assert gmail_oauth.GMAIL_SEND_SCOPE in query["scope"][0]
    assert "gmail.readonly" not in query["scope"][0]

    callback = client.post(
        "/api/admin/gmail-assistant/callback",
        data={"state": query["state"][0], "code": "oauth-code"},
    )
    assert callback.status_code == 302
    assert callback.headers["Location"].endswith("/admin/gmail-assistant?gmail=connected")
    connected = client.get(
        "/api/admin/gmail-assistant/status", headers=auth("admin")
    ).get_json()
    assert connected["configured"] is True
    assert connected["connected"] is True
    assert connected["sender_email"] == "cinevoshop@gmail.com"
    assert connected["delivery_mode"] == "GMAIL_OAUTH"

    with app.app_context():
        credential = db.session.get(GmailOAuthCredential, 1)
        assert "access-token-test" not in credential.encrypted_tokens
        assert "refresh-token-test" not in credential.encrypted_tokens


def test_connected_oauth_sender_is_used_for_otp_before_smtp(
    app, monkeypatch
):
    app.config["SMTP_USERNAME"] = "legacy@example.com"
    app.config["SMTP_PASSWORD"] = "legacy-app-password"
    sent = []
    monkeypatch.setattr(
        email_service,
        "send_otp_with_gmail_oauth",
        lambda email, code: sent.append((email, code)),
    )

    with app.app_context():
        db.session.add(GmailOAuthCredential(
            id=1,
            sender_email="cinevoshop@gmail.com",
            encrypted_tokens="encrypted",
        ))
        db.session.commit()
        assert email_service.is_email_delivery_configured()
        email_service.deliver_otp("customer@example.com", "482913")

    assert sent == [("customer@example.com", "482913")]


def test_configured_but_unconnected_oauth_does_not_fall_back_to_smtp(
    app, monkeypatch
):
    app.config["GMAIL_OAUTH_CLIENT_ID"] = "client-id"
    app.config["GMAIL_OAUTH_CLIENT_SECRET"] = "client-secret"
    app.config["SMTP_USERNAME"] = "legacy@example.com"
    app.config["SMTP_PASSWORD"] = "legacy-password"
    monkeypatch.setattr(
        email_service.smtplib,
        "SMTP_SSL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("must not attempt SMTP while OAuth is pending")
        ),
    )

    with app.app_context():
        user = User.query.filter_by(email="user@cinevo.vn").one()
        assert email_service.email_delivery_mode() == "GMAIL_OAUTH_PENDING"
        try:
            email_service.deliver_otp(user.email, "123456")
        except OtpDeliveryError as error:
            assert "chưa kết nối" in str(error).lower()
        else:
            raise AssertionError("OTP delivery must fail until OAuth is connected")
