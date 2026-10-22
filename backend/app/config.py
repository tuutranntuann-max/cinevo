"""Cấu hình ứng dụng. Giá trị đọc từ file .env (xem .env.example ở thư mục gốc).

APP_ENV=development (mặc định) hoặc production. Ở production, cấu hình không an toàn
(SECRET_KEY yếu, OTP cố định, debug...) sẽ bị TỪ CHỐI khởi động thay vì chạy âm thầm.
"""
import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent          # .../Cinevo/backend
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

APP_ENV = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV == "production"
INSECURE_SECRETS = {"", "dev-secret-change-me", "doi-chuoi-bi-mat-nay", "changeme", "secret"}
DEV_SECRET_FILE = BASE_DIR / "database" / ".dev_secret_key"


def resolve_secret_key(value: str | None, is_production: bool, dev_file: Path = DEV_SECRET_FILE) -> str:
    """Trả về SECRET_KEY an toàn.

    - Có khóa mạnh trong .env: dùng khóa đó.
    - Production mà thiếu/yếu: báo lỗi, không khởi động.
    - Development mà thiếu: tự sinh khóa ngẫu nhiên và lưu file riêng (không dùng chuỗi mặc định đoán được).
    """
    value = (value or "").strip()
    strong = value not in INSECURE_SECRETS and len(value) >= 32
    if strong:
        return value
    if is_production:
        raise RuntimeError("SECRET_KEY chưa đặt hoặc quá yếu. Tạo khóa: "
                           "python -c \"import secrets; print(secrets.token_hex(32))\"")
    if value not in INSECURE_SECRETS:   # dev: chấp nhận khóa ngắn do người dùng tự đặt
        return value
    if dev_file.exists():
        return dev_file.read_text().strip()
    key = secrets.token_hex(32)
    dev_file.write_text(key)
    logging.getLogger(__name__).warning("Đã sinh SECRET_KEY phát triển tại %s", dev_file)
    return key


def get_run_settings(env=None) -> tuple[str, int, bool]:
    """(host, port, debug) cho run.py. Debug chỉ bật ở development VÀ khi chỉ lắng nghe localhost,
    vì trình gỡ lỗi Werkzeug cho phép chạy code tùy ý nếu bị truy cập từ mạng."""
    env = os.environ if env is None else env
    host = env.get("HOST", "127.0.0.1")
    port = int(env.get("PORT", "5000"))
    debug = (not IS_PRODUCTION) and env.get("FLASK_DEBUG", "true").lower() == "true"
    if debug and host not in ("127.0.0.1", "localhost", "::1"):
        logging.getLogger(__name__).warning("Tắt debug vì HOST=%s không phải localhost.", host)
        debug = False
    return host, port, debug


class Config:
    APP_ENV = APP_ENV
    IS_PRODUCTION = IS_PRODUCTION
    SECRET_KEY = resolve_secret_key(os.getenv("SECRET_KEY"), IS_PRODUCTION)
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "24"))
    MAX_CONTENT_LENGTH = 1024 * 1024        # 1 MB: giới hạn chung cho API
    POSTER_MAX_CONTENT_LENGTH = 6 * 1024 * 1024  # 6 MB gồm overhead multipart, ảnh tối đa 5 MB
    MOVIE_IMPORT_MAX_CONTENT_LENGTH = 6 * 1024 * 1024  # file Excel/CSV tối đa 5 MB
    CINEMA_IMPORT_MAX_CONTENT_LENGTH = 6 * 1024 * 1024  # file Excel/CSV tối đa 5 MB
    TRAILER_MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024 + 1024 * 1024  # 10 GB video + multipart overhead
    FILM_MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024 + 1024 * 1024

    # SQLite mặc định. Sau này chỉ cần đổi DATABASE_URL sang PostgreSQL, ví dụ:
    # postgresql+psycopg2://user:pass@localhost:5432/cinevo
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'database' / 'cinevo.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POSTER_UPLOAD_DIR = BASE_DIR / "uploads" / "posters"
    TRAILER_UPLOAD_DIR = BASE_DIR / "uploads" / "trailers"
    FEATURE_FILM_UPLOAD_DIR = BASE_DIR / "uploads" / "films"
    APPEARANCE_UPLOAD_DIR = BASE_DIR / "uploads" / "appearance"
    CONTENT_UPLOAD_DIR = BASE_DIR / "uploads" / "content"
    AVATAR_UPLOAD_DIR = BASE_DIR / "uploads" / "avatars"
    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "cinevoshop@gmail.com").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "cinevoshop@gmail.com").strip() or SMTP_USERNAME
    GMAIL_OAUTH_CLIENT_ID = os.getenv("GMAIL_OAUTH_CLIENT_ID", "").strip()
    GMAIL_OAUTH_CLIENT_SECRET = os.getenv("GMAIL_OAUTH_CLIENT_SECRET", "").strip()
    GMAIL_OAUTH_REDIRECT_URI = os.getenv(
        "GMAIL_OAUTH_REDIRECT_URI",
        f"http://127.0.0.1:{os.getenv('PORT', '5000')}/api/admin/gmail-assistant/callback",
    ).strip()
    GMAIL_OAUTH_FRONTEND_URL = os.getenv("GMAIL_OAUTH_FRONTEND_URL", "http://localhost:5173").strip()

    # OTP: development dùng mã cố định cho dễ thử. Production luôn sinh mã ngẫu nhiên và KHÔNG trả mã ra API.
    MOCK_OTP_CODE = "" if IS_PRODUCTION else os.getenv("MOCK_OTP_CODE", "123456")
    OTP_DEBUG_HINT = (not IS_PRODUCTION) and os.getenv("OTP_DEBUG_HINT", "true").lower() == "true"

    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"

    # Tính năng AI: TẠM TẮT theo lộ trình hiện tại (chưa tích hợp AI).
    # Code trong app/ai/ được GIỮ LẠI để dùng sau; khi tắt thì không đăng ký route /api/ai/*,
    # endpoint admin AI trả 404 và giao diện tự ẩn các phần AI. Chỉ bật khi được cho phép: FEATURE_AI=true
    FEATURE_AI = os.getenv("FEATURE_AI", "false").lower() == "true"
