"""Restricted Gmail OAuth transport for registration OTP messages."""
import base64
import hashlib
import json
import logging
import secrets
import time
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from ..extensions import db
from ..models import (
    GmailAssistantSettings,
    GmailOAuthCredential,
    GmailOAuthState,
    ROLE_ADMIN,
    STATUS_ACTIVE,
    User,
)

log = logging.getLogger(__name__)

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_PROFILE_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
OAUTH_STATE_TTL_SECONDS = 600


class GmailOAuthError(Exception):
    """Safe-to-display Gmail OAuth or API error."""


def delivery_settings():
    stored = db.session.get(GmailAssistantSettings, 1)
    saved = _decrypt_tokens(stored.encrypted_settings) if stored else {}
    return {
        "oauth_client_id": saved.get("oauth_client_id", current_app.config.get("GMAIL_OAUTH_CLIENT_ID", "")),
        "oauth_client_secret": saved.get("oauth_client_secret", current_app.config.get("GMAIL_OAUTH_CLIENT_SECRET", "")),
        "oauth_redirect_uri": saved.get("oauth_redirect_uri", current_app.config["GMAIL_OAUTH_REDIRECT_URI"]),
        "oauth_frontend_url": saved.get("oauth_frontend_url", current_app.config["GMAIL_OAUTH_FRONTEND_URL"]),
        "smtp_host": saved.get("smtp_host", current_app.config["SMTP_HOST"]),
        "smtp_port": saved.get("smtp_port", current_app.config["SMTP_PORT"]),
        "smtp_username": saved.get("smtp_username", current_app.config["SMTP_USERNAME"]),
        "smtp_password": saved.get("smtp_password", current_app.config["SMTP_PASSWORD"]),
        "smtp_from_email": saved.get("smtp_from_email", current_app.config["SMTP_FROM_EMAIL"]),
        "smtp_configured": bool(
            saved.get("smtp_username", current_app.config["SMTP_USERNAME"])
            and saved.get("smtp_password", current_app.config["SMTP_PASSWORD"])
        ),
        "oauth_configured": bool(
            saved.get("oauth_client_id", current_app.config.get("GMAIL_OAUTH_CLIENT_ID"))
            and saved.get("oauth_client_secret", current_app.config.get("GMAIL_OAUTH_CLIENT_SECRET"))
            and saved.get("oauth_redirect_uri", current_app.config["GMAIL_OAUTH_REDIRECT_URI"])
        ),
        "oauth_client_id_configured": bool(
            saved.get("oauth_client_id", current_app.config.get("GMAIL_OAUTH_CLIENT_ID"))
        ),
        "oauth_client_secret_configured": bool(
            saved.get("oauth_client_secret", current_app.config.get("GMAIL_OAUTH_CLIENT_SECRET"))
        ),
    }


def save_delivery_settings(updates):
    settings = delivery_settings()
    for key, value in updates.items():
        if key in {"oauth_client_secret", "smtp_password"} and value == "":
            continue
        settings[key] = value
    row = db.session.get(GmailAssistantSettings, 1)
    if row is None:
        row = GmailAssistantSettings(id=1, encrypted_settings="")
        db.session.add(row)
    row.encrypted_settings = _encrypt_tokens(settings)
    db.session.commit()


def clear_delivery_settings(*, oauth=False, smtp=False):
    settings = delivery_settings()
    if oauth:
        settings["oauth_client_id"] = ""
        settings["oauth_client_secret"] = ""
        settings["oauth_redirect_uri"] = ""
    if smtp:
        settings["smtp_username"] = ""
        settings["smtp_password"] = ""
        settings["smtp_host"] = ""
        settings["smtp_port"] = ""
        settings["smtp_from_email"] = ""
    row = db.session.get(GmailAssistantSettings, 1)
    if row is None:
        return
    row.encrypted_settings = _encrypt_tokens(settings)
    db.session.commit()


def oauth_is_configured():
    return delivery_settings()["oauth_configured"]


def has_connected_account():
    return db.session.get(GmailOAuthCredential, 1) is not None


def _client_credentials():
    settings = delivery_settings()
    if not settings["oauth_configured"]:
        raise GmailOAuthError(
            "Hãy nhập OAuth Client ID và Client Secret trong trang Trợ lý gửi OTP."
        )
    return (
        settings["oauth_client_id"],
        settings["oauth_client_secret"],
        settings["oauth_redirect_uri"],
    )


def _cipher():
    key = hashlib.sha256(
        current_app.config["SECRET_KEY"].encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _encrypt_tokens(tokens):
    serialized = json.dumps(tokens, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _cipher().encrypt(serialized).decode("ascii")


def _decrypt_tokens(encrypted):
    try:
        return json.loads(_cipher().decrypt(encrypted.encode("ascii")))
    except (InvalidToken, UnicodeError, json.JSONDecodeError) as error:
        log.error("Gmail OAuth token could not be decrypted; check SECRET_KEY stability.")
        raise GmailOAuthError(
            "Không đọc được kết nối Gmail đã lưu. Hãy ngắt kết nối và kết nối lại."
        ) from error


def _request_json(url, *, data=None, headers=None, method=None):
    request = Request(
        url,
        data=data,
        headers=headers or {},
        method=method,
    )
    try:
        with urlopen(request, timeout=15) as response:
            content = response.read()
    except HTTPError as error:
        log.warning("Gmail OAuth request failed with HTTP %s.", error.code)
        raise GmailOAuthError("Google từ chối yêu cầu. Hãy thử kết nối Gmail lại.") from error
    except (OSError, URLError) as error:
        log.warning("Gmail OAuth request could not reach Google (%s).", type(error).__name__)
        raise GmailOAuthError("Không kết nối được dịch vụ Gmail. Vui lòng thử lại.") from error
    if not content:
        return {}
    try:
        return json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GmailOAuthError("Google trả về phản hồi không hợp lệ.") from error


def create_authorization_url(admin_user_id):
    client_id, _client_secret, redirect_uri = _client_credentials()
    state = secrets.token_urlsafe(32)
    now = int(time.time())
    GmailOAuthState.query.filter(GmailOAuthState.expires_at <= now).delete()
    db.session.add(GmailOAuthState(
        state_hash=hashlib.sha256(state.encode("utf-8")).hexdigest(),
        admin_user_id=admin_user_id,
        expires_at=now + OAUTH_STATE_TTL_SECONDS,
    ))
    db.session.commit()
    return OAUTH_AUTHORIZE_URL + "?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": f"openid email {GMAIL_SEND_SCOPE}",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "false",
        "response_mode": "form_post",
        "state": state,
    })


def _consume_state(state):
    if not state or len(state) > 200:
        raise GmailOAuthError("Yêu cầu kết nối Gmail không hợp lệ hoặc đã hết hạn.")
    state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
    record = db.session.get(GmailOAuthState, state_hash)
    if not record or record.expires_at < int(time.time()):
        if record:
            db.session.delete(record)
            db.session.commit()
        raise GmailOAuthError("Yêu cầu kết nối Gmail không hợp lệ hoặc đã hết hạn.")
    user = db.session.get(User, record.admin_user_id)
    db.session.delete(record)
    db.session.commit()
    if not user or user.status != STATUS_ACTIVE or user.role.name != ROLE_ADMIN:
        raise GmailOAuthError("Tài khoản quản trị không còn quyền kết nối Gmail.")
    return user


def _exchange_code(code):
    client_id, client_secret, redirect_uri = _client_credentials()
    return _request_json(
        OAUTH_TOKEN_URL,
        data=urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )


def _fetch_google_email(access_token):
    profile = _request_json(
        GMAIL_PROFILE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    email = profile.get("email", "").strip().lower()
    if not email or profile.get("verified_email") is False:
        raise GmailOAuthError("Không xác minh được địa chỉ Gmail đã kết nối.")
    return email


def complete_authorization(state, code):
    _consume_state(state)
    if not code or len(code) > 4096:
        raise GmailOAuthError("Google không trả về mã cấp quyền hợp lệ.")
    tokens = _exchange_code(code)
    if not tokens.get("access_token") or not tokens.get("refresh_token"):
        raise GmailOAuthError(
            "Google chưa cấp quyền duy trì kết nối. Hãy thử lại và chấp thuận quyền gửi thư."
        )
    if GMAIL_SEND_SCOPE not in tokens.get("scope", GMAIL_SEND_SCOPE):
        raise GmailOAuthError("Kết nối chưa được cấp quyền gửi thư Gmail.")
    email = _fetch_google_email(tokens["access_token"])
    tokens["expires_at"] = int(time.time()) + int(tokens.get("expires_in", 3600))
    credential = db.session.get(GmailOAuthCredential, 1)
    if credential is None:
        credential = GmailOAuthCredential(id=1, sender_email=email)
        db.session.add(credential)
    credential.sender_email = email
    credential.encrypted_tokens = _encrypt_tokens(tokens)
    db.session.commit()
    return email


def connection_status():
    credential = db.session.get(GmailOAuthCredential, 1)
    settings = delivery_settings()
    if credential:
        delivery_mode = "GMAIL_OAUTH"
    elif settings["oauth_configured"]:
        delivery_mode = "GMAIL_OAUTH_PENDING"
    elif settings["smtp_configured"]:
        delivery_mode = "SMTP"
    else:
        delivery_mode = "DEVELOPMENT"
    return {
        "configured": settings["oauth_configured"],
        "oauth_client_id_configured": settings["oauth_client_id_configured"],
        "oauth_client_secret_configured": settings["oauth_client_secret_configured"],
        "smtp_configured": settings["smtp_configured"],
        "delivery_mode": delivery_mode,
        "connected": credential is not None,
        "sender_email": credential.sender_email if credential else None,
    }


def _get_access_token():
    credential = db.session.get(GmailOAuthCredential, 1)
    if credential is None:
        raise GmailOAuthError("Chưa kết nối Gmail. Hãy kết nối tài khoản tại trang quản trị.")
    tokens = _decrypt_tokens(credential.encrypted_tokens)
    if tokens.get("access_token") and tokens.get("expires_at", 0) > int(time.time()) + 60:
        return tokens["access_token"]

    client_id, client_secret, _redirect_uri = _client_credentials()
    refreshed = _request_json(
        OAUTH_TOKEN_URL,
        data=urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": tokens.get("refresh_token", ""),
            "grant_type": "refresh_token",
        }).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    access_token = refreshed.get("access_token")
    if not access_token:
        raise GmailOAuthError("Kết nối Gmail hết hạn. Admin cần kết nối lại tài khoản.")
    tokens.update(refreshed)
    tokens["expires_at"] = int(time.time()) + int(refreshed.get("expires_in", 3600))
    credential.encrypted_tokens = _encrypt_tokens(tokens)
    db.session.commit()
    return access_token


def send_otp(email, code):
    message = EmailMessage()
    message["Subject"] = "Mã xác thực đăng ký Cinevo"
    message["To"] = email
    message.set_content(
        f"Mã xác thực Cinevo của bạn là: {code}\n\n"
        "Mã có hiệu lực trong 10 phút và chỉ sử dụng được một lần. "
        "Nếu bạn không yêu cầu mã này, hãy bỏ qua email."
    )
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
    _request_json(
        GMAIL_SEND_URL,
        data=json.dumps({"raw": raw}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_get_access_token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )


def revoke_connection():
    credential = db.session.get(GmailOAuthCredential, 1)
    if credential is None:
        return
    tokens = _decrypt_tokens(credential.encrypted_tokens)
    token = tokens.get("refresh_token") or tokens.get("access_token")
    if token:
        _request_json(
            OAUTH_REVOKE_URL,
            data=urlencode({"token": token}).encode("ascii"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    db.session.delete(credential)
    db.session.commit()


def callback_frontend_url(result):
    return delivery_settings()["oauth_frontend_url"].rstrip("/") + f"/admin/gmail-assistant?gmail={result}"
