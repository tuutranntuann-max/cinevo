"""Fixture dùng chung. Mỗi test có một database SQLite riêng (file tạm) đã nạp dữ liệu demo."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("APP_ENV", "development")

from app import create_app                    # noqa: E402
from app.config import Config                 # noqa: E402
from app.extensions import db                 # noqa: E402
from app.services import rate_limit           # noqa: E402
from database.seed import seed_demo           # noqa: E402

ACCOUNTS = {"user": ("user@cinevo.vn", "User@123"),
            "manager": ("manager@cinevo.vn", "Manager@123"),
            "admin": ("admin@cinevo.vn", "Admin@123")}


def make_app(tmp_path, **overrides):
    attrs = {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
             "RATELIMIT_ENABLED": False, "TESTING": True,
             "SMTP_USERNAME": "", "SMTP_PASSWORD": "", "SMTP_FROM_EMAIL": "",
             "GMAIL_OAUTH_CLIENT_ID": "", "GMAIL_OAUTH_CLIENT_SECRET": "",
             **overrides}
    app = create_app(type("TestConfig", (Config,), attrs))
    with app.app_context():
        db.create_all()
        seed_demo()
    rate_limit.reset()
    return app


@pytest.fixture
def app(tmp_path):
    return make_app(tmp_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ai_client(tmp_path):
    """Ứng dụng đã BẬT cờ FEATURE_AI (mặc định tắt) để test riêng phần AI."""
    return make_app(tmp_path, FEATURE_AI=True).test_client()


@pytest.fixture
def tokens(client):
    out = {}
    for role, (email, pw) in ACCOUNTS.items():
        response = client.post("/api/auth/login", json={"email": email, "password": pw})
        out[role] = response.get_json()["token"]
    return out


@pytest.fixture
def auth(tokens):
    """auth('user') -> header Authorization. auth(None) -> không có header."""
    return lambda role: {"Authorization": f"Bearer {tokens[role]}"} if role else {}


REGISTER = {"full_name": "Pham Dat", "email": "dat@gmail.com", "phone": "0912345678",
            "password": "abc123", "confirm_password": "abc123", "accept_terms": True}


@pytest.fixture
def register_payload():
    return dict(REGISTER)


@pytest.fixture
def seat_info(client):
    """Một suất chiếu tương lai + danh sách ghế của nó."""
    sid = client.get("/api/showtimes?movie_id=1").get_json()[0]["id"]
    seats = client.get(f"/api/showtimes/{sid}/seats").get_json()["seats"]
    return sid, seats
