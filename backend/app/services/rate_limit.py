"""Giới hạn số lần gọi (in-memory, đủ cho 1 tiến trình).

GHI CHÚ TRIỂN KHAI: khi chạy nhiều worker/server (Phase 15) cần chuyển bộ đếm sang Redis
(ví dụ Flask-Limiter). Sau reverse proxy, phải cấu hình để request.remote_addr là IP thật của khách.
"""
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, request

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def reset():
    with _lock:
        _hits.clear()


def _client_ip():
    return request.remote_addr or "unknown"


def rate_limit(name, limit, window_seconds, key=None):
    """key(): hàm trả chuỗi định danh thêm (vd email). Mặc định chỉ theo IP."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_app.config.get("RATELIMIT_ENABLED", True):
                return fn(*args, **kwargs)
            ident = key() if key else _client_ip()
            bucket, now = f"{name}:{ident}", time.monotonic()
            with _lock:
                hits = _hits[bucket]
                while hits and now - hits[0] > window_seconds:
                    hits.popleft()
                if len(hits) >= limit:
                    retry = int(window_seconds - (now - hits[0])) + 1
                    resp = jsonify({"message": f"Thao tác quá nhiều lần. Vui lòng thử lại sau {retry} giây.",
                                    "code": "RATE_LIMITED"})
                    resp.status_code = 429
                    resp.headers["Retry-After"] = str(retry)
                    return resp
                hits.append(now)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def email_key():
    data = request.get_json(silent=True)
    email = data.get("email") if isinstance(data, dict) else ""
    return str(email or "").strip().lower()[:160]


def ip_and_email_key():
    return f"{_client_ip()}|{email_key()}"
