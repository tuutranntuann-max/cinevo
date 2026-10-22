"""API phim (công khai, không cần đăng nhập)."""
import re
from urllib.parse import parse_qs, urlparse

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import and_, or_

from ..extensions import db
from ..models import AppearanceSettings, Cinema, Membership, Movie, MovieCancellation, MovieFilm, MovieSubtitle, Room, Showtime
from ..models.appearance_settings import public_appearance_values
from ..services.auth_service import current_user_from_request
from ..timeutil import local_now, utc_now

bp = Blueprint("movies", __name__, url_prefix="/api/movies")
PLAYBACK_TOKEN_MAX_AGE = 10 * 60


def _active_viewer():
    user = current_user_from_request()
    if not user:
        return None
    now = utc_now()
    activated = Membership.query.filter_by(user_id=user.id, status="SCHEDULED").filter(
        Membership.starts_at <= now,
    ).update({"status": "ACTIVE"}, synchronize_session=False)
    if activated:
        db.session.commit()
    return Membership.query.filter_by(user_id=user.id, status="ACTIVE").filter(
        Membership.starts_at <= now,
        Membership.expires_at > now,
    ).order_by(Membership.expires_at.desc()).first()


def _playback_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="cinevo-movie-playback")


def _playback_grant(movie_id, user_id):
    return _playback_serializer().dumps({"user_id": user_id, "movie_id": movie_id})


def _playback_url(movie, user_id, grant):
    return f"/api/movies/{movie.id}/film?format={movie.film.extension}&v={movie.film.file_name}&access={grant}"


def _has_playback_access(movie_id):
    grant = request.args.get("access", "")
    try:
        payload = _playback_serializer().loads(grant, max_age=PLAYBACK_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    if payload.get("movie_id") != movie_id:
        return False
    now = utc_now()
    membership = Membership.query.filter_by(user_id=payload.get("user_id"), status="ACTIVE").filter(
        Membership.starts_at <= now,
        Membership.expires_at > now,
    ).first()
    return membership is not None


def _watch_movie_dict(movie, viewer=None):
    data = movie.to_dict()
    can_watch = viewer is not None
    data["can_watch"] = can_watch
    if can_watch:
        grant = _playback_grant(movie.id, viewer.user_id)
        data["film_url"] = _playback_url(movie, viewer.user_id, grant)
        data["subtitles"] = [
            {
                "id": subtitle.id,
                "label": subtitle.label,
                "language": subtitle.language,
                "url": subtitle.source_url or (
                    f"/api/movies/{movie.id}/subtitles/{subtitle.id}"
                    f"?format=vtt&v={subtitle.file_name}&access={grant}"
                ),
            }
            for subtitle in movie.subtitles
        ]
        if movie.film.image_file_name:
            data["film_image_url"] = (
                f"/api/movies/{movie.id}/film-image?format={movie.film.image_extension}"
                f"&v={movie.film.image_file_name}&access={grant}"
            )
    else:
        data["film_url"] = None
        data["film_image_url"] = None
        data["subtitles"] = []
    return data


@bp.get("")
def list_movies():
    """?status=now_showing|coming_soon &genre= &q= &city="""
    query = Movie.query.filter(~Movie.id.in_(db.session.query(MovieCancellation.movie_id)))
    future_movie_ids = db.session.query(Showtime.movie_id).filter(Showtime.start_time >= local_now())
    query = query.filter(or_(
        Movie.status == "coming_soon",
        and_(Movie.status == "now_showing", Movie.id.in_(future_movie_ids)),
    ))
    if status := request.args.get("status"):
        query = query.filter(Movie.status == status)
    if genre := request.args.get("genre"):
        query = query.filter(Movie.genre.ilike(f"%{genre}%"))
    if q := request.args.get("q"):
        query = query.filter(Movie.title.ilike(f"%{q}%"))
    if city := request.args.get("city"):   # chỉ giữ phim có suất chiếu sắp tới tại khu vực
        ids = (db.session.query(Showtime.movie_id).join(Room).join(Cinema)
               .filter(Cinema.city == city, Showtime.start_time >= local_now()))
        query = query.filter(Movie.status == "coming_soon") if request.args.get("status") == "coming_soon" \
            else query.filter(Movie.id.in_(ids))
    return jsonify([m.to_dict() for m in query.order_by(Movie.rating.desc()).all()])


@bp.get("/<int:movie_id>")
def get_movie(movie_id):
    movie = db.session.get(Movie, movie_id)
    if (
        not movie
        or movie.status not in {"coming_soon", "now_showing"}
        or db.session.get(MovieCancellation, movie_id)
    ):
        return jsonify({"message": "Không tìm thấy phim."}), 404
    if movie.status == "now_showing" and not Showtime.query.filter(
        Showtime.movie_id == movie_id, Showtime.start_time >= local_now()
    ).first():
        return jsonify({"message": "Không tìm thấy phim."}), 404
    return jsonify(movie.to_dict())


@bp.get("/watch")
def watchable_movies():
    """Movies whose theatrical run ended and whose full-length film is available."""
    viewer = _active_viewer()
    return jsonify([
        _watch_movie_dict(movie, viewer=viewer)
        for movie in _watchable_movies().order_by(Movie.rating.desc()).all()
    ])


@bp.get("/watch/<int:movie_id>")
def get_watchable_movie(movie_id):
    movie = _watchable_movies().filter(Movie.id == movie_id).first()
    if not movie:
        return jsonify({"message": "Phim chưa có bản xem trực tuyến hoặc vẫn còn chiếu tại rạp."}), 404
    return jsonify(_watch_movie_dict(movie, viewer=_active_viewer()))


def _watchable_movies():
    past_showing_ids = db.session.query(Showtime.movie_id).filter(Showtime.start_time < local_now())
    future_showing_ids = db.session.query(Showtime.movie_id).filter(Showtime.start_time >= local_now())
    return (
        Movie.query.join(MovieFilm)
        .filter(Movie.status.in_(("now_showing", "ended")))
        .filter(or_(
            Movie.theatrical_end_date.is_(None),
            Movie.theatrical_end_date <= local_now().date(),
        ))
        .filter(or_(
            and_(
                Movie.status == "now_showing",
                Movie.id.in_(past_showing_ids),
                ~Movie.id.in_(future_showing_ids),
            ),
            Movie.status == "ended",
        ))
        .filter(~Movie.id.in_(db.session.query(MovieCancellation.movie_id)))
    )


@bp.get("/<int:movie_id>/film")
def movie_film(movie_id):
    movie = db.session.get(Movie, movie_id)
    if (
        not movie
        or not movie.film
        or not _watchable_movies().filter(Movie.id == movie_id).first()
    ):
        return jsonify({"message": "Phim chưa có bản xem trực tuyến hoặc vẫn còn chiếu tại rạp."}), 404
    if not _has_playback_access(movie_id):
        return jsonify({"message": "Bạn cần gói thành viên đang hoạt động để xem phim.", "code": "MEMBERSHIP_REQUIRED"}), 403
    if request.args.get("v") != movie.film.file_name:
        return jsonify({"message": "Không tìm thấy phim để xem."}), 404
    mimetype = {"mp4": "video/mp4", "webm": "video/webm"}.get(movie.film.extension)
    if not mimetype or request.args.get("format", "").lower() != movie.film.extension:
        return jsonify({"message": "Không tìm thấy phim để xem."}), 404
    return send_from_directory(
        current_app.config["FEATURE_FILM_UPLOAD_DIR"],
        movie.film.file_name,
        mimetype=mimetype,
        conditional=True,
        max_age=0,
    )


@bp.get("/<int:movie_id>/subtitles/<int:subtitle_id>")
def movie_subtitle(movie_id, subtitle_id):
    subtitle = db.session.get(MovieSubtitle, subtitle_id)
    if (
        not subtitle
        or subtitle.movie_id != movie_id
        or subtitle.source_type != "upload"
        or not _watchable_movies().filter(Movie.id == movie_id).first()
    ):
        return jsonify({"message": "Không tìm thấy phụ đề phim."}), 404
    if not _has_playback_access(movie_id):
        return jsonify({"message": "Bạn cần gói thành viên đang hoạt động để xem phim.", "code": "MEMBERSHIP_REQUIRED"}), 403
    if request.args.get("format") != "vtt" or request.args.get("v") != subtitle.file_name:
        return jsonify({"message": "Không tìm thấy phụ đề phim."}), 404
    return send_from_directory(
        current_app.config["FEATURE_FILM_UPLOAD_DIR"],
        subtitle.file_name,
        mimetype="text/vtt",
        conditional=True,
        max_age=0,
    )


@bp.get("/<int:movie_id>/film-image")
def movie_film_image(movie_id):
    movie = db.session.get(Movie, movie_id)
    if (
        not movie
        or not movie.film
        or not movie.film.image_file_name
        or not _watchable_movies().filter(Movie.id == movie_id).first()
    ):
        return jsonify({"message": "Không tìm thấy ảnh phim."}), 404
    if not _has_playback_access(movie_id):
        return jsonify({"message": "Bạn cần gói thành viên đang hoạt động để xem phim.", "code": "MEMBERSHIP_REQUIRED"}), 403
    if request.args.get("v") != movie.film.image_file_name:
        return jsonify({"message": "Không tìm thấy ảnh phim."}), 404
    mimetypes = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    extension = movie.film.image_extension
    if request.args.get("format", "").lower() != extension or extension not in mimetypes:
        return jsonify({"message": "Không tìm thấy ảnh phim."}), 404
    return send_from_directory(
        current_app.config["FEATURE_FILM_UPLOAD_DIR"],
        movie.film.image_file_name,
        mimetype=mimetypes[extension],
        conditional=True,
        max_age=0,
    )


@bp.get("/<int:movie_id>/poster")
def movie_poster(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.poster_url:
        return jsonify({"message": "Phim chưa có ảnh poster."}), 404
    extension = request.args.get("format", "").lower()
    if extension not in {"jpg", "jpeg", "png", "webp"}:
        return jsonify({"message": "Không tìm thấy ảnh poster."}), 404
    version = request.args.get("v", "")
    stored_query = parse_qs(urlparse(movie.poster_url).query)
    if version != stored_query.get("v", [""])[0] or extension != stored_query.get("format", [""])[0]:
        return jsonify({"message": "Không tìm thấy ảnh poster."}), 404
    if re.fullmatch(rf"movie_{movie.id}_[0-9a-f]{{32}}\.(?:jpg|jpeg|png|webp)", version):
        file_name = version
        if not file_name.endswith(f".{extension}"):
            return jsonify({"message": "Không tìm thấy ảnh poster."}), 404
    else:
        file_name = f"movie_{movie.id}.{extension}"
    return send_from_directory(
        current_app.config["POSTER_UPLOAD_DIR"],
        file_name,
        mimetype={"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[extension],
        max_age=0,
    )


@bp.get("/<int:movie_id>/title-logo")
def movie_title_logo(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.title_logo_url:
        return jsonify({"message": "Phim chưa có logo tên phim."}), 404
    extension = request.args.get("format", "").lower()
    version = request.args.get("v", "")
    stored_query = parse_qs(urlparse(movie.title_logo_url).query)
    if (
        version != stored_query.get("v", [""])[0]
        or extension != stored_query.get("format", [""])[0]
        or not re.fullmatch(rf"movie_{movie.id}_title_[0-9a-f]{{32}}\.(?:jpg|jpeg|png|webp)", version)
        or not version.endswith(f".{extension}")
    ):
        return jsonify({"message": "Không tìm thấy logo tên phim."}), 404
    return send_from_directory(
        current_app.config["POSTER_UPLOAD_DIR"],
        version,
        mimetype={"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[extension],
        max_age=0,
    )


@bp.get("/<int:movie_id>/trailer")
def movie_trailer(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.trailer:
        return jsonify({"message": "Phim chưa có video trailer."}), 404
    extension = request.args.get("format", "").lower()
    if extension != movie.trailer.extension:
        return jsonify({"message": "Không tìm thấy tệp trailer."}), 404
    mimetype = {"mp3": "audio/mpeg", "mp4": "video/mp4", "webm": "video/webm"}.get(extension)
    if not mimetype:
        return jsonify({"message": "Không tìm thấy tệp trailer."}), 404
    return send_from_directory(
        current_app.config["TRAILER_UPLOAD_DIR"],
        movie.trailer.file_name,
        mimetype=mimetype,
        conditional=True,
        max_age=0,
    )


@bp.get("/<int:movie_id>/audio")
def movie_audio(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie or not movie.trailer:
        return jsonify({"message": "Phim chưa có tệp âm thanh trailer."}), 404
    trailer = movie.trailer
    file_name = trailer.audio_file_name
    if not file_name and trailer.extension == "mp3":
        file_name = trailer.file_name
    if not file_name or request.args.get("format", "").lower() != "mp3":
        return jsonify({"message": "Không tìm thấy tệp âm thanh trailer."}), 404
    if request.args.get("v") != file_name:
        return jsonify({"message": "Không tìm thấy tệp âm thanh trailer."}), 404
    return send_from_directory(
        current_app.config["TRAILER_UPLOAD_DIR"],
        file_name,
        mimetype="audio/mpeg",
        conditional=True,
        max_age=0,
    )


@bp.get("/appearance")
def public_appearance():
    setting = db.session.get(AppearanceSettings, 1)
    values = setting.values if setting else {}
    result = public_appearance_values(values)
    for scope in ("site", "banner", "logo", "welcome"):
        file_name = values.get(f"{scope}_media_file")
        if file_name:
            result[f"{scope}_media_url"] = f"/api/movies/appearance/media/{scope}?v={file_name}"
    return jsonify(result)


@bp.get("/appearance/media/<scope>")
def public_appearance_media(scope):
    if scope not in {"site", "banner", "logo", "welcome"}:
        return jsonify({"message": "Không tìm thấy tệp giao diện."}), 404
    setting = db.session.get(AppearanceSettings, 1)
    values = setting.values if setting else {}
    file_name = values.get(f"{scope}_media_file")
    extension = values.get(f"{scope}_media_extension")
    if not file_name or request.args.get("v") != file_name:
        return jsonify({"message": "Không tìm thấy tệp giao diện."}), 404
    mimetypes = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "webp": "image/webp", "mp4": "video/mp4", "webm": "video/webm",
    }
    if extension not in mimetypes:
        return jsonify({"message": "Không tìm thấy tệp giao diện."}), 404
    return send_from_directory(
        current_app.config["APPEARANCE_UPLOAD_DIR"],
        file_name,
        mimetype=mimetypes[extension],
        conditional=True,
        max_age=0,
    )
