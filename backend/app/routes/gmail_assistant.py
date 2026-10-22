import hashlib

from flask import Blueprint, current_app, g, jsonify, redirect, request

from ..extensions import db
from ..models import GmailOAuthState
from ..services.auth_service import roles_required
from ..services.gmail_oauth import (
    GmailOAuthError,
    callback_frontend_url,
    complete_authorization,
    connection_status,
    create_authorization_url,
    clear_delivery_settings,
    revoke_connection,
    save_delivery_settings,
)
from ..services.validation import EMAIL_RE, ApiError, clean_str, json_body

bp = Blueprint("gmail_assistant", __name__, url_prefix="/api/admin/gmail-assistant")
admin_only = roles_required("ADMIN")


@bp.get("/status")
@admin_only
def status():
    return jsonify(connection_status())


@bp.put("/settings")
@admin_only
def update_settings():
    data = json_body()
    updates = {}
    for key, label, max_length in (
        ("oauth_client_id", "OAuth Client ID", 300),
        ("oauth_client_secret", "OAuth Client Secret", 500),
        ("oauth_redirect_uri", "OAuth Redirect URI", 500),
        ("oauth_frontend_url", "Frontend URL", 500),
        ("smtp_host", "SMTP host", 253),
        ("smtp_username", "SMTP email", 254),
        ("smtp_password", "SMTP App Password", 500),
        ("smtp_from_email", "Sender email", 254),
    ):
        if key in data:
            updates[key] = clean_str(
                data[key], label, max_len=max_length
            )
    if "smtp_port" in data:
        port = data["smtp_port"]
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ApiError("SMTP port phải là số từ 1 đến 65535.")
        updates["smtp_port"] = port
    if not updates:
        raise ApiError("Không có cấu hình nào để lưu.")
    if updates.get("oauth_redirect_uri") and not updates["oauth_redirect_uri"].startswith(
        ("http://127.0.0.1:", "http://localhost:", "https://")
    ):
        raise ApiError("OAuth Redirect URI phải dùng localhost hoặc HTTPS.")
    if updates.get("oauth_frontend_url") and not updates["oauth_frontend_url"].startswith(
        ("http://127.0.0.1:", "http://localhost:", "https://")
    ):
        raise ApiError("Frontend URL phải dùng localhost hoặc HTTPS.")
    for key in ("smtp_username", "smtp_from_email"):
        if updates.get(key) and not EMAIL_RE.fullmatch(updates[key]):
            raise ApiError(f"{key} không phải địa chỉ email hợp lệ.")
    if updates.get("smtp_host") and updates["smtp_host"].lower() != "smtp.gmail.com":
        raise ApiError("Trợ lý hiện chỉ hỗ trợ máy chủ smtp.gmail.com.")
    save_delivery_settings(updates)
    current_app.logger.info("Admin %s updated encrypted Gmail delivery settings.", g.current_user.id)
    return jsonify({"message": "Đã lưu cấu hình gửi email an toàn.", **connection_status()})


@bp.post("/settings/clear")
@admin_only
def clear_settings():
    data = json_body()
    oauth = data.get("oauth") is True
    smtp = data.get("smtp") is True
    if not oauth and not smtp:
        raise ApiError("Chọn loại cấu hình cần xóa.")
    clear_delivery_settings(oauth=oauth, smtp=smtp)
    return jsonify({"message": "Đã xóa cấu hình gửi email đã lưu.", **connection_status()})


@bp.post("/authorize")
@admin_only
def authorize():
    try:
        return jsonify({"authorization_url": create_authorization_url(g.current_user.id)})
    except GmailOAuthError as error:
        raise ApiError(str(error), 503, "GMAIL_OAUTH_NOT_CONFIGURED") from error


@bp.post("/disconnect")
@admin_only
def disconnect():
    try:
        revoke_connection()
    except GmailOAuthError as error:
        raise ApiError(str(error), 503, "GMAIL_DISCONNECT_FAILED") from error
    return jsonify({"message": "Đã ngắt kết nối Gmail."})


@bp.post("/callback")
def callback():
    state = request.form.get("state", "")
    if request.form.get("error"):
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        pending = db.session.get(GmailOAuthState, state_hash)
        if pending:
            db.session.delete(pending)
            db.session.commit()
        return redirect(_frontend_url("denied"))
    try:
        sender_email = complete_authorization(state, request.form.get("code", ""))
    except GmailOAuthError:
        current_app.logger.warning("Gmail OAuth connection was not completed.")
        return redirect(_frontend_url("error"))
    current_app.logger.info("Gmail OAuth connected for administrator %s.", sender_email)
    return redirect(_frontend_url("connected"))


def _frontend_url(result):
    return callback_frontend_url(result)
