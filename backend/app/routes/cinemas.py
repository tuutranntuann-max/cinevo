"""API rạp và khu vực (công khai)."""
from flask import Blueprint, jsonify, request

from ..data.vietnam_provinces import province_catalog
from ..extensions import db
from ..models import Cinema
from ..data.vietnam_provinces import normalize_province, region_for_province

bp = Blueprint("cinemas", __name__, url_prefix="/api")


@bp.get("/provinces")
def provinces():
    return jsonify(province_catalog())


@bp.get("/cities")
def cities():
    rows = db.session.query(Cinema.city).distinct().order_by(Cinema.city).all()
    return jsonify([r[0] for r in rows])


@bp.get("/cinemas")
def list_cinemas():
    query = Cinema.query
    if city := request.args.get("city"):
        query = query.filter_by(city=city)
    return jsonify([
        {
            **cinema.to_dict(),
            "province": normalize_province(cinema.city) or cinema.city,
            "region": region_for_province(normalize_province(cinema.city) or ""),
        }
        for cinema in query.order_by(Cinema.name).all()
    ])
