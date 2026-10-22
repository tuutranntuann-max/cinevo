"""API cho ADMIN (quản trị hệ thống). Chỉ role ADMIN."""
from datetime import date, datetime, time, timedelta
from math import isfinite
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_

from ..extensions import db
from ..models import (ActivityLog, AppearanceSettings, Booking, BookingSeat, Cinema, Expense, Food, Movie, MovieCancellation, MovieFilm, MovieSubtitle, MovieTrailer, OtpCode, Payment, Product, Promotion,
                      ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_USER, Role, Room, Seat, Showtime, STATUS_ACTIVE, STATUS_LOCKED, STATUS_PENDING,
                      User, log_activity)
from ..models.appearance_settings import DEFAULT_APPEARANCE, public_appearance_values
from ..services.auth_service import issue_otp, roles_required
from ..services.cinema_import import parse_cinema_import
from ..services.email_service import OtpDeliveryError, email_delivery_mode
from ..services.movie_import import parse_movie_import
from ..services.rate_limit import rate_limit
from ..services.tmdb import POSTER_PATH_RE, TmdbError, download_poster, search_movie_posters
from ..services.validation import EMAIL_RE, PHONE_RE, ApiError, clean_int, clean_str, json_body
from flask import g
from ..data.vietnam_provinces import normalize_province, region_for_province
from ..timeutil import iso_utc, local_now, utc_now

bp = Blueprint("admin", __name__, url_prefix="/api/admin")
admin_only = roles_required(ROLE_ADMIN)
DEMO_PRIVILEGED_ACCOUNTS = {
    ("manager@cinevo.vn", "Quản lý Demo", ROLE_MANAGER),
    ("admin@cinevo.vn", "Admin Demo", ROLE_ADMIN),
}

# Cấu hình AI giả lập (lưu trong bộ nhớ). TODO: chuyển sang bảng settings trong DB.
AI_SETTINGS = {"provider": "mock", "recommendation_enabled": True, "chatbot_enabled": True, "seat_ai_enabled": True}


@bp.get("/dashboard")
@admin_only
def dashboard():
    total = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.status == "PAID").scalar()
    now = local_now()
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    utc_offset = timedelta(hours=7)
    query_start = min(year_start, week_start)
    utc_start = datetime.combine(query_start, time.min) - utc_offset
    utc_end = datetime.combine(today + timedelta(days=1), time.min) - utc_offset
    daily_revenue = (
        db.session.query(
            func.strftime("%Y-%m-%d", Payment.paid_at, "+7 hours").label("local_day"),
            func.sum(Payment.amount).label("amount"),
        )
        .filter(
            Payment.status == "PAID",
            Payment.paid_at.isnot(None),
            Payment.paid_at >= utc_start,
            Payment.paid_at < utc_end,
        )
        .group_by("local_day")
        .all()
    )
    daily_amounts = {
        date.fromisoformat(day): int(amount)
        for day, amount in daily_revenue
    }
    daily_expenses = (
        db.session.query(Expense.spent_on, func.sum(Expense.amount))
        .filter(Expense.spent_on >= query_start, Expense.spent_on <= today)
        .group_by(Expense.spent_on)
        .all()
    )
    expense_amounts = {day: int(amount) for day, amount in daily_expenses}

    def financial_series(start, labels, bucket_for):
        values = [
            {"label": label, "income": 0, "expense": 0, "profit": 0}
            for label in labels
        ]
        for source, key in ((daily_amounts, "income"), (expense_amounts, "expense")):
            for day, amount in source.items():
                if day < start or day > today:
                    continue
                index = bucket_for(day)
                values[index][key] += amount
        for item in values:
            item["profit"] = item["income"] - item["expense"]
        return {
            "income": sum(item["income"] for item in values),
            "expense": sum(item["expense"] for item in values),
            "profit": sum(item["profit"] for item in values),
            "items": values,
        }

    finance = {
        "week": financial_series(
            week_start,
            ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
            lambda day: day.weekday(),
        ),
        "month": financial_series(
            month_start,
            [f"Tuần {week}" for week in range(1, 6)],
            lambda day: (day.day - 1) // 7,
        ),
        "year": financial_series(
            year_start,
            ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
             "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"],
            lambda day: day.month - 1,
        ),
    }
    revenue = {
        period: {
            "total": series["income"],
            "items": [{"label": item["label"], "amount": item["income"]} for item in series["items"]],
        }
        for period, series in finance.items()
    }
    return jsonify({"stats": [
        {"label": "Người dùng", "value": User.query.count()},
        {"label": "Nhân viên & quản lý", "value": User.query.join(Role).filter(
            Role.name.in_((ROLE_MANAGER, ROLE_EMPLOYEE))
        ).count()},
        {"label": "Phim", "value": Movie.query.count()},
        {"label": "Giao dịch", "value": Payment.query.count()},
        {"label": "Tổng thu (đ)", "value": f"{total:,}".replace(",", ".")},
    ], "revenue": revenue, "finance": finance, "expenses": [
        expense.to_dict()
        for expense in Expense.query.order_by(Expense.spent_on.desc(), Expense.id.desc()).limit(50)
    ]})


@bp.post("/expenses")
@admin_only
def create_expense():
    data = json_body()
    try:
        spent_on = datetime.strptime(
            clean_str(data.get("spent_on"), "ngày chi", max_len=10, required=True),
            "%Y-%m-%d",
        ).date()
    except ValueError as error:
        raise ApiError("Ngày chi không hợp lệ.") from error
    expense = Expense(
        description=clean_str(data.get("description"), "nội dung", max_len=250, required=True),
        amount=clean_int(data.get("amount"), "số tiền", lo=1, hi=2_000_000_000),
        spent_on=spent_on,
        created_by_id=g.current_user.id,
    )
    db.session.add(expense)
    log_activity(g.current_user.id, "EXPENSE_CREATED", f"{expense.description}: {expense.amount}đ")
    db.session.commit()
    return jsonify(expense.to_dict()), 201


@bp.delete("/expenses/<int:expense_id>")
@admin_only
def delete_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        raise ApiError("Không tìm thấy khoản chi.", 404)
    log_activity(g.current_user.id, "EXPENSE_DELETED", f"{expense.description}: {expense.amount}đ")
    db.session.delete(expense)
    db.session.commit()
    return jsonify({"id": expense_id})


@bp.get("/users")
@admin_only
def users():
    last_logins = (
        db.session.query(
            ActivityLog.user_id.label("user_id"),
            func.max(ActivityLog.created_at).label("last_login_at"),
        )
        .filter(ActivityLog.action == "LOGIN")
        .group_by(ActivityLog.user_id)
        .subquery()
    )
    rows = (
        db.session.query(User, last_logins.c.last_login_at)
        .outerjoin(last_logins, last_logins.c.user_id == User.id)
        .order_by(User.id)
        .all()
    )
    result = []
    for user, last_login_at in rows:
        user_data = user.to_dict()
        user_data["last_login_at"] = iso_utc(last_login_at) if last_login_at else None
        result.append(user_data)
    return jsonify(result)


@bp.get("/pending-registrations")
@admin_only
def pending_registrations():
    users = (
        User.query.join(Role)
        .filter(User.status == STATUS_PENDING, Role.name == ROLE_USER)
        .order_by(User.created_at.desc(), User.id.desc())
        .all()
    )
    user_ids = [user.id for user in users]
    latest_otps = (
        OtpCode.query.filter(
            OtpCode.user_id.in_(user_ids),
            OtpCode.purpose == "REGISTER",
            OtpCode.used.is_(False),
        )
        .order_by(OtpCode.id.desc())
        .all()
    ) if user_ids else []
    otp_by_user = {}
    for otp in latest_otps:
        otp_by_user.setdefault(otp.user_id, otp)

    now = utc_now()
    return jsonify([
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "created_at": iso_utc(user.created_at),
            "otp_sent_at": iso_utc(otp.expires_at - timedelta(minutes=10)) if otp else None,
            "otp_expires_at": iso_utc(otp.expires_at) if otp else None,
            "otp_status": (
                "NOT_SENT" if not otp else "EXPIRED" if otp.expires_at <= now else "SENT"
            ),
            "delivery_mode": email_delivery_mode(),
        }
        for user in users
        for otp in [otp_by_user.get(user.id)]
    ])


@bp.post("/pending-registrations/<int:user_id>/resend-otp")
@admin_only
@rate_limit("admin-registration-otp-resend", 3, 600, key=lambda: str(request.view_args["user_id"]))
def resend_registration_otp(user_id):
    user = (
        User.query.join(Role)
        .filter(User.id == user_id, User.status == STATUS_PENDING, Role.name == ROLE_USER)
        .first()
    )
    if not user:
        raise ApiError("Không tìm thấy đăng ký đang chờ xác minh.", 404)
    try:
        issue_otp(user, "REGISTER")
    except OtpDeliveryError as error:
        db.session.rollback()
        raise ApiError(str(error), 503, "OTP_DELIVERY_FAILED") from error
    log_activity(g.current_user.id, "REGISTRATION_OTP_RESENT", user.email)
    db.session.commit()
    return jsonify({"message": "Đã gửi lại mã xác thực qua email khách hàng."})


@bp.patch("/users/<int:user_id>/status")
@admin_only
def set_status(user_id):
    user = db.session.get(User, user_id)
    status = json_body().get("status")
    if not user or status not in (STATUS_ACTIVE, STATUS_LOCKED):
        raise ApiError("Dữ liệu không hợp lệ.")
    if user.id == g.current_user.id:
        return jsonify({"message": "Không thể tự khóa tài khoản của mình."}), 400
    user.status = status
    log_activity(g.current_user.id, "USER_STATUS", f"{user.email} -> {status}")
    db.session.commit()
    return jsonify(user.to_dict())


@bp.delete("/users/<int:user_id>")
@admin_only
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise ApiError("Không tìm thấy tài khoản người dùng.", 404)
    if user.id == g.current_user.id:
        raise ApiError("Không thể xóa tài khoản đang đăng nhập.", 400)
    demo_account = (user.email, user.full_name, user.role.name if user.role else None)
    if not user.role or (user.role.name != "USER" and demo_account not in DEMO_PRIVILEGED_ACCOUNTS):
        raise ApiError("Chỉ có thể xóa tài khoản người dùng, không thể xóa Admin hoặc Manager.", 400)
    if Booking.query.filter_by(user_id=user.id).count():
        raise ApiError(
            "Tài khoản đã có lịch sử đặt vé nên không thể xóa để bảo toàn vé và giao dịch. "
            "Bạn có thể khóa tài khoản thay thế.",
            409,
        )

    email = user.email
    OtpCode.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    ActivityLog.query.filter_by(user_id=user.id).update(
        {ActivityLog.user_id: None},
        synchronize_session=False,
    )
    log_activity(g.current_user.id, "USER_DELETED", email)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"id": user_id, "message": "Đã xóa tài khoản người dùng."})


@bp.get("/managers")
@admin_only
def managers():
    return jsonify([
        u.to_dict()
        for u in User.query.join(Role).filter(Role.name.in_((ROLE_MANAGER, ROLE_EMPLOYEE))).all()
    ])


@bp.post("/managers")
@admin_only
def create_manager():
    raise ApiError(
        "Tài khoản nhân viên/quản lý phải được tạo qua hồ sơ và mã mời dùng một lần.",
        410,
        "INVITATION_REQUIRED",
    )


@bp.get("/movies")
@admin_only
def movies():
    movie_rows = Movie.query.order_by(Movie.id).all()
    today = local_now().date()
    cancelled_ids = {movie_id for (movie_id,) in db.session.query(MovieCancellation.movie_id).all()}
    booking_statuses = {}
    for movie_id, status in (
        db.session.query(Showtime.movie_id, Booking.status)
        .join(Booking, Booking.showtime_id == Showtime.id)
        .all()
    ):
        booking_statuses.setdefault(movie_id, []).append(status)
    future_showing_ids = {
        movie_id for (movie_id,) in db.session.query(Showtime.movie_id)
        .filter(Showtime.start_time >= local_now()).distinct().all()
    }
    past_showing_ids = {
        movie_id for (movie_id,) in db.session.query(Showtime.movie_id)
        .filter(Showtime.start_time < local_now()).distinct().all()
    }
    expired_ids = {
        movie.id for movie in movie_rows
        if (
            movie.status == "now_showing"
            and movie.id not in future_showing_ids
            and movie.theatrical_end_date is not None
            and movie.theatrical_end_date <= today
        )
    }
    return jsonify([
        {**movie.to_dict(),
         "subtitle_tracks": [subtitle.to_dict() for subtitle in movie.subtitles],
         "booking_count": len(booking_statuses.get(movie.id, [])),
         "cancelled_booking_count": sum(
             status == "CANCELLED" for status in booking_statuses.get(movie.id, [])
         ),
         "delete_allowed": (
             not any(status != "CANCELLED" for status in booking_statuses.get(movie.id, []))
             and (
                 movie.id in cancelled_ids
                 or (
                     bool(booking_statuses.get(movie.id))
                     and all(status == "CANCELLED" for status in booking_statuses[movie.id])
                 )
             )
         ),
         "cancelled": movie.id in cancelled_ids,
         "has_future_showtime": movie.id in future_showing_ids,
         "expired": movie.id in expired_ids,
         "watch_ready": (
             (
                 movie.status == "ended"
                 or (
                     movie.status == "now_showing"
                     and movie.id in past_showing_ids
                     and movie.id not in future_showing_ids
                 )
             )
             and movie.id not in cancelled_ids
             and movie.film is not None
             and (
                 movie.theatrical_end_date is None
                 or movie.theatrical_end_date <= today
             )
         ),
         "display_status": (
             "Đã hủy" if movie.id in cancelled_ids else
             "Bản nháp" if movie.status == "draft" else
             "Đã kết thúc công chiếu" if movie.status == "ended" else
             "Hết hạn" if movie.id in expired_ids else
             "Chưa có suất chiếu sắp tới" if (
                 movie.status == "now_showing" and movie.id not in future_showing_ids
             ) else
             "Đang chiếu" if movie.status == "now_showing" else "Sắp chiếu"
         )}
        for movie in movie_rows
    ])


@bp.delete("/movies/<int:movie_id>")
@admin_only
def delete_movie(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)

    bookings = (
        Booking.query.join(Showtime, Booking.showtime_id == Showtime.id)
        .filter(Showtime.movie_id == movie.id)
        .all()
    )
    active_bookings = [booking for booking in bookings if booking.status != "CANCELLED"]
    if active_bookings:
        raise ApiError(
            "Không thể xóa phim khi còn vé chưa hủy. Hãy hủy tất cả vé liên quan trước.",
            409,
        )

    cancellation = db.session.get(MovieCancellation, movie.id)
    if cancellation is None and not bookings:
        raise ApiError("Chỉ có thể xóa phim đã hủy hoặc phim có toàn bộ vé đã hủy.", 409)

    title = movie.title
    cancelled_booking_count = len(bookings)
    showtimes = Showtime.query.filter_by(movie_id=movie.id).all()
    trailer_files = []
    if movie.trailer:
        trailer_files.extend(
            file_name for file_name in (movie.trailer.file_name, movie.trailer.audio_file_name)
            if file_name
        )
    film_files = []
    if movie.film:
        film_files.extend(
            file_name for file_name in (movie.film.file_name, movie.film.image_file_name)
            if file_name
        )

    for booking in bookings:
        if booking.payment:
            db.session.delete(booking.payment)
        db.session.delete(booking)
    for showtime in showtimes:
        db.session.delete(showtime)
    if cancellation:
        db.session.delete(cancellation)

    title_logo_name = _movie_title_logo_file_name(movie.title_logo_url, movie_id)
    log_activity(
        g.current_user.id,
        "MOVIE_DELETED",
        f"{title}; vé đã hủy đã xóa: {cancelled_booking_count}",
    )
    db.session.delete(movie)
    db.session.commit()

    trailer_dir = Path(current_app.config["TRAILER_UPLOAD_DIR"])
    for file_name in set(trailer_files):
        _remove_trailer_file(trailer_dir / Path(file_name).name)
    film_dir = Path(current_app.config["FEATURE_FILM_UPLOAD_DIR"])
    for file_name in set(film_files):
        _remove_feature_film(film_dir / Path(file_name).name)
    poster_dir = Path(current_app.config["POSTER_UPLOAD_DIR"])
    for extension in ("jpg", "jpeg", "png", "webp"):
        _remove_feature_film(poster_dir / f"movie_{movie_id}.{extension}")
    if title_logo_name:
        _remove_feature_film(poster_dir / title_logo_name)

    return jsonify({
        "id": movie_id,
        "deleted_booking_count": cancelled_booking_count,
        "deleted_showtime_count": len(showtimes),
    })


@bp.patch("/movies/<int:movie_id>/watch-details")
@admin_only
def update_movie_watch_details(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
         raise ApiError("Không tìm thấy phim.", 404)
    data = json_body()
    try:
         release_date = (
             datetime.strptime(data["release_date"], "%Y-%m-%d").date()
             if data.get("release_date") else None
         )
         theatrical_end_date = movie.theatrical_end_date
         if "theatrical_end_date" in data:
             theatrical_end_date = (
                 datetime.strptime(data["theatrical_end_date"], "%Y-%m-%d").date()
                 if data.get("theatrical_end_date") else None
             )
    except (TypeError, ValueError):
         raise ApiError("Ngày khởi chiếu hoặc ngày kết thúc chiếu rạp không hợp lệ.")
    if release_date and theatrical_end_date and theatrical_end_date < release_date:
         raise ApiError("Ngày kết thúc chiếu rạp không được trước ngày ra phim.")
    movie.description = clean_str(data.get("description"), "mô tả", max_len=5000) or None
    movie.director = clean_str(data.get("director"), "đạo diễn/tác giả", max_len=120) or None
    movie.duration_minutes = clean_int(
         data.get("duration_minutes"), "thời lượng", lo=1, hi=600,
    )
    movie.release_date = release_date
    movie.theatrical_end_date = theatrical_end_date
    log_activity(g.current_user.id, "MOVIE_WATCH_DETAILS_UPDATED", movie.title)
    db.session.commit()
    return jsonify(movie.to_dict())


@bp.post("/movies/import")
@admin_only
def import_movies():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn file Excel .xlsx hoặc CSV.")
    extension = Path(upload.filename).suffix.lower().lstrip(".")
    if extension not in {"xlsx", "csv"}:
        raise ApiError("Chỉ hỗ trợ file Excel .xlsx hoặc CSV UTF-8.")
    content = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise ApiError("File nhập phim không được vượt quá 5 MB.")
    try:
        rows = parse_movie_import(content, extension)
    except ValueError as exc:
        raise ApiError(str(exc))

    existing_titles = {
        " ".join(title.casefold().split())
        for (title,) in db.session.query(Movie.title).all()
    }
    imported = []
    skipped_titles = []
    for row in rows:
        normalized_title = " ".join(row["title"].casefold().split())
        if normalized_title in existing_titles:
            skipped_titles.append(row["title"])
            continue
        existing_titles.add(normalized_title)
        imported.append(Movie(
            title=row["title"],
            genre=row["genre"],
            duration_minutes=row["duration_minutes"],
            age_rating=row["age_rating"],
            rating=0,
            director=row["director"],
            description=row["description"],
            release_date=row["release_date"],
            status="draft",
            poster_color="#7f1d1d",
        ))

    for movie in imported:
        db.session.add(movie)
        log_activity(g.current_user.id, "MOVIE_IMPORTED", movie.title)
    db.session.commit()
    return jsonify({
        "imported_count": len(imported),
        "skipped_count": len(skipped_titles),
        "skipped_titles": skipped_titles,
        "message": f"Đã nhập {len(imported)} phim vào bản nháp; bỏ qua {len(skipped_titles)} phim trùng.",
    })


@bp.patch("/movies/<int:movie_id>/status")
@admin_only
def set_movie_status(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    status = json_body().get("status")
    if status not in ("draft", "coming_soon", "now_showing", "ended"):
        raise ApiError("Trạng thái phim không hợp lệ.")
    previous_status = movie.status
    previous_end_date = movie.theatrical_end_date
    movie.status = status
    if status == "ended":
        movie.theatrical_end_date = local_now().date()
    elif (
        status == "now_showing"
        and movie.theatrical_end_date is not None
        and movie.theatrical_end_date <= local_now().date()
    ):
        movie.theatrical_end_date = None
    if previous_status != status or movie.theatrical_end_date != previous_end_date:
        log_activity(g.current_user.id, "MOVIE_STATUS", f"{movie.title}: {previous_status} -> {status}")
        db.session.commit()
    return jsonify(movie.to_dict())


@bp.patch("/movies/<int:movie_id>/cancellation")
@admin_only
def set_movie_cancellation(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    cancelled = json_body().get("cancelled")
    if not isinstance(cancelled, bool):
        raise ApiError("Trạng thái hủy phim không hợp lệ.")

    cancellation = db.session.get(MovieCancellation, movie.id)
    if cancelled and cancellation is None:
        cancellation = MovieCancellation(movie_id=movie.id, previous_status=movie.status)
        db.session.add(cancellation)
        log_activity(g.current_user.id, "MOVIE_CANCELLED", movie.title)
    elif not cancelled and cancellation is not None:
        db.session.delete(cancellation)
        log_activity(g.current_user.id, "MOVIE_RESTORED", movie.title)

    db.session.commit()
    return jsonify({"id": movie.id, "cancelled": cancelled})


@bp.post("/movies")
@admin_only
def create_movie():
    data = json_body()
    status = data.get("status", "coming_soon")
    if status not in ("now_showing", "coming_soon"):
        raise ApiError("Trạng thái phim không hợp lệ.")
    try:
        release_date = (
            datetime.strptime(data["release_date"], "%Y-%m-%d").date()
            if data.get("release_date") else None
        )
        theatrical_end_date = (
            datetime.strptime(data["theatrical_end_date"], "%Y-%m-%d").date()
            if data.get("theatrical_end_date") else None
        )
    except (TypeError, ValueError):
        raise ApiError("Ngày công chiếu hoặc ngày kết thúc công chiếu không hợp lệ.")
    if release_date and theatrical_end_date and theatrical_end_date < release_date:
        raise ApiError("Ngày kết thúc công chiếu không được trước ngày công chiếu.")
    movie = Movie(
        title=clean_str(data.get("title"), "tên phim", max_len=200, required=True),
        genre=clean_str(data.get("genre"), "thể loại", max_len=120) or None,
        duration_minutes=clean_int(data.get("duration_minutes", 120), "thời lượng", lo=1, hi=600),
        age_rating=clean_str(data.get("age_rating", "T13"), "phân loại tuổi", max_len=10) or "T13",
        rating=clean_int(data.get("rating", 0), "điểm đánh giá", lo=0, hi=10),
        director=clean_str(data.get("director"), "đạo diễn", max_len=120) or None,
        cast_members=clean_str(data.get("cast"), "diễn viên", max_len=500) or None,
        description=clean_str(data.get("description"), "mô tả", max_len=5000) or None,
        release_date=release_date,
        theatrical_end_date=theatrical_end_date,
        status=status,
        poster_color="#7f1d1d",
    )
    db.session.add(movie)
    db.session.flush()
    log_activity(g.current_user.id, "MOVIE_CREATED", movie.title)
    db.session.commit()
    return jsonify(movie.to_dict()), 201


@bp.patch("/movies/<int:movie_id>/details")
@admin_only
def update_movie_details(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    data = json_body()
    title = clean_str(data.get("title"), "tên phim", max_len=200, required=True)
    normalized_title = " ".join(title.casefold().split())
    if any(
        " ".join(existing.casefold().split()) == normalized_title
        for (existing,) in Movie.query.filter(Movie.id != movie.id).with_entities(Movie.title).all()
    ):
        raise ApiError("Tên phim đã tồn tại.", 409)

    age_rating = clean_str(data.get("age_rating", "T13"), "phân loại tuổi", max_len=10) or "T13"
    if age_rating not in {"P", "T13", "T16", "T18"}:
        raise ApiError("Phân loại tuổi phải là P, T13, T16 hoặc T18.")
    raw_rating = data.get("rating", 0)
    if isinstance(raw_rating, bool):
        raise ApiError("Điểm đánh giá không hợp lệ.")
    try:
        rating = float(raw_rating)
    except (TypeError, ValueError) as exc:
        raise ApiError("Điểm đánh giá không hợp lệ.") from exc
    if not isfinite(rating) or not 0 <= rating <= 10:
        raise ApiError("Điểm đánh giá nằm ngoài khoảng cho phép.")
    status = data.get("status")
    if status not in {"draft", "coming_soon", "now_showing", "ended"}:
        raise ApiError("Trạng thái phim không hợp lệ.")
    try:
        release_date = (
            datetime.strptime(data["release_date"], "%Y-%m-%d").date()
            if data.get("release_date") else None
        )
        theatrical_end_date = movie.theatrical_end_date
        if "theatrical_end_date" in data:
            theatrical_end_date = (
                datetime.strptime(data["theatrical_end_date"], "%Y-%m-%d").date()
                if data.get("theatrical_end_date") else None
            )
    except (TypeError, ValueError) as exc:
        raise ApiError("Ngày công chiếu hoặc ngày kết thúc công chiếu không hợp lệ.") from exc
    if release_date and theatrical_end_date and theatrical_end_date < release_date:
        raise ApiError("Ngày kết thúc công chiếu không được trước ngày công chiếu.")

    movie.title = title
    movie.genre = clean_str(data.get("genre"), "thể loại", max_len=120) or None
    movie.description = clean_str(data.get("description"), "mô tả", max_len=5000) or None
    movie.duration_minutes = clean_int(data.get("duration_minutes"), "thời lượng", lo=1, hi=600)
    movie.age_rating = age_rating
    movie.rating = rating
    movie.director = clean_str(data.get("director"), "đạo diễn/tác giả", max_len=120) or None
    movie.cast_members = clean_str(data.get("cast"), "diễn viên", max_len=500) or None
    movie.release_date = release_date
    if status == "ended":
        theatrical_end_date = local_now().date()
    elif (
        status == "now_showing"
        and theatrical_end_date is not None
        and theatrical_end_date <= local_now().date()
    ):
        theatrical_end_date = None
    movie.theatrical_end_date = theatrical_end_date
    movie.status = status
    log_activity(g.current_user.id, "MOVIE_DETAILS_UPDATED", movie.title)
    db.session.commit()
    return jsonify(movie.to_dict())


@bp.post("/movies/<int:movie_id>/poster")
@admin_only
def upload_movie_poster(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    upload = request.files.get("poster")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn ảnh poster.")

    safe_name = secure_filename(upload.filename)
    extension = Path(safe_name).suffix.lower().lstrip(".")
    if extension == "jfif":
        extension = "jpg"
    if extension not in {"jpg", "jpeg", "png", "webp"}:
        raise ApiError("Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.")
    image = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(image) > 5 * 1024 * 1024:
        raise ApiError("Ảnh poster không được vượt quá 5 MB.")
    if not _valid_image_signature(image, extension):
        raise ApiError("Nội dung tệp không phải ảnh hợp lệ.")

    _save_movie_poster(movie, image, extension, "MOVIE_POSTER_UPDATED")
    return jsonify(movie.to_dict())


@bp.post("/movies/<int:movie_id>/title-logo")
@admin_only
def upload_movie_title_logo(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    upload = request.files.get("logo")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn ảnh logo tên phim.")
    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension not in {"jpg", "jpeg", "png", "webp"}:
        raise ApiError("Logo tên phim chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.")
    image = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(image) > 5 * 1024 * 1024:
        raise ApiError("Ảnh logo tên phim không được vượt quá 5 MB.")
    if not _valid_image_signature(image, extension):
        raise ApiError("Nội dung tệp không phải ảnh hợp lệ.")

    upload_dir = Path(current_app.config["POSTER_UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"movie_{movie.id}_title_{uuid4().hex}.{extension}"
    target = upload_dir / file_name
    temporary = upload_dir / f".{file_name}.tmp"
    try:
        temporary.write_bytes(image)
        temporary.replace(target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu logo tên phim %s", movie.id)
        raise ApiError("Không thể lưu ảnh logo tên phim. Vui lòng thử lại.", 500) from exc

    previous_url = movie.title_logo_url
    movie.title_logo_url = f"/api/movies/{movie.id}/title-logo?format={extension}&v={file_name}"
    movie.title_logo_enabled = True
    log_activity(g.current_user.id, "MOVIE_TITLE_LOGO_UPDATED", movie.title)
    db.session.commit()
    previous_file = _movie_title_logo_file_name(previous_url, movie.id)
    if previous_file and previous_file != file_name:
        _remove_feature_film(upload_dir / previous_file)
    return jsonify(movie.to_dict())


@bp.patch("/movies/<int:movie_id>/title-logo")
@admin_only
def set_movie_title_logo_enabled(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    enabled = json_body().get("enabled")
    if not isinstance(enabled, bool):
        raise ApiError("Trạng thái logo tên phim không hợp lệ.")
    if enabled and not movie.title_logo_url:
        raise ApiError("Hãy tải ảnh logo tên phim lên trước.")
    movie.title_logo_enabled = enabled
    log_activity(g.current_user.id, "MOVIE_TITLE_LOGO_TOGGLED", f"{movie.title}: {enabled}")
    db.session.commit()
    return jsonify(movie.to_dict())


@bp.delete("/movies/<int:movie_id>/title-logo")
@admin_only
def delete_movie_title_logo(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    old_file = _movie_title_logo_file_name(movie.title_logo_url, movie.id)
    movie.title_logo_url = None
    movie.title_logo_enabled = False
    log_activity(g.current_user.id, "MOVIE_TITLE_LOGO_DELETED", movie.title)
    db.session.commit()
    if old_file:
        _remove_feature_film(Path(current_app.config["POSTER_UPLOAD_DIR"]) / old_file)
    return jsonify(movie.to_dict())


@bp.post("/movies/<int:movie_id>/poster/search")
@admin_only
def search_movie_tmdb_poster(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    api_key = current_app.config.get("TMDB_API_KEY", "").strip()
    if not api_key:
        raise ApiError(
            "Chưa cấu hình TMDB_API_KEY ở backend. Hãy thêm khóa TMDb vào file .env rồi khởi động lại máy chủ.",
            503,
        )
    try:
        candidates = search_movie_posters(movie.title, api_key)
    except TmdbError as exc:
        current_app.logger.warning("Không tìm được poster TMDb cho phim %s: %s", movie.id, exc)
        raise ApiError(str(exc), 502) from exc

    exact_match = next(
        (
            candidate for candidate in candidates
            if _normalize_movie_title(candidate["title"]) == _normalize_movie_title(movie.title)
            or _normalize_movie_title(candidate["original_title"]) == _normalize_movie_title(movie.title)
        ),
        None,
    )
    if exact_match:
        updated_movie = _apply_tmdb_poster(movie, exact_match["poster_path"])
        return jsonify({
            "auto_applied": True,
            "matched_title": exact_match["title"],
            "movie": updated_movie,
            "candidates": [],
            "attribution": "Poster từ TMDb",
        })
    return jsonify({
        "auto_applied": False,
        "matched_title": None,
        "movie": None,
        "candidates": candidates,
        "message": (
            "Không có tên phim khớp chính xác. Hãy chọn poster phù hợp bên dưới; "
            "poster chỉ được gắn vào phim sau khi bạn xác nhận."
            if candidates else "TMDb không tìm thấy poster cho phim này."
        ),
        "attribution": "Poster từ TMDb",
    })


@bp.post("/movies/<int:movie_id>/poster/tmdb")
@admin_only
def apply_movie_tmdb_poster(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    if not current_app.config.get("TMDB_API_KEY", "").strip():
        raise ApiError(
            "Chưa cấu hình TMDB_API_KEY ở backend. Hãy thêm khóa TMDb vào file .env rồi khởi động lại máy chủ.",
            503,
        )
    poster_path = json_body().get("poster_path")
    if not isinstance(poster_path, str) or not POSTER_PATH_RE.fullmatch(poster_path):
        raise ApiError("Poster được chọn không hợp lệ.")
    return jsonify(_apply_tmdb_poster(movie, poster_path))


@bp.post("/movies/<int:movie_id>/film")
@admin_only
def upload_movie_film(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    upload = request.files.get("film")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn tệp phim.")
    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension not in {"mp4", "webm"}:
        raise ApiError("Phim chỉ hỗ trợ định dạng MP4 hoặc WebM.")
    if not _valid_video_signature(upload.stream.read(16), extension):
        raise ApiError("Nội dung tệp không đúng định dạng video MP4 hoặc WebM.")

    upload_dir = Path(current_app.config["FEATURE_FILM_UPLOAD_DIR"])
    file_name, _ = _store_feature_film(upload, upload_dir, movie.id, extension)
    previous_file = movie.film.file_name if movie.film else None
    if movie.film:
        movie.film.extension = extension
        movie.film.file_name = file_name
        movie.film.updated_at = utc_now()
    else:
        movie.film = MovieFilm(movie_id=movie.id, extension=extension, file_name=file_name)
    log_activity(g.current_user.id, "MOVIE_FILM_UPDATED", movie.title)
    db.session.commit()
    if previous_file:
        _remove_feature_film(upload_dir / previous_file)
    return jsonify(movie.to_dict())


@bp.delete("/movies/<int:movie_id>/film")
@admin_only
def delete_movie_film(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.film:
        raise ApiError("Phim chưa có bản xem trực tuyến.", 404)
    file_name = movie.film.file_name
    image_file_name = movie.film.image_file_name
    db.session.delete(movie.film)
    log_activity(g.current_user.id, "MOVIE_FILM_DELETED", movie.title)
    db.session.commit()
    upload_dir = Path(current_app.config["FEATURE_FILM_UPLOAD_DIR"])
    _remove_feature_film(upload_dir / file_name)
    if image_file_name:
        _remove_feature_film(upload_dir / image_file_name)
    return jsonify(movie.to_dict())


@bp.post("/movies/<int:movie_id>/film-image")
@admin_only
def upload_movie_film_image(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    if not movie.film:
        raise ApiError("Hãy tải bản phim lên trước khi thêm ảnh.", 409)
    upload = request.files.get("image")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn ảnh đại diện phim.")

    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension not in {"jpg", "jpeg", "png", "webp"}:
        raise ApiError("Ảnh phim chỉ hỗ trợ JPG, PNG hoặc WEBP.")
    image = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(image) > 5 * 1024 * 1024:
        raise ApiError("Ảnh phim không được vượt quá 5 MB.")
    if not _valid_image_signature(image, extension):
        raise ApiError("Nội dung tệp không phải ảnh hợp lệ.")

    upload_dir = Path(current_app.config["FEATURE_FILM_UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"film_{movie.id}_{uuid4().hex}.{extension}"
    target = upload_dir / file_name
    temporary = upload_dir / f".film_{movie.id}_{uuid4().hex}.tmp"
    try:
        temporary.write_bytes(image)
        temporary.replace(target)
    except OSError:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu ảnh phim %s", movie.id)
        raise ApiError("Không thể lưu ảnh phim. Vui lòng thử lại.", 500)

    previous_file = movie.film.image_file_name
    movie.film.image_extension = extension
    movie.film.image_file_name = file_name
    movie.film.updated_at = utc_now()
    log_activity(g.current_user.id, "MOVIE_FILM_IMAGE_UPDATED", movie.title)
    db.session.commit()
    if previous_file:
        _remove_feature_film(upload_dir / previous_file)
    return jsonify(movie.to_dict())


def _subtitle_language(value):
    language = clean_str(value or "vi", "ngôn ngữ phụ đề", max_len=35, required=True)
    if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
        raise ApiError("Mã ngôn ngữ phụ đề không hợp lệ, ví dụ vi hoặc en.")
    return language


def _subtitle_label(value, language):
    return clean_str(value or language.upper(), "tên phụ đề", max_len=80, required=True)


def _srt_to_vtt(contents):
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ApiError("Tệp phụ đề phải được mã hóa UTF-8.") from error
    if "\x00" in text:
        raise ApiError("Tệp phụ đề không hợp lệ.")
    timestamp = re.compile(
        r"^(\s*\d{2}:\d{2}:\d{2}),(\d{3})(\s+-->\s+)"
        r"(\d{2}:\d{2}:\d{2}),(\d{3})(.*)$"
    )
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    converted = []
    cue_count = 0
    for line in lines:
        match = timestamp.match(line)
        if match:
            cue_count += 1
            line = (
                f"{match.group(1)}.{match.group(2)}{match.group(3)}"
                f"{match.group(4)}.{match.group(5)}{match.group(6)}"
            )
        converted.append(line)
    if not cue_count:
        raise ApiError("Tệp SRT không có mốc thời gian phụ đề hợp lệ.")
    return ("WEBVTT\n\n" + "\n".join(converted).strip() + "\n").encode("utf-8")


@bp.post("/movies/<int:movie_id>/subtitles")
@admin_only
def upload_movie_subtitle(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    upload = request.files.get("subtitle")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn tệp phụ đề VTT hoặc SRT.")
    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension not in {"vtt", "srt"}:
        raise ApiError("Phụ đề chỉ hỗ trợ định dạng VTT hoặc SRT.")
    contents = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(contents) > 5 * 1024 * 1024:
        raise ApiError("Tệp phụ đề không được vượt quá 5 MB.")
    if extension == "srt":
        contents = _srt_to_vtt(contents)
    else:
        try:
            text = contents.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ApiError("Tệp phụ đề phải được mã hóa UTF-8.") from error
        if "\x00" in text or not text.lstrip().startswith("WEBVTT"):
            raise ApiError("Tệp VTT không có tiêu đề WEBVTT hợp lệ.")
        contents = (text.lstrip("\ufeff").rstrip() + "\n").encode("utf-8")

    language = _subtitle_language(request.form.get("language"))
    label = _subtitle_label(request.form.get("label"), language)
    upload_dir = Path(current_app.config["FEATURE_FILM_UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"subtitle_{movie.id}_{uuid4().hex}.vtt"
    target = upload_dir / file_name
    temporary = upload_dir / f".subtitle_{movie.id}_{uuid4().hex}.tmp"
    try:
        temporary.write_bytes(contents)
        temporary.replace(target)
    except OSError:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu phụ đề phim %s", movie.id)
        raise ApiError("Không thể lưu phụ đề. Vui lòng thử lại.", 500)

    subtitle = MovieSubtitle(
        movie_id=movie.id,
        label=label,
        language=language,
        source_type="upload",
        file_name=file_name,
    )
    db.session.add(subtitle)
    log_activity(g.current_user.id, "MOVIE_SUBTITLE_ADDED", f"{movie.title}: {label}")
    db.session.commit()
    return jsonify(subtitle.to_dict()), 201


@bp.post("/movies/<int:movie_id>/subtitles/url")
@admin_only
def add_movie_subtitle_url(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    data = json_body()
    source_url = clean_str(data.get("url"), "đường dẫn phụ đề", max_len=2048, required=True)
    parsed_url = urlparse(source_url)
    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
    ):
        raise ApiError("Đường dẫn phụ đề phải là URL HTTPS công khai hợp lệ.")
    language = _subtitle_language(data.get("language"))
    label = _subtitle_label(data.get("label"), language)
    subtitle = MovieSubtitle(
        movie_id=movie.id,
        label=label,
        language=language,
        source_type="url",
        source_url=source_url,
    )
    db.session.add(subtitle)
    log_activity(g.current_user.id, "MOVIE_SUBTITLE_ADDED", f"{movie.title}: {label}")
    db.session.commit()
    return jsonify(subtitle.to_dict()), 201


@bp.delete("/movies/<int:movie_id>/subtitles/<int:subtitle_id>")
@admin_only
def delete_movie_subtitle(movie_id, subtitle_id):
    subtitle = db.session.get(MovieSubtitle, subtitle_id)
    if not subtitle or subtitle.movie_id != movie_id:
        raise ApiError("Không tìm thấy phụ đề của phim.", 404)
    file_name = subtitle.file_name
    log_activity(g.current_user.id, "MOVIE_SUBTITLE_DELETED", subtitle.label)
    db.session.delete(subtitle)
    db.session.commit()
    if file_name:
        _remove_feature_film(Path(current_app.config["FEATURE_FILM_UPLOAD_DIR"]) / file_name)
    return jsonify({"message": "Đã xóa phụ đề."})


def _store_feature_film(upload, upload_dir, movie_id, extension):
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"film_{movie_id}_{uuid4().hex}.{extension}"
    target = upload_dir / file_name
    temporary = upload_dir / f".film_{movie_id}_{uuid4().hex}.tmp"
    upload.stream.seek(0)
    size = 0
    try:
        with temporary.open("wb") as destination:
            while chunk := upload.stream.read(1024 * 1024):
                size += len(chunk)
                if size > 10 * 1024 * 1024 * 1024:
                    raise ApiError("Tệp phim không được vượt quá 10 GB.")
                destination.write(chunk)
        temporary.replace(target)
    except ApiError:
        temporary.unlink(missing_ok=True)
        raise
    except OSError:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu tệp phim %s", movie_id)
        raise ApiError("Không thể lưu tệp phim. Hãy kiểm tra dung lượng ổ đĩa và thử lại.", 500)
    return file_name, target


def _remove_feature_film(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        current_app.logger.exception("Không thể dọn tệp phim cũ: %s", path.name)


def _valid_image_signature(image, extension):
    if extension in {"jpg", "jpeg"}:
        return image.startswith(b"\xff\xd8\xff")
    if extension == "png":
        return image.startswith(b"\x89PNG\r\n\x1a\n")
    return len(image) >= 12 and image.startswith(b"RIFF") and image[8:12] == b"WEBP"


def _normalize_movie_title(title):
    return " ".join((title or "").casefold().split())


def _apply_tmdb_poster(movie, poster_path):
    try:
        image, extension = download_poster(poster_path)
    except TmdbError as exc:
        current_app.logger.warning("Không tải được poster TMDb cho phim %s: %s", movie.id, exc)
        raise ApiError(str(exc), 502) from exc

    _save_movie_poster(movie, image, extension, "MOVIE_POSTER_TMDB_APPLIED")
    return movie.to_dict()


def _save_movie_poster(movie, image, extension, action):
    upload_dir = Path(current_app.config["POSTER_UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"movie_{movie.id}_{uuid4().hex}.{extension}"
    target = upload_dir / file_name
    temporary = upload_dir / f".{file_name}.tmp"
    try:
        temporary.write_bytes(image)
        temporary.replace(target)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu poster phim %s", movie.id)
        raise ApiError("Không thể lưu ảnh poster. Vui lòng thử lại.", 500) from exc

    previous_url = movie.poster_url
    movie.poster_url = f"/api/movies/{movie.id}/poster?format={extension}&v={file_name}"
    log_activity(g.current_user.id, action, movie.title)
    db.session.commit()
    previous_query = parse_qs(urlparse(previous_url or "").query)
    previous_version = previous_query.get("v", [""])[0]
    if re.fullmatch(rf"movie_{movie.id}_[0-9a-f]{{32}}\.(?:jpg|jpeg|png|webp)", previous_version):
        previous_file = previous_version
    else:
        previous_extension = previous_query.get("format", [""])[0]
        previous_file = (
            f"movie_{movie.id}.{previous_extension}"
            if previous_extension in {"jpg", "jpeg", "png", "webp"}
            else None
        )
    if previous_file and previous_file != file_name:
        try:
            (upload_dir / previous_file).unlink(missing_ok=True)
        except OSError:
            current_app.logger.warning("Không thể xóa poster cũ của phim %s", movie.id, exc_info=True)


def _movie_title_logo_file_name(url, movie_id):
    query = parse_qs(urlparse(url or "").query)
    version = query.get("v", [""])[0]
    if re.fullmatch(rf"movie_{movie_id}_title_[0-9a-f]{{32}}\.(?:jpg|jpeg|png|webp)", version):
        return version
    return None


@bp.post("/movies/<int:movie_id>/trailer")
@admin_only
def upload_movie_trailer(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    upload = request.files.get("trailer")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn video trailer.")

    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension not in {"mp4", "webm"}:
        raise ApiError("Video trailer chỉ hỗ trợ MP4 hoặc WebM.")
    header = upload.stream.read(16)
    if not _valid_video_signature(header, extension):
        raise ApiError("Nội dung tệp không đúng định dạng video MP4 hoặc WebM.")

    upload_dir = Path(current_app.config["TRAILER_UPLOAD_DIR"])
    file_name, target = _store_trailer_upload(upload, upload_dir, movie.id, extension)
    trailer = movie.trailer
    previous_video = None
    if trailer:
        if trailer.extension == "mp3":
            trailer.audio_file_name = trailer.audio_file_name or trailer.file_name
        else:
            previous_video = trailer.file_name
        trailer.extension = extension
        trailer.file_name = file_name
        trailer.updated_at = utc_now()
    else:
        movie.trailer = MovieTrailer(movie_id=movie.id, extension=extension, file_name=file_name)
    log_activity(g.current_user.id, "MOVIE_TRAILER_UPDATED", movie.title)
    db.session.commit()
    if previous_video:
        _remove_trailer_file(upload_dir / previous_video)
    return jsonify(movie.to_dict())


@bp.post("/movies/<int:movie_id>/audio")
@admin_only
def upload_movie_audio(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    upload = request.files.get("audio")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn tệp âm thanh MP3.")
    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension != "mp3":
        raise ApiError("Âm thanh trailer chỉ hỗ trợ MP3.")
    if not _valid_trailer_signature(upload.stream.read(16), extension):
        raise ApiError("Nội dung tệp không đúng định dạng MP3.")

    upload_dir = Path(current_app.config["TRAILER_UPLOAD_DIR"])
    file_name, _ = _store_trailer_upload(upload, upload_dir, movie.id, extension)
    trailer = movie.trailer
    previous_audio = None
    if trailer and trailer.extension in {"mp4", "webm"}:
        previous_audio = trailer.audio_file_name
        trailer.audio_file_name = file_name
        trailer.updated_at = utc_now()
    elif trailer:
        previous_audio = trailer.file_name
        trailer.extension = "mp3"
        trailer.file_name = file_name
        trailer.updated_at = utc_now()
    else:
        movie.trailer = MovieTrailer(movie_id=movie.id, extension="mp3", file_name=file_name)
    log_activity(g.current_user.id, "MOVIE_TRAILER_AUDIO_UPDATED", movie.title)
    db.session.commit()
    if previous_audio:
        _remove_trailer_file(upload_dir / previous_audio)
    return jsonify(movie.to_dict())


@bp.delete("/movies/<int:movie_id>/trailer")
@admin_only
def delete_movie_trailer(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    if not movie.trailer:
        raise ApiError("Phim chưa có video trailer.", 404)
    trailer = movie.trailer
    if trailer.extension == "mp3":
        raise ApiError("Phim chưa có video trailer để xóa.", 404)
    file_name = trailer.file_name
    if trailer.audio_file_name:
        audio_file = trailer.audio_file_name
        trailer.extension = "mp3"
        trailer.file_name = audio_file
        trailer.audio_file_name = None
        trailer.updated_at = utc_now()
    else:
        db.session.delete(trailer)
    log_activity(g.current_user.id, "MOVIE_TRAILER_DELETED", movie.title)
    db.session.commit()
    _remove_trailer_file(Path(current_app.config["TRAILER_UPLOAD_DIR"]) / file_name)
    return jsonify(movie.to_dict())


@bp.delete("/movies/<int:movie_id>/audio")
@admin_only
def delete_movie_audio(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.trailer:
        raise ApiError("Phim chưa có tệp âm thanh.", 404)
    trailer = movie.trailer
    if trailer.extension == "mp3":
        file_name = trailer.file_name
        db.session.delete(trailer)
    elif trailer.audio_file_name:
        file_name = trailer.audio_file_name
        trailer.audio_file_name = None
        trailer.updated_at = utc_now()
    else:
        raise ApiError("Phim chưa có tệp âm thanh.", 404)
    log_activity(g.current_user.id, "MOVIE_TRAILER_AUDIO_DELETED", movie.title)
    db.session.commit()
    _remove_trailer_file(Path(current_app.config["TRAILER_UPLOAD_DIR"]) / file_name)
    return jsonify(movie.to_dict())


def _store_trailer_upload(upload, upload_dir, movie_id, extension):
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"movie_{movie_id}_{uuid4().hex}.{extension}"
    target = upload_dir / file_name
    temporary = upload_dir / f".movie_{movie_id}.{uuid4().hex}.tmp"
    upload.stream.seek(0)
    size = 0
    try:
        with temporary.open("wb") as destination:
            while chunk := upload.stream.read(1024 * 1024):
                size += len(chunk)
                if size > 10 * 1024 * 1024 * 1024:
                    raise ApiError("Tệp trailer không được vượt quá 10 GB.")
                destination.write(chunk)
        temporary.replace(target)
    except ApiError:
        temporary.unlink(missing_ok=True)
        raise
    except OSError:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu trailer phim %s", movie_id)
        raise ApiError("Không thể lưu tệp trailer. Hãy kiểm tra dung lượng ổ đĩa và thử lại.", 500)
    return file_name, target


def _remove_trailer_file(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        current_app.logger.exception("Không thể dọn video trailer cũ: %s", path.name)


def _valid_video_signature(video, extension):
    if extension == "webm":
        return video.startswith(b"\x1a\x45\xdf\xa3")
    return len(video) >= 12 and video[4:8] == b"ftyp"


def _valid_trailer_signature(data, extension):
    if extension == "mp3":
        return data.startswith(b"ID3") or (
            len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0
        )
    return _valid_video_signature(data, extension)


@bp.get("/appearance")
@admin_only
def get_appearance_settings():
    return jsonify(_public_appearance(_appearance_settings().values))


APPEARANCE_TITLE_OPTIONS = {
    "title_font": {"bebas", "sans", "serif", "script"},
    "title_frame": {"none", "underline", "rounded", "geometric", "speech"},
    "title_preset": {"cinema", "glow", "shadow", "stroke", "three-d"},
    "title_motion": {
        "none", "bob", "sway", "float", "breathe", "tilt", "drift-left",
        "drift-right", "nod", "wave", "swing", "lift", "orbit", "sway-wide",
        "bounce-soft", "rise-fall", "shimmer", "rotate-soft", "dance", "hover",
    },
}


@bp.patch("/appearance")
@admin_only
def update_appearance_settings():
    data = json_body()
    setting = _appearance_settings()
    values = dict(setting.values or {})
    color_fields = {"accent_color", "page_color", "surface_color"}
    for field in color_fields & data.keys():
        value = data[field]
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ApiError(f"Màu {field} không hợp lệ.")
        values[field] = value.lower()
    if "overlay_opacity" in data:
        opacity = data["overlay_opacity"]
        if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) or not 0 <= opacity <= 0.9:
            raise ApiError("Độ phủ nền phải từ 0 đến 0.9.")
        values["overlay_opacity"] = float(opacity)
    if "title_size" in data:
        title_size = data["title_size"]
        if isinstance(title_size, bool) or not isinstance(title_size, (int, float)) or not 60 <= title_size <= 100:
            raise ApiError("Cỡ tên phim phải từ 60 đến 100.")
        values["title_size"] = int(title_size)
    for field, allowed_values in APPEARANCE_TITLE_OPTIONS.items():
        if field in data:
            value = data[field]
            if not isinstance(value, str) or value not in allowed_values:
                raise ApiError(f"Lựa chọn {field} không hợp lệ.")
            values[field] = value
    footer_text_fields = {
        "welcome_title": ("Tiêu đề màn chào", 120),
        "welcome_description": ("Mô tả màn chào", 500),
        "welcome_button_text": ("Nhãn nút màn chào", 60),
        "footer_company_name": ("Tên công ty", 120),
        "footer_tax_code": ("Mã số thuế", 100),
        "footer_email": ("Email liên hệ", 254),
        "footer_license": ("Thông tin cấp phép", 240),
        "footer_registered": ("Ngày đăng ký", 120),
        "footer_address": ("Địa chỉ", 300),
        "footer_version": ("Phiên bản", 40),
        "footer_commerce_notice": ("Nhãn thông báo thương mại", 100),
    }
    for field, (label, max_len) in footer_text_fields.items():
        if field in data:
            values[field] = clean_str(
                data[field],
                label,
                min_len=1 if field in {"welcome_title", "welcome_button_text"} else 0,
                max_len=max_len,
                required=field in {"welcome_title", "welcome_button_text"},
            )
    if "welcome_enabled" in data:
        if not isinstance(data["welcome_enabled"], bool):
            raise ApiError("Tùy chọn màn chào không hợp lệ.")
        values["welcome_enabled"] = data["welcome_enabled"]
    if "footer_email" in data and values["footer_email"] and not EMAIL_RE.fullmatch(values["footer_email"]):
        raise ApiError("Email liên hệ không hợp lệ.")
    if "footer_show_upcoming" in data:
        if not isinstance(data["footer_show_upcoming"], bool):
            raise ApiError("Tùy chọn phim sắp chiếu không hợp lệ.")
        values["footer_show_upcoming"] = data["footer_show_upcoming"]
    if "footer_partners_enabled" in data:
        if not isinstance(data["footer_partners_enabled"], bool):
            raise ApiError("Tùy chọn hiển thị đối tác không hợp lệ.")
        values["footer_partners_enabled"] = data["footer_partners_enabled"]
    if "footer_links" in data:
        links = data["footer_links"]
        if not isinstance(links, list) or len(links) > 12:
            raise ApiError("Danh sách liên kết chân trang không hợp lệ.")
        values["footer_links"] = [
            _clean_footer_link(link, "Liên kết chân trang")
            for link in links
        ]
    if "footer_partners" in data:
        partners = data["footer_partners"]
        if not isinstance(partners, list) or len(partners) > 30:
            raise ApiError("Danh sách đối tác không hợp lệ (tối đa 30 đối tác).")
        values["footer_partners"] = [
            _clean_footer_partner(partner)
            for partner in partners
        ]
    setting.values = values
    log_activity(g.current_user.id, "APPEARANCE_UPDATED", "Cập nhật giao diện")
    db.session.commit()
    return jsonify(_public_appearance(values))


@bp.post("/appearance/<scope>/media")
@admin_only
def upload_appearance_media(scope):
    if scope not in {"site", "banner", "logo", "welcome"}:
        raise ApiError("Khu vực giao diện không hợp lệ.", 404)
    upload = request.files.get("media")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn ảnh hoặc video giao diện.")
    extension = Path(secure_filename(upload.filename)).suffix.lower().lstrip(".")
    if extension not in {"jpg", "jpeg", "png", "webp", "mp4", "webm"}:
        raise ApiError("Chỉ hỗ trợ JPG, PNG, WEBP, MP4 hoặc WebM.")

    stream = upload.stream
    header = stream.read(16)
    is_video = extension in {"mp4", "webm"}
    if scope == "logo" and is_video:
        raise ApiError("Logo chỉ hỗ trợ ảnh PNG, JPG hoặc WEBP.")
    if not (_valid_video_signature(header, extension) if is_video else _valid_image_signature(header, extension)):
        raise ApiError("Nội dung tệp không đúng định dạng ảnh hoặc video.")

    upload_dir = Path(current_app.config["APPEARANCE_UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{scope}_{uuid4().hex}.{extension}"
    temporary = upload_dir / f".{scope}_{uuid4().hex}.tmp"
    stream.seek(0)
    size = 0
    try:
        with temporary.open("wb") as destination:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                max_size = 10 * 1024 * 1024 if scope == "logo" else 10 * 1024 * 1024 * 1024
                if size > max_size:
                    limit = "10 MB" if scope == "logo" else "10 GB"
                    raise ApiError(f"Tệp { 'logo' if scope == 'logo' else 'nền' } không được vượt quá {limit}.")
                destination.write(chunk)
        if size == 0:
            raise ApiError("Tệp tải lên đang trống.")
        target = upload_dir / file_name
        temporary.replace(target)
    except ApiError:
        temporary.unlink(missing_ok=True)
        raise
    except OSError:
        temporary.unlink(missing_ok=True)
        current_app.logger.exception("Không thể lưu tệp nền %s", scope)
        raise ApiError("Không thể lưu tệp nền. Hãy kiểm tra dung lượng ổ đĩa.", 500)

    setting = _appearance_settings()
    values = dict(setting.values or {})
    old_file = values.get(f"{scope}_media_file")
    values.update({
        f"{scope}_media_file": file_name,
        f"{scope}_media_type": "video" if is_video else "image",
        f"{scope}_media_extension": extension,
    })
    setting.values = values
    log_activity(g.current_user.id, "APPEARANCE_MEDIA_UPDATED", scope)
    db.session.commit()
    if old_file:
        _remove_trailer_file(upload_dir / old_file)
    return jsonify(_public_appearance(values))


@bp.delete("/appearance/<scope>/media")
@admin_only
def delete_appearance_media(scope):
    if scope not in {"site", "banner", "logo", "welcome"}:
        raise ApiError("Khu vực giao diện không hợp lệ.", 404)
    setting = _appearance_settings()
    values = dict(setting.values or {})
    old_file = values.pop(f"{scope}_media_file", None)
    values.pop(f"{scope}_media_type", None)
    values.pop(f"{scope}_media_extension", None)
    setting.values = values
    log_activity(g.current_user.id, "APPEARANCE_MEDIA_DELETED", scope)
    db.session.commit()
    if old_file:
        _remove_trailer_file(Path(current_app.config["APPEARANCE_UPLOAD_DIR"]) / old_file)
    return jsonify(_public_appearance(values))


def _appearance_settings():
    setting = db.session.get(AppearanceSettings, 1)
    if setting is None:
        setting = AppearanceSettings(id=1, values=dict(DEFAULT_APPEARANCE))
        db.session.add(setting)
        db.session.flush()
    return setting


def _public_appearance(values):
    result = public_appearance_values(values)
    for scope in ("site", "banner", "logo", "welcome"):
        file_name = values.get(f"{scope}_media_file")
        if file_name:
            result[f"{scope}_media_url"] = f"/api/movies/appearance/media/{scope}?v={file_name}"
    return result


def _clean_footer_link(link, label):
    if not isinstance(link, dict):
        raise ApiError(f"{label} không hợp lệ.")
    cleaned = {
        "label": clean_str(link.get("label"), label, min_len=1, max_len=60, required=True),
        "url": clean_str(link.get("url"), label, max_len=2048),
    }
    _validate_footer_url(cleaned["url"], label)
    return cleaned


def _clean_footer_partner(partner):
    if not isinstance(partner, dict):
        raise ApiError("Thông tin đối tác không hợp lệ.")
    cleaned = {
        "name": clean_str(partner.get("name"), "Tên đối tác", min_len=1, max_len=100, required=True),
        "logo_url": clean_str(partner.get("logo_url"), "Đường dẫn logo", max_len=2048),
        "url": clean_str(partner.get("url"), "Đường dẫn đối tác", max_len=2048),
    }
    _validate_footer_url(cleaned["logo_url"], "Đường dẫn logo")
    _validate_footer_url(cleaned["url"], "Đường dẫn đối tác")
    return cleaned


def _validate_footer_url(value, label):
    if not value or value == "#":
        return
    parsed = urlparse(value)
    if value.startswith("/") and not value.startswith("//"):
        return
    if parsed.scheme == "https" and parsed.netloc:
        return
    raise ApiError(f"{label} chỉ được dùng liên kết HTTPS hoặc đường dẫn nội bộ.")


@bp.get("/cinemas")
@admin_only
def cinemas():
    room_counts = dict(
        db.session.query(Room.cinema_id, func.count(Room.id))
        .group_by(Room.cinema_id)
        .all()
    )
    return jsonify([
        {
            **cinema.to_dict(),
            "province": normalize_province(cinema.city) or cinema.city,
            "region": region_for_province(normalize_province(cinema.city) or ""),
            "rooms_count": room_counts.get(cinema.id, 0),
        }
        for cinema in Cinema.query.order_by(Cinema.city, Cinema.name).all()
    ])


@bp.post("/cinemas")
@admin_only
def create_cinema():
    data = json_body()
    chain = clean_str(data.get("chain"), "hệ thống rạp", max_len=100) or None
    name = clean_str(data.get("name"), "tên rạp", max_len=150, required=True)
    raw_city = clean_str(data.get("city"), "tỉnh/thành phố", max_len=80, required=True)
    city = normalize_province(raw_city)
    if not city:
        raise ApiError("Vui lòng chọn một trong 34 tỉnh/thành phố hiện hành.")
    address = clean_str(data.get("address"), "địa chỉ", max_len=250, required=True)
    phone = clean_str(data.get("phone"), "số điện thoại", max_len=20) or None
    room_name = clean_str(data.get("room_name"), "tên phòng", max_len=50, required=True)
    room_type = clean_str(data.get("room_type", "2D"), "loại phòng", max_len=20).upper()
    if room_type not in {"2D", "3D", "IMAX"}:
        raise ApiError("Loại phòng phải là 2D, 3D hoặc IMAX.")
    total_rows = clean_int(data.get("total_rows", 8), "số hàng", lo=1, hi=26)
    total_cols = clean_int(data.get("total_cols", 10), "số cột", lo=1, hi=30)
    normalized_name = " ".join(name.casefold().split())
    normalized_chain = " ".join(chain.casefold().split()) if chain else ""
    if any(
        " ".join(cinema.name.casefold().split()) == normalized_name
        and (" ".join((cinema.chain or "").casefold().split())) == normalized_chain
        and (normalize_province(cinema.city) or cinema.city) == city
        for cinema in Cinema.query.all()
    ):
        raise ApiError("Rạp cùng tên đã tồn tại tại tỉnh/thành phố này.", 409)

    cinema = Cinema(chain=chain, name=name, city=city, address=address, phone=phone)
    db.session.add(cinema)
    db.session.flush()
    room = _create_cinema_room(cinema, {
        "name": room_name,
        "room_type": room_type,
        "total_rows": total_rows,
        "total_cols": total_cols,
    })
    log_activity(g.current_user.id, "CINEMA_CREATED", f"{cinema.name} · {city}")
    db.session.commit()
    return jsonify({
        **cinema.to_dict(),
        "region": region_for_province(city),
        "rooms_count": 1,
        "rooms": [room.to_dict()],
    }), 201


@bp.put("/cinemas/<int:cinema_id>")
@admin_only
def update_cinema(cinema_id):
    cinema = db.session.get(Cinema, cinema_id)
    if not cinema:
        raise ApiError("Không tìm thấy rạp.", 404)
    data = json_body()
    chain = clean_str(data.get("chain"), "hệ thống rạp", max_len=100) or None
    name = clean_str(data.get("name"), "tên rạp", max_len=150, required=True)
    raw_city = clean_str(data.get("city"), "tỉnh/thành phố", max_len=80, required=True)
    city = normalize_province(raw_city)
    if not city:
        raise ApiError("Vui lòng chọn một trong 34 tỉnh/thành phố hiện hành.")
    address = clean_str(data.get("address"), "địa chỉ", max_len=250) or None
    phone = clean_str(data.get("phone"), "số điện thoại", max_len=20) or None
    normalized_name = " ".join(name.casefold().split())
    normalized_chain = " ".join(chain.casefold().split()) if chain else ""
    duplicate = Cinema.query.filter(Cinema.id != cinema.id).all()
    if any(
        " ".join(other.name.casefold().split()) == normalized_name
        and " ".join((other.chain or "").casefold().split()) == normalized_chain
        and (normalize_province(other.city) or other.city) == city
        for other in duplicate
    ):
        raise ApiError("Rạp cùng tên đã tồn tại tại tỉnh/thành phố này.", 409)

    cinema.chain = chain
    cinema.name = name
    cinema.city = city
    cinema.address = address
    cinema.phone = phone
    log_activity(g.current_user.id, "CINEMA_UPDATED", f"{cinema.name} · {city}")
    db.session.commit()
    return jsonify({
        **cinema.to_dict(),
        "province": city,
        "region": region_for_province(city),
        "rooms_count": len(cinema.rooms),
    })


@bp.post("/cinemas/<int:cinema_id>/rooms")
@admin_only
def create_cinema_room(cinema_id):
    cinema = db.session.get(Cinema, cinema_id)
    if not cinema:
        raise ApiError("Không tìm thấy rạp.", 404)
    data = json_body()
    room = _validated_room_data(data)
    if Room.query.filter_by(cinema_id=cinema.id, name=room["name"]).first():
        raise ApiError("Tên phòng đã tồn tại tại rạp này.", 409)
    created = _create_cinema_room(cinema, room)
    log_activity(g.current_user.id, "CINEMA_ROOM_CREATED", f"{cinema.name} · {created.name}")
    db.session.commit()
    return jsonify(_admin_room_dict(created)), 201


@bp.put("/rooms/<int:room_id>")
@admin_only
def update_cinema_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        raise ApiError("Không tìm thấy phòng chiếu.", 404)
    data = json_body()
    values = _validated_room_data(data)
    duplicate = Room.query.filter(
        Room.cinema_id == room.cinema_id,
        Room.id != room.id,
        func.lower(Room.name) == values["name"].lower(),
    ).first()
    if duplicate:
        raise ApiError("Tên phòng đã tồn tại tại rạp này.", 409)

    removed_seats = Seat.query.filter(
        Seat.room_id == room.id,
        or_(
            Seat.row_label > chr(ord("A") + values["total_rows"] - 1),
            Seat.number > values["total_cols"],
        ),
    ).all()
    removed_seat_ids = [seat.id for seat in removed_seats]
    if removed_seat_ids and BookingSeat.query.filter(
        BookingSeat.seat_id.in_(removed_seat_ids)
    ).first():
        raise ApiError(
            "Không thể giảm số ghế vì ghế cần xóa đã có vé đặt. Hãy giữ nguyên các ghế đó.",
            409,
        )

    seats_by_position = {
        (seat.row_label, seat.number): seat
        for seat in Seat.query.filter_by(room_id=room.id).all()
    }
    for seat in removed_seats:
        db.session.delete(seat)
    room.name = values["name"]
    room.room_type = values["room_type"]
    room.total_rows = values["total_rows"]
    room.total_cols = values["total_cols"]
    existing_positions = set(seats_by_position) - {
        (seat.row_label, seat.number) for seat in removed_seats
    }
    for row_index in range(room.total_rows):
        row_label = chr(ord("A") + row_index)
        for number in range(1, room.total_cols + 1):
            if (row_label, number) not in existing_positions:
                db.session.add(Seat(
                    room_id=room.id,
                    row_label=row_label,
                    number=number,
                ))
    log_activity(g.current_user.id, "CINEMA_ROOM_UPDATED", f"{room.cinema.name} · {room.name}")
    db.session.commit()
    return jsonify(_admin_room_dict(room))


@bp.delete("/rooms/<int:room_id>")
@admin_only
def delete_cinema_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        raise ApiError("Không tìm thấy phòng chiếu.", 404)
    if Showtime.query.filter_by(room_id=room.id).first():
        raise ApiError(
            "Không thể xóa phòng đã có suất chiếu. Hãy giữ phòng để bảo toàn lịch sử và vé.",
            409,
        )
    room_name = room.name
    cinema_name = room.cinema.name
    db.session.delete(room)
    log_activity(g.current_user.id, "CINEMA_ROOM_DELETED", f"{cinema_name} · {room_name}")
    db.session.commit()
    return jsonify({"id": room_id, "deleted": True})


@bp.post("/cinemas/import")
@admin_only
def import_cinemas():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        raise ApiError("Vui lòng chọn file Excel .xlsx hoặc CSV.")
    extension = Path(upload.filename).suffix.lower().lstrip(".")
    if extension not in {"xlsx", "csv"}:
        raise ApiError("Chỉ hỗ trợ file Excel .xlsx hoặc CSV UTF-8.")
    content = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise ApiError("File nhập rạp không được vượt quá 5 MB.")
    try:
        imported_rows = parse_cinema_import(content, extension)
    except ValueError as exc:
        raise ApiError(str(exc))

    existing = {}
    for cinema in Cinema.query.all():
        normalized_city = normalize_province(cinema.city) or cinema.city
        normalized_chain = " ".join((cinema.chain or "").casefold().split())
        normalized_name = " ".join(cinema.name.casefold().split())
        existing[(normalized_chain, normalized_name, normalized_city)] = cinema
        if not normalized_chain:
            existing[(None, normalized_name, normalized_city)] = cinema

    imported_count = 0
    corrected_region_count = sum(data["region_corrected"] for data in imported_rows)
    skipped_names = []
    for data in imported_rows:
        normalized_chain = " ".join((data.get("chain") or "").casefold().split())
        normalized_name = " ".join(data["name"].casefold().split())
        key = (normalized_chain, normalized_name, data["city"])
        legacy_key = (None, normalized_name, data["city"])
        if key in existing:
            skipped_names.append(data["name"])
            continue
        if normalized_chain and legacy_key in existing:
            existing[legacy_key].chain = data["chain"]
            existing[key] = existing.pop(legacy_key)
            skipped_names.append(data["name"])
            continue
        if not normalized_chain and any(
            existing_key[1:] == key[1:] for existing_key in existing
        ):
            skipped_names.append(data["name"])
            continue
        cinema = Cinema(
            chain=data.get("chain"),
            name=data["name"],
            city=data["city"],
            address=data["address"],
            phone=data["phone"],
        )
        db.session.add(cinema)
        existing[key] = cinema
        if not normalized_chain:
            existing[legacy_key] = cinema
        db.session.flush()
        room_data_list = data["rooms"] or [{
            "name": "Phòng 01",
            "room_type": "2D",
            "total_rows": 8,
            "total_cols": 10,
        }]
        for room_data in room_data_list:
            _create_cinema_room(cinema, room_data)
        imported_count += 1
        log_activity(g.current_user.id, "CINEMA_IMPORTED", f"{cinema.name} · {data['city']}")
    db.session.commit()
    message = f"Đã nhập {imported_count} rạp cùng phòng và ghế; bỏ qua {len(skipped_names)} rạp trùng."
    if corrected_region_count:
        message += f" Đã tự phân loại lại miền theo tỉnh/thành cho {corrected_region_count} rạp."
    missing_address_count = sum(not data["address"] for data in imported_rows)
    if missing_address_count:
        message += f" {missing_address_count} rạp không có địa chỉ trong file nên để trống."
    return jsonify({
        "imported_count": imported_count,
        "skipped_count": len(skipped_names),
        "skipped_names": skipped_names,
        "corrected_region_count": corrected_region_count,
        "missing_address_count": missing_address_count,
        "message": message,
    })


def _create_cinema_room(cinema, data):
    room = Room(
        cinema=cinema,
        name=data["name"],
        room_type=data["room_type"],
        total_rows=data["total_rows"],
        total_cols=data["total_cols"],
    )
    db.session.add(room)
    db.session.flush()
    db.session.add_all([
        Seat(room_id=room.id, row_label=chr(ord("A") + row_index), number=number)
        for row_index in range(room.total_rows)
        for number in range(1, room.total_cols + 1)
    ])
    return room


def _validated_room_data(data):
    name = clean_str(data.get("name"), "tên phòng", max_len=50, required=True)
    room_type = clean_str(data.get("room_type", "2D"), "loại phòng", max_len=20).upper()
    if room_type not in {"2D", "3D", "IMAX"}:
        raise ApiError("Loại phòng phải là 2D, 3D hoặc IMAX.")
    total_rows = clean_int(data.get("total_rows", 8), "số hàng ghế", lo=1, hi=26)
    total_cols = clean_int(data.get("total_cols", 10), "số ghế mỗi hàng", lo=1, hi=30)
    return {
        "name": name,
        "room_type": room_type,
        "total_rows": total_rows,
        "total_cols": total_cols,
    }


def _admin_room_dict(room):
    return {
        **room.to_dict(),
        "seats_count": Seat.query.filter_by(room_id=room.id).count(),
        "showtimes_count": Showtime.query.filter_by(room_id=room.id).count(),
    }


@bp.get("/rooms")
@admin_only
def rooms():
    room_rows = Room.query.order_by(Room.cinema_id, Room.name).all()
    seat_counts = dict(
        db.session.query(Seat.room_id, func.count(Seat.id))
        .group_by(Seat.room_id)
        .all()
    )
    showtime_counts = dict(
        db.session.query(Showtime.room_id, func.count(Showtime.id))
        .group_by(Showtime.room_id)
        .all()
    )
    return jsonify([
        {
            **room.to_dict(),
            "seats_count": seat_counts.get(room.id, 0),
            "showtimes_count": showtime_counts.get(room.id, 0),
        }
        for room in room_rows
    ])


@bp.get("/showtimes")
@admin_only
def showtimes():
    rows = Showtime.query.order_by(Showtime.start_time.desc()).all()
    return jsonify([_admin_showtime_dict(showtime) for showtime in rows])


@bp.post("/showtimes")
@admin_only
def create_showtime():
    data = json_body()
    movie, room, start_time, base_price = _showtime_values(data)
    if start_time <= local_now():
        raise ApiError("Giờ chiếu phải ở trong tương lai.")
    _ensure_room_available(movie, room, start_time)
    showtime = Showtime(movie=movie, room=room, start_time=start_time, base_price=base_price)
    db.session.add(showtime)
    log_activity(g.current_user.id, "SHOWTIME_CREATED", f"{movie.title} - {room.name}")
    db.session.commit()
    return jsonify(_admin_showtime_dict(showtime)), 201


@bp.post("/showtimes/bulk")
@admin_only
def create_showtimes_bulk():
    data = json_body()
    room_ids = data.get("room_ids")
    if not isinstance(room_ids, list) or not room_ids:
        raise ApiError("Vui lòng tích ít nhất một phòng chiếu.")
    if len(room_ids) > 50:
        raise ApiError("Mỗi lần chỉ có thể tạo lịch cho tối đa 50 phòng.")

    normalized_room_ids = [clean_int(room_id, "phòng chiếu", lo=1) for room_id in room_ids]
    if len(set(normalized_room_ids)) != len(normalized_room_ids):
        raise ApiError("Danh sách phòng chiếu có phòng bị lặp.")

    schedules = [
        _showtime_values({**data, "room_id": room_id})
        for room_id in normalized_room_ids
    ]
    start_time = schedules[0][2]
    if start_time <= local_now():
        raise ApiError("Giờ chiếu phải ở trong tương lai.")
    if any(schedule[2] != start_time for schedule in schedules):
        raise ApiError("Các phòng chiếu phải dùng cùng ngày và giờ.")

    for movie, room, _, _ in schedules:
        _ensure_room_available(movie, room, start_time)

    showtimes = [
        Showtime(movie=movie, room=room, start_time=start_time, base_price=base_price)
        for movie, room, _, base_price in schedules
    ]
    db.session.add_all(showtimes)
    for showtime in showtimes:
        log_activity(
            g.current_user.id,
            "SHOWTIME_CREATED",
            f"{showtime.movie.title} - {showtime.room.name}",
        )
    db.session.commit()
    return jsonify([_admin_showtime_dict(showtime) for showtime in showtimes]), 201


@bp.put("/showtimes/<int:showtime_id>")
@admin_only
def update_showtime(showtime_id):
    showtime = db.session.get(Showtime, showtime_id)
    if not showtime:
        raise ApiError("Không tìm thấy suất chiếu.", 404)
    data = json_body()
    movie, room, start_time, base_price = _showtime_values(data)
    if start_time <= local_now():
        raise ApiError("Giờ chiếu phải ở trong tương lai.")
    _ensure_room_available(movie, room, start_time, exclude_id=showtime.id)

    has_bookings = Booking.query.filter_by(showtime_id=showtime.id).first() is not None
    schedule_changed = (
        showtime.movie_id != movie.id
        or showtime.room_id != room.id
        or showtime.start_time != start_time
    )
    if has_bookings and schedule_changed:
        raise ApiError("Không thể đổi phim, phòng hoặc giờ chiếu vì suất này đã có vé được đặt.", 409)

    showtime.movie = movie
    showtime.room = room
    showtime.start_time = start_time
    showtime.base_price = base_price
    log_activity(g.current_user.id, "SHOWTIME_UPDATED", f"{movie.title} - {room.name}")
    db.session.commit()
    return jsonify(_admin_showtime_dict(showtime))


def _showtime_values(data):
    movie_id = clean_int(data.get("movie_id"), "phim", lo=1)
    cinema_id = clean_int(data.get("cinema_id"), "rạp", lo=1)
    room_id = clean_int(data.get("room_id"), "phòng chiếu", lo=1)
    movie = db.session.get(Movie, movie_id)
    cinema = db.session.get(Cinema, cinema_id)
    room = db.session.get(Room, room_id)
    if movie and db.session.get(MovieCancellation, movie.id):
        raise ApiError("Không thể tạo suất chiếu cho phim đã hủy.")
    if not movie or not cinema or not room or room.cinema_id != cinema.id:
        raise ApiError("Phim, rạp hoặc phòng chiếu không hợp lệ.")
    if movie.status == "ended":
        raise ApiError("Không thể tạo suất chiếu cho phim đã kết thúc công chiếu.")
    raw_start_time = clean_str(data.get("start_time"), "giờ chiếu", max_len=16, required=True)
    try:
        start_time = datetime.strptime(raw_start_time, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise ApiError("Giờ chiếu không hợp lệ.")
    base_price = clean_int(data.get("base_price"), "giá vé", lo=0, hi=1_000_000_000)
    return movie, room, start_time, base_price


def _ensure_room_available(movie, room, start_time, *, exclude_id=None):
    candidate_end = start_time + timedelta(minutes=movie.duration_minutes + 15)
    existing = Showtime.query.filter_by(room_id=room.id)
    if exclude_id is not None:
        existing = existing.filter(Showtime.id != exclude_id)
    for showtime in existing.all():
        existing_end = showtime.start_time + timedelta(minutes=showtime.movie.duration_minutes + 15)
        if start_time < existing_end and showtime.start_time < candidate_end:
            raise ApiError("Suất chiếu bị trùng giờ hoặc không đủ thời gian chuyển phòng.", 409)


def _admin_showtime_dict(showtime):
    return {
        "id": showtime.id,
        "movie_id": showtime.movie_id,
        "movie": showtime.movie.title,
        "cinema_id": showtime.room.cinema_id,
        "cinema": showtime.room.cinema.name,
        "room_id": showtime.room_id,
        "room": showtime.room.name,
        "start_time": showtime.start_time.isoformat(),
        "base_price": showtime.base_price,
    }


@bp.get("/transactions")
@admin_only
def transactions():
    return jsonify([p.to_dict() for p in Payment.query.order_by(Payment.id.desc()).limit(100).all()])


@bp.get("/promotions")
@admin_only
def promotions():
    return jsonify([p.to_dict() for p in Promotion.query.all()])


@bp.get("/foods")
@admin_only
def foods():
    return jsonify([f.to_dict() for f in Food.query.order_by(Food.id).all()])


@bp.post("/foods")
@admin_only
def create_food():
    data = json_body()
    food = Food(
        name=clean_str(data.get("name"), "tên mặt hàng", max_len=100, required=True),
        description=clean_str(data.get("description"), "mô tả", max_len=200) or None,
        price=clean_int(data.get("price"), "giá", lo=0, hi=1_000_000_000),
        is_combo=_bool_field(data, "is_combo", default=False),
        available=_bool_field(data, "available", default=True),
    )
    db.session.add(food)
    log_activity(g.current_user.id, "FOOD_CREATED", food.name)
    db.session.commit()
    return jsonify(food.to_dict()), 201


@bp.put("/foods/<int:food_id>")
@admin_only
def update_food(food_id):
    food = db.session.get(Food, food_id)
    if not food:
        raise ApiError("Không tìm thấy mặt hàng.", 404)
    data = json_body()
    if "name" in data:
        food.name = clean_str(data["name"], "tên mặt hàng", max_len=100, required=True)
    if "description" in data:
        food.description = clean_str(data["description"], "mô tả", max_len=200) or None
    if "price" in data:
        food.price = clean_int(data["price"], "giá", lo=0, hi=1_000_000_000)
    if "is_combo" in data:
        food.is_combo = _bool_field(data, "is_combo")
    if "available" in data:
        food.available = _bool_field(data, "available")
    log_activity(g.current_user.id, "FOOD_UPDATED", food.name)
    db.session.commit()
    return jsonify(food.to_dict())


@bp.get("/products")
@admin_only
def products():
    return jsonify([p.to_dict() for p in Product.query.order_by(Product.id).all()])


@bp.post("/products")
@admin_only
def create_product():
    data = json_body()
    product = Product(
        name=clean_str(data.get("name"), "tên sản phẩm", max_len=100, required=True),
        category=clean_str(data.get("category", "Khác"), "danh mục", max_len=60, required=True),
        description=clean_str(data.get("description"), "mô tả", max_len=200) or None,
        price=clean_int(data.get("price"), "giá", lo=0, hi=1_000_000_000),
        stock_quantity=clean_int(data.get("stock_quantity"), "số lượng tồn kho", lo=0, hi=1_000_000_000),
        active=_bool_field(data, "active", default=True),
    )
    db.session.add(product)
    log_activity(g.current_user.id, "PRODUCT_CREATED", product.name)
    db.session.commit()
    return jsonify(product.to_dict()), 201


@bp.put("/products/<int:product_id>")
@admin_only
def update_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        raise ApiError("Không tìm thấy sản phẩm.", 404)
    data = json_body()
    if "name" in data:
        product.name = clean_str(data["name"], "tên sản phẩm", max_len=100, required=True)
    if "category" in data:
        product.category = clean_str(data["category"], "danh mục", max_len=60, required=True)
    if "description" in data:
        product.description = clean_str(data["description"], "mô tả", max_len=200) or None
    if "price" in data:
        product.price = clean_int(data["price"], "giá", lo=0, hi=1_000_000_000)
    if "stock_quantity" in data:
        product.stock_quantity = clean_int(data["stock_quantity"], "số lượng tồn kho", lo=0, hi=1_000_000_000)
    if "active" in data:
        product.active = _bool_field(data, "active")
    log_activity(g.current_user.id, "PRODUCT_UPDATED", product.name)
    db.session.commit()
    return jsonify(product.to_dict())


def _bool_field(data, key, *, default=None):
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ApiError(f"{key} không hợp lệ.")
    return value


@bp.get("/roles")
@admin_only
def roles():
    return jsonify([r.to_dict() for r in Role.query.all()])


@bp.get("/ai-settings")
@admin_only
def ai_settings():
    if not current_app.config["FEATURE_AI"]:     # AI đang tắt: coi như endpoint không tồn tại
        raise ApiError("Không tìm thấy tài nguyên.", 404)
    return jsonify([{"key": k, "value": str(v)} for k, v in AI_SETTINGS.items()])


@bp.get("/settings")
@admin_only
def settings():
    return jsonify([{"key": "app_name", "value": "CINEVO"}, {"key": "currency", "value": "VND"},
                    {"key": "payment_mode", "value": "mock"}, {"key": "otp_mode", "value": "mock"}])


@bp.get("/activity-logs")
@admin_only
def activity_logs():
    return jsonify([a.to_dict() for a in ActivityLog.query.order_by(ActivityLog.id.desc()).limit(100).all()])
