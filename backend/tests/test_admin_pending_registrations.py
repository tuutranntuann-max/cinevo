from datetime import timedelta

from app.extensions import db
from app.models import OtpCode, User
from app.timeutil import utc_now
from tests.conftest import REGISTER


def test_pending_registration_status_is_admin_only_and_never_returns_otp(
    client, auth, register_payload,
):
    registration = client.post("/api/auth/register", json=register_payload)
    assert registration.status_code == 201

    assert client.get("/api/admin/pending-registrations").status_code == 401
    assert client.get("/api/admin/pending-registrations", headers=auth("user")).status_code == 403
    assert client.get("/api/admin/pending-registrations", headers=auth("manager")).status_code == 403

    response = client.get("/api/admin/pending-registrations", headers=auth("admin"))
    assert response.status_code == 200
    [pending] = response.get_json()
    assert pending["email"] == REGISTER["email"]
    assert pending["otp_status"] == "SENT"
    assert pending["otp_sent_at"]
    assert "code" not in pending
    assert "otp" not in pending


def test_admin_can_resend_registration_otp_without_receiving_code(
    client, app, auth, register_payload, monkeypatch,
):
    from app.services import auth_service

    registration = client.post("/api/auth/register", json=register_payload)
    assert registration.status_code == 201
    with app.app_context():
        user = User.query.filter_by(email=register_payload["email"]).one()
        user_id = user.id
        old_code = OtpCode.query.filter_by(user_id=user.id, purpose="REGISTER").one().code

    app.config.update({
        "SMTP_USERNAME": "sender@example.com",
        "SMTP_PASSWORD": "app-password",
        "SMTP_FROM_EMAIL": "sender@example.com",
    })
    monkeypatch.setattr(auth_service, "deliver_otp", lambda *_args: None)

    response = client.post(
        f"/api/admin/pending-registrations/{user_id}/resend-otp",
        headers=auth("admin"),
        json={},
    )
    assert response.status_code == 200
    assert "otp" not in response.get_json()
    assert "code" not in response.get_json()

    with app.app_context():
        user = User.query.filter_by(email=register_payload["email"]).one()
        codes = (
            OtpCode.query.filter_by(user_id=user.id, purpose="REGISTER")
            .order_by(OtpCode.id.desc())
            .all()
        )
        assert codes[0].code != old_code
        assert codes[1].used is True
        latest_code = codes[0].code

    expired = client.post(
        "/api/auth/verify-otp",
        json={"email": register_payload["email"], "code": old_code},
    )
    assert expired.status_code == 400
    verified = client.post(
        "/api/auth/verify-otp",
        json={"email": register_payload["email"], "code": latest_code},
    )
    assert verified.status_code == 200


def test_resend_otp_reports_delivery_failure_without_creating_a_code(
    client, app, auth, register_payload, monkeypatch,
):
    from app.services import email_service

    registration = client.post("/api/auth/register", json=register_payload)
    assert registration.status_code == 201
    with app.app_context():
        user = User.query.filter_by(email=register_payload["email"]).one()
        user_id = user.id
        original_count = OtpCode.query.filter_by(user_id=user.id, purpose="REGISTER").count()

    app.config.update({
        "SMTP_USERNAME": "sender@example.com",
        "SMTP_PASSWORD": "app-password",
        "SMTP_FROM_EMAIL": "sender@example.com",
    })

    def fail_delivery(*_args):
        raise email_service.OtpDeliveryError("SMTP unavailable")

    monkeypatch.setattr("app.services.auth_service.deliver_otp", fail_delivery)
    response = client.post(
        f"/api/admin/pending-registrations/{user_id}/resend-otp",
        headers=auth("admin"),
        json={},
    )
    assert response.status_code == 503
    with app.app_context():
        assert OtpCode.query.filter_by(user_id=user_id, purpose="REGISTER").count() == original_count


def test_pending_registration_marks_expired_otp(client, app, auth, register_payload):
    registration = client.post("/api/auth/register", json=register_payload)
    assert registration.status_code == 201
    with app.app_context():
        otp = OtpCode.query.one()
        otp.expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()

    response = client.get("/api/admin/pending-registrations", headers=auth("admin"))
    assert response.get_json()[0]["otp_status"] == "EXPIRED"
