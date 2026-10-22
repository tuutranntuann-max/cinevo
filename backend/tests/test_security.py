"""Cấu hình an toàn: secret, debug, OTP, rate limit, header."""
import pytest

from app.config import get_run_settings, resolve_secret_key
from tests.conftest import make_app


def test_production_rejects_missing_or_weak_secret(tmp_path):
    for bad in (None, "", "dev-secret-change-me", "ngan"):
        with pytest.raises(RuntimeError):
            resolve_secret_key(bad, True, tmp_path / "k")
    assert resolve_secret_key("a" * 40, True, tmp_path / "k") == "a" * 40


def test_dev_generates_random_persistent_secret_not_the_known_default(tmp_path):
    f = tmp_path / "k"
    k1 = resolve_secret_key("dev-secret-change-me", False, f)
    assert k1 != "dev-secret-change-me" and len(k1) >= 32
    assert resolve_secret_key(None, False, f) == k1      # dùng lại, không đổi mỗi lần chạy


def test_debug_only_on_localhost_and_never_in_production():
    assert get_run_settings({"HOST": "127.0.0.1"})[2] is True
    assert get_run_settings({"HOST": "0.0.0.0"})[2] is False
    assert get_run_settings({"HOST": "127.0.0.1", "FLASK_DEBUG": "false"})[2] is False


def test_otp_hint_hidden_when_disabled(tmp_path, register_payload):
    c = make_app(tmp_path, OTP_DEBUG_HINT=False).test_client()
    assert "otp_hint" not in c.post("/api/auth/register", json=register_payload).get_json()


def test_production_otp_is_random_not_fixed(tmp_path, register_payload):
    app = make_app(tmp_path, MOCK_OTP_CODE="", OTP_DEBUG_HINT=True)
    codes = set()
    for i in range(3):
        codes.add(app.test_client().post("/api/auth/register",
                  json={**register_payload, "email": f"u{i}@x.com"}).get_json()["otp_hint"])
    assert "123456" not in codes and len(codes) == 3


def test_login_rate_limited(tmp_path):
    c = make_app(tmp_path, RATELIMIT_ENABLED=True).test_client()
    codes = [c.post("/api/auth/login", json={"email": "user@cinevo.vn", "password": f"sai{i}"}).status_code for i in range(12)]
    assert codes[:10] == [401] * 10 and codes[10] == 429
    r = c.post("/api/auth/login", json={"email": "user@cinevo.vn", "password": "User@123"})
    assert r.status_code == 429 and "Retry-After" in r.headers          # đúng mật khẩu cũng bị chặn khi đã vượt giới hạn


def test_otp_brute_force_blocked(tmp_path, register_payload):
    c = make_app(tmp_path, RATELIMIT_ENABLED=True, MOCK_OTP_CODE="123456").test_client()
    c.post("/api/auth/register", json=register_payload)
    codes = [c.post("/api/auth/verify-otp", json={"email": register_payload["email"], "code": f"{i:06d}"}).status_code
             for i in range(7)]
    assert codes[:5] == [400] * 5 and codes[5:] == [429, 429]
    # sau khi bị khóa, ngay cả mã ĐÚNG cũng không dùng được
    assert c.post("/api/auth/verify-otp", json={"email": register_payload["email"], "code": "123456"}).status_code == 429


def test_security_headers_and_cors(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["X-Frame-Options"] == "DENY"
    evil = client.options("/api/movies", headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "GET"})
    assert evil.headers.get("Access-Control-Allow-Origin") is None


def test_request_body_size_limited(client):
    r = client.post("/api/auth/login", data="x" * (2 * 1024 * 1024), content_type="application/json")
    assert r.status_code == 413


def test_times_are_utc_marked(client, auth):
    assert client.get("/api/auth/me", headers=auth("user")).get_json()["user"]["created_at"].endswith("Z")
