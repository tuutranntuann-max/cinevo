"""Persisted site appearance configuration."""
from copy import deepcopy

from ..extensions import db


DEFAULT_APPEARANCE = {
    "accent_color": "#e11d2e",
    "page_color": "#080808",
    "surface_color": "#141414",
    "overlay_opacity": 0.45,
    "welcome_enabled": True,
    "welcome_title": "Chào mừng đến với CINEVO",
    "welcome_description": "Khám phá phim đang chiếu, chọn chỗ ngồi yêu thích và đặt vé nhanh chóng.",
    "welcome_button_text": "Vào xem phim",
    "title_font": "bebas",
    "title_size": 78,
    "title_frame": "none",
    "title_preset": "cinema",
    "title_motion": "bob",
    "footer_company_name": "CINEVO",
    "footer_tax_code": "0335823036",
    "footer_email": "tuutranntuann@gmail.com",
    "footer_license": "",
    "footer_registered": "",
    "footer_address": "",
    "footer_version": "v8.1",
    "footer_links": [
        {"label": "Về chúng tôi", "url": ""},
        {"label": "Chính sách bảo mật", "url": ""},
        {"label": "Hỗ trợ", "url": ""},
        {"label": "Liên hệ", "url": ""},
    ],
    "footer_partners": [
        {"name": "beta cinemas", "logo_url": "", "url": ""},
        {"name": "Mega GS", "logo_url": "", "url": ""},
        {"name": "CINESTAR", "logo_url": "", "url": ""},
        {"name": "DCINE", "logo_url": "", "url": ""},
        {"name": "CINEMAX", "logo_url": "", "url": ""},
        {"name": "STARLIGHT", "logo_url": "", "url": ""},
        {"name": "RIO", "logo_url": "", "url": ""},
        {"name": "DDC", "logo_url": "", "url": ""},
        {"name": "TOUCH CINEMA", "logo_url": "", "url": ""},
        {"name": "GALAXY", "logo_url": "", "url": ""},
        {"name": "AEON BETA", "logo_url": "", "url": ""},
        {"name": "AZ", "logo_url": "", "url": ""},
        {"name": "Payoo", "logo_url": "", "url": ""},
        {"name": "momo", "logo_url": "", "url": ""},
        {"name": "ZaloPay", "logo_url": "", "url": ""},
    ],
    "footer_partners_enabled": True,
    "footer_commerce_notice": "",
    "footer_show_upcoming": True,
}


def public_appearance_values(values):
    result = {key: value for key, value in (values or {}).items() if not key.endswith("_media_file")}
    for key, value in DEFAULT_APPEARANCE.items():
        if key not in result or (key == "footer_partners" and not result[key]):
            result[key] = deepcopy(value)
    for key in ("footer_tax_code", "footer_email"):
        if not result.get(key):
            result[key] = DEFAULT_APPEARANCE[key]
    return result


class AppearanceSettings(db.Model):
    __tablename__ = "appearance_settings"

    id = db.Column(db.Integer, primary_key=True, default=1)
    values = db.Column(db.JSON, nullable=False, default=dict)
