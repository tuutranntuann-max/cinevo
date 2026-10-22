from ..extensions import db
from ..models import CommerceSettings
from .validation import ApiError


DEFAULT_COMMERCE_SETTINGS = {
    "bank_name": "",
    "bank_bin": "",
    "account_number": "",
    "account_name": "",
    "qr_image_url": "",
    "membership_prices": {"SILVER": None, "GOLD": None, "DIAMOND": None},
}


def get_commerce_settings():
    row = db.session.get(CommerceSettings, 1)
    if row is None:
        row = CommerceSettings(id=1, values=dict(DEFAULT_COMMERCE_SETTINGS))
        db.session.add(row)
        db.session.flush()
    values = dict(DEFAULT_COMMERCE_SETTINGS)
    values.update(row.values or {})
    prices = dict(DEFAULT_COMMERCE_SETTINGS["membership_prices"])
    prices.update((row.values or {}).get("membership_prices") or {})
    values["membership_prices"] = prices
    return row, values


def require_payment_configuration():
    _, values = get_commerce_settings()
    if not values.get("bank_bin") or not values.get("account_number"):
        raise ApiError("Admin chưa cấu hình ngân hàng và số tài khoản nhận tiền.", 503, "PAYMENT_NOT_CONFIGURED")
    return values
