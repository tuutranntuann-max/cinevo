"""Public editorial content and staff-managed promotions and events."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import CinemaEvent, NewsArticle, Promotion, ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER, log_activity
from ..services.auth_service import roles_required
from ..services.validation import ApiError, clean_int, clean_str, json_body
from ..timeutil import utc_now

bp = Blueprint("content_management", __name__, url_prefix="/api/content")
staff_editor = roles_required(ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE)
IMAGE_TYPES = {"jpg", "jpeg", "png", "webp"}
IMAGE_MIMETYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def _valid_image_signature(image, extension):
    if extension in {"jpg", "jpeg"}:
        return image.startswith(b"\xff\xd8\xff")
    if extension == "png":
        return image.startswith(b"\x89PNG\r\n\x1a\n")
    return len(image) >= 12 and image[:4] == b"RIFF" and image[8:12] == b"WEBP"


def _parse_datetime(value, label):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ApiError(f"{label} không hợp lệ.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApiError(f"{label} không hợp lệ.") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _boolean(data, key, default=None):
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ApiError("Trạng thái nội dung không hợp lệ.")
    return value


def _image_url(value):
    url = clean_str(value, "đường dẫn ảnh", max_len=500) or None
    if url and not (url.startswith("/api/content/media/") or url.startswith("https://")):
        raise ApiError("Ảnh cần được tải lên Cinevo hoặc dùng liên kết HTTPS.")
    return url


@bp.get("/news")
def public_news():
    articles = NewsArticle.query.filter(
        NewsArticle.active.is_(True),
        NewsArticle.published_at <= utc_now(),
    ).order_by(
        NewsArticle.published_at.desc(), NewsArticle.id.desc()
    ).limit(100).all()
    return jsonify([article.to_dict() for article in articles])


@bp.get("/events")
def public_events():
    now = utc_now()
    events = CinemaEvent.query.filter(
        CinemaEvent.active.is_(True),
        or_(CinemaEvent.starts_at.is_(None), CinemaEvent.starts_at <= now),
        or_(CinemaEvent.ends_at.is_(None), CinemaEvent.ends_at >= now),
    ).order_by(CinemaEvent.created_at.desc()).limit(100).all()
    return jsonify([event.to_dict() for event in events])


@bp.get("/manage/news")
@staff_editor
def list_news():
    articles = NewsArticle.query.order_by(NewsArticle.published_at.desc(), NewsArticle.id.desc()).all()
    return jsonify([article.to_dict() for article in articles])


@bp.post("/manage/news")
@staff_editor
def create_news():
    data = json_body()
    article = NewsArticle(
        title=clean_str(data.get("title"), "tiêu đề", max_len=200, required=True),
        summary=clean_str(data.get("summary"), "mô tả ngắn", max_len=500, required=True),
        body=clean_str(data.get("body"), "nội dung", max_len=20000, required=True),
        category=clean_str(data.get("category", "Tin điện ảnh"), "chủ đề", max_len=60, required=True),
        source=clean_str(data.get("source"), "nguồn tin", max_len=200) or None,
        image_url=_image_url(data.get("image_url")),
        active=_boolean(data, "active", True),
        published_at=_parse_datetime(data.get("published_at"), "ngày đăng") or utc_now(),
        created_by_id=g.current_user.id,
    )
    db.session.add(article)
    log_activity(g.current_user.id, "NEWS_CREATED", article.title)
    db.session.commit()
    return jsonify(article.to_dict()), 201


@bp.put("/manage/news/<int:article_id>")
@staff_editor
def update_news(article_id):
    article = db.session.get(NewsArticle, article_id)
    if not article:
        raise ApiError("Không tìm thấy tin tức.", 404)
    data = json_body()
    if "title" in data:
        article.title = clean_str(data["title"], "tiêu đề", max_len=200, required=True)
    if "summary" in data:
        article.summary = clean_str(data["summary"], "mô tả ngắn", max_len=500, required=True)
    if "body" in data:
        article.body = clean_str(data["body"], "nội dung", max_len=20000, required=True)
    if "category" in data:
        article.category = clean_str(data["category"], "chủ đề", max_len=60, required=True)
    if "source" in data:
        article.source = clean_str(data["source"], "nguồn tin", max_len=200) or None
    if "image_url" in data:
        article.image_url = _image_url(data["image_url"])
    if "active" in data:
        article.active = _boolean(data, "active")
    if "published_at" in data:
        article.published_at = _parse_datetime(data["published_at"], "ngày đăng") or utc_now()
    log_activity(g.current_user.id, "NEWS_UPDATED", article.title)
    db.session.commit()
    return jsonify(article.to_dict())


@bp.delete("/manage/news/<int:article_id>")
@staff_editor
def delete_news(article_id):
    article = db.session.get(NewsArticle, article_id)
    if not article:
        raise ApiError("Không tìm thấy tin tức.", 404)
    log_activity(g.current_user.id, "NEWS_DELETED", article.title)
    db.session.delete(article)
    db.session.commit()
    return jsonify({"message": "Đã xóa tin tức."})


@bp.get("/manage/events")
@staff_editor
def list_events():
    events = CinemaEvent.query.order_by(CinemaEvent.created_at.desc()).all()
    return jsonify([event.to_dict() for event in events])


@bp.post("/manage/events")
@staff_editor
def create_event():
    data = json_body()
    event = CinemaEvent(
        title=clean_str(data.get("title"), "tên sự kiện", max_len=200, required=True),
        summary=clean_str(data.get("summary"), "mô tả ngắn", max_len=500, required=True),
        body=clean_str(data.get("body"), "nội dung", max_len=20000) or None,
        image_url=_image_url(data.get("image_url")),
        starts_at=_parse_datetime(data.get("starts_at"), "thời gian bắt đầu"),
        ends_at=_parse_datetime(data.get("ends_at"), "thời gian kết thúc"),
        active=_boolean(data, "active", True),
    )
    if event.starts_at and event.ends_at and event.ends_at < event.starts_at:
        raise ApiError("Thời gian kết thúc không được trước thời gian bắt đầu.")
    event.created_by_id = g.current_user.id
    db.session.add(event)
    log_activity(g.current_user.id, "EVENT_CREATED", event.title)
    db.session.commit()
    return jsonify(event.to_dict()), 201


@bp.put("/manage/events/<int:event_id>")
@staff_editor
def update_event(event_id):
    event = db.session.get(CinemaEvent, event_id)
    if not event:
        raise ApiError("Không tìm thấy sự kiện.", 404)
    data = json_body()
    for key, label, maximum in (
        ("title", "tên sự kiện", 200),
        ("summary", "mô tả ngắn", 500),
    ):
        if key in data:
            setattr(event, key, clean_str(data[key], label, max_len=maximum, required=True))
    if "body" in data:
        event.body = clean_str(data["body"], "nội dung", max_len=20000) or None
    if "image_url" in data:
        event.image_url = _image_url(data["image_url"])
    if "active" in data:
        event.active = _boolean(data, "active")
    if "starts_at" in data:
        event.starts_at = _parse_datetime(data["starts_at"], "thời gian bắt đầu")
    if "ends_at" in data:
        event.ends_at = _parse_datetime(data["ends_at"], "thời gian kết thúc")
    if event.starts_at and event.ends_at and event.ends_at < event.starts_at:
        raise ApiError("Thời gian kết thúc không được trước thời gian bắt đầu.")
    log_activity(g.current_user.id, "EVENT_UPDATED", event.title)
    db.session.commit()
    return jsonify(event.to_dict())


@bp.delete("/manage/events/<int:event_id>")
@staff_editor
def delete_event(event_id):
    event = db.session.get(CinemaEvent, event_id)
    if not event:
        raise ApiError("Không tìm thấy sự kiện.", 404)
    log_activity(g.current_user.id, "EVENT_DELETED", event.title)
    db.session.delete(event)
    db.session.commit()
    return jsonify({"message": "Đã xóa sự kiện."})


@bp.get("/manage/promotions")
@staff_editor
def list_promotions():
    promotions = Promotion.query.order_by(Promotion.id.desc()).all()
    return jsonify([promotion.to_dict() for promotion in promotions])


@bp.post("/manage/promotions")
@staff_editor
def create_promotion():
    data = json_body()
    code = clean_str(data.get("code"), "mã giảm giá", max_len=30, required=True).upper()
    if Promotion.query.filter_by(code=code).first():
        raise ApiError("Mã giảm giá đã tồn tại.", 409, "PROMOTION_CODE_EXISTS")
    promotion = Promotion(
        code=code,
        description=clean_str(data.get("description"), "mô tả", max_len=250) or None,
        discount_percent=clean_int(data.get("discount_percent"), "phần trăm giảm", lo=1, hi=100),
        active=_boolean(data, "active", True),
        image_url=_image_url(data.get("image_url")),
    )
    db.session.add(promotion)
    log_activity(g.current_user.id, "PROMOTION_CREATED", promotion.code)
    db.session.commit()
    return jsonify(promotion.to_dict()), 201


@bp.put("/manage/promotions/<int:promotion_id>")
@staff_editor
def update_promotion(promotion_id):
    promotion = db.session.get(Promotion, promotion_id)
    if not promotion:
        raise ApiError("Không tìm thấy mã giảm giá.", 404)
    data = json_body()
    if "code" in data:
        code = clean_str(data["code"], "mã giảm giá", max_len=30, required=True).upper()
        if Promotion.query.filter(Promotion.code == code, Promotion.id != promotion_id).first():
            raise ApiError("Mã giảm giá đã tồn tại.", 409, "PROMOTION_CODE_EXISTS")
        promotion.code = code
    if "description" in data:
        promotion.description = clean_str(data["description"], "mô tả", max_len=250) or None
    if "discount_percent" in data:
        promotion.discount_percent = clean_int(data["discount_percent"], "phần trăm giảm", lo=1, hi=100)
    if "active" in data:
        promotion.active = _boolean(data, "active")
    if "image_url" in data:
        promotion.image_url = _image_url(data["image_url"])
    log_activity(g.current_user.id, "PROMOTION_UPDATED", promotion.code)
    db.session.commit()
    return jsonify(promotion.to_dict())


@bp.delete("/manage/promotions/<int:promotion_id>")
@staff_editor
def delete_promotion(promotion_id):
    promotion = db.session.get(Promotion, promotion_id)
    if not promotion:
        raise ApiError("Không tìm thấy mã giảm giá.", 404)
    log_activity(g.current_user.id, "PROMOTION_DELETED", promotion.code)
    db.session.delete(promotion)
    db.session.commit()
    return jsonify({"message": "Đã xóa mã giảm giá."})


@bp.post("/manage/media")
@staff_editor
def upload_content_image():
    upload = request.files.get("image")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn ảnh.")
    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension == "jfif":
        extension = "jpg"
    if extension not in IMAGE_TYPES:
        raise ApiError("Ảnh chỉ hỗ trợ định dạng JPG, PNG hoặc WEBP.")
    image = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(image) > 5 * 1024 * 1024:
        raise ApiError("Ảnh không được vượt quá 5 MB.")
    if not _valid_image_signature(image, extension):
        raise ApiError("Nội dung tệp không phải ảnh hợp lệ.")

    directory = Path(current_app.config["CONTENT_UPLOAD_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    file_name = f"content_{uuid4().hex}.{extension}"
    target = directory / file_name
    temporary = directory / f".{file_name}.tmp"
    try:
        temporary.write_bytes(image)
        temporary.replace(target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu ảnh nội dung.")
        raise ApiError("Không thể lưu ảnh. Vui lòng thử lại.", 500) from exc
    return jsonify({"image_url": f"/api/content/media/{file_name}"})


@bp.get("/media/<path:file_name>")
def serve_content_image(file_name):
    safe_name = secure_filename(file_name)
    if safe_name != file_name or not safe_name.startswith("content_"):
        raise ApiError("Không tìm thấy ảnh.", 404)
    extension = Path(safe_name).suffix.lower().lstrip(".")
    if extension not in IMAGE_TYPES:
        raise ApiError("Không tìm thấy ảnh.", 404)
    return send_from_directory(
        current_app.config["CONTENT_UPLOAD_DIR"],
        safe_name,
        mimetype=IMAGE_MIMETYPES[extension],
        conditional=True,
    )
