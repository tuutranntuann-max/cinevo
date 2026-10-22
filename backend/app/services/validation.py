"""Validate đầu vào dùng chung + lỗi API thống nhất."""
import re

from flask import request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^(0|\+84)\d{9,10}$")


class ApiError(Exception):
    def __init__(self, message, status=400, code=None):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code


def json_body() -> dict:
    """Đọc JSON object. Body rỗng -> {}. JSON hỏng hoặc không phải object -> 400."""
    if not request.get_data():
        return {}
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Dữ liệu gửi lên không hợp lệ.", 400, "BAD_JSON")
    return data


def clean_str(value, label, *, min_len=0, max_len=200, required=False) -> str:
    if value is None or value == "":
        if required:
            raise ApiError(f"Vui lòng nhập {label}.")
        return ""
    if not isinstance(value, str):
        raise ApiError(f"{label} không hợp lệ.")
    value = value.strip()
    if required and not value:
        raise ApiError(f"Vui lòng nhập {label}.")
    if len(value) < min_len:
        raise ApiError(f"{label} quá ngắn (tối thiểu {min_len} ký tự).")
    if len(value) > max_len:
        raise ApiError(f"{label} quá dài (tối đa {max_len} ký tự).")
    return value


def clean_int(value, label, *, lo=None, hi=None) -> int:
    if isinstance(value, bool):
        raise ApiError(f"{label} không hợp lệ.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(f"{label} không hợp lệ.")
    if (lo is not None and number < lo) or (hi is not None and number > hi):
        raise ApiError(f"{label} nằm ngoài khoảng cho phép.")
    return number


def int_arg(name, default=None, *, lo=None, hi=None):
    """Đọc tham số query kiểu số nguyên; sai định dạng -> 400 thay vì lỗi 500."""
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    return clean_int(raw, name, lo=lo, hi=hi)
