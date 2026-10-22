"""Encrypt staff identity details at rest and provide a keyed duplicate lookup."""
import base64
import hashlib
import hmac

from cryptography.fernet import Fernet
from flask import current_app


def _purpose_key(purpose):
    secret = current_app.config["SECRET_KEY"].encode("utf-8")
    digest = hmac.new(secret, purpose.encode("ascii"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_staff_data(value):
    return Fernet(_purpose_key("cinevo/staff-pii/encryption/v1")).encrypt(
        value.encode("utf-8")
    ).decode("ascii")


def decrypt_staff_data(value):
    return Fernet(_purpose_key("cinevo/staff-pii/encryption/v1")).decrypt(
        value.encode("ascii")
    ).decode("utf-8")


def staff_data_digest(value):
    return hmac.new(
        _purpose_key("cinevo/staff-pii/index/v1"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
