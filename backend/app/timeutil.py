"""Quy ước thời gian của CINEVO (một nơi duy nhất, tránh lẫn lộn múi giờ).

- Mọi mốc hệ thống (created_at, paid_at, hạn OTP, log) lưu theo UTC, KHÔNG gắn tzinfo  -> utc_now().
- Giờ chiếu (Showtime.start_time) là giờ treo tường tại rạp ở Việt Nam (UTC+7, không có giờ mùa hè)
  -> so sánh bằng local_now(). Nhờ đó server đặt ở múi giờ nào cũng cho kết quả đúng.
"""
from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_now() -> datetime:
    return datetime.now(VN_TZ).replace(tzinfo=None)


def iso_utc(dt: datetime | None) -> str | None:
    """Chuỗi ISO có hậu tố Z để trình duyệt hiểu đúng là UTC."""
    return dt.isoformat() + "Z" if dt else None
