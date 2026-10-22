"""Gửi OTP qua SMTP; chỉ dùng mã giả lập trong development khi SMTP chưa cấu hình."""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app

from ..models import GmailOAuthCredential
from .gmail_oauth import (
    GmailOAuthError,
    delivery_settings,
    oauth_is_configured,
    send_otp as send_otp_with_gmail_oauth,
)

log = logging.getLogger(__name__)


class OtpDeliveryError(Exception):
    """Đã cấu hình dịch vụ gửi email nhưng không thể gửi mã OTP."""


def email_delivery_mode():
    if GmailOAuthCredential.query.get(1):
        return "GMAIL_OAUTH"
    if oauth_is_configured():
        return "GMAIL_OAUTH_PENDING"
    settings = delivery_settings()
    if settings["smtp_configured"]:
        return "SMTP"
    return "DEVELOPMENT"


def is_email_delivery_configured():
    return email_delivery_mode() != "DEVELOPMENT"


def deliver_otp(email: str, code: str) -> None:
    config = current_app.config
    if GmailOAuthCredential.query.get(1):
        try:
            send_otp_with_gmail_oauth(email, code)
        except GmailOAuthError as error:
            log.warning("Gmail OAuth could not deliver an OTP (%s).", type(error).__name__)
            raise OtpDeliveryError(str(error)) from error
        return

    if oauth_is_configured():
        raise OtpDeliveryError(
            "Gmail OAuth đã cấu hình nhưng chưa kết nối. Admin hãy bấm Kết nối Gmail "
            "và chấp thuận quyền gửi thư trước khi gửi OTP."
        )

    settings = delivery_settings()
    username = settings["smtp_username"].strip()
    password = settings["smtp_password"]
    if not username and not password:
        if config["IS_PRODUCTION"]:
            raise OtpDeliveryError("Chưa cấu hình dịch vụ gửi email OTP.")
        log.info("[DEV] Không gửi email OTP tới %s vì SMTP chưa được cấu hình.", email)
        return
    if not username or not password:
        raise OtpDeliveryError(
            "Chưa cấu hình đầy đủ Gmail SMTP. Hãy nhập email và App Password ở trang Trợ lý gửi OTP."
        )

    message = EmailMessage()
    message["Subject"] = "Mã xác thực đăng ký Cinevo"
    message["From"] = settings["smtp_from_email"]
    message["To"] = email
    message.set_content(
        f"Mã xác thực Cinevo của bạn là: {code}\n\n"
        "Mã có hiệu lực trong 10 phút và chỉ sử dụng được một lần. "
        "Nếu bạn không yêu cầu mã này, hãy bỏ qua email."
    )

    try:
        if int(settings["smtp_port"]) == 465:
            with smtplib.SMTP_SSL(
                settings["smtp_host"],
                int(settings["smtp_port"]),
                timeout=15,
                context=ssl.create_default_context(),
            ) as server:
                server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(settings["smtp_host"], int(settings["smtp_port"]), timeout=15) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(username, password)
                server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        log.exception("SMTP không gửi được mã OTP tới %s.", email)
        raise OtpDeliveryError("Không gửi được email xác thực. Vui lòng thử lại sau.") from error
