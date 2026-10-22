"""Publicly visible active discount codes."""
from flask import Blueprint, jsonify
from sqlalchemy import func

from ..models import Promotion
from ..services.auth_service import auth_required
from ..services.validation import ApiError, clean_str, json_body

bp = Blueprint("promotions", __name__, url_prefix="/api/promotions")


@bp.get("")
def list_active_promotions():
    promotions = Promotion.query.filter_by(active=True).order_by(Promotion.id.desc()).all()
    return jsonify([promotion.to_dict() for promotion in promotions])


@bp.post("/validate")
@auth_required
def validate_promotion():
    code = clean_str(json_body().get("code"), "mã giảm giá", max_len=30, required=True).upper()
    promotion = Promotion.query.filter(func.upper(Promotion.code) == code, Promotion.active.is_(True)).first()
    if not promotion:
        raise ApiError("Mã giảm giá không hợp lệ hoặc đã hết hiệu lực.", 400, "PROMOTION_INVALID")
    return jsonify(promotion.to_dict())
