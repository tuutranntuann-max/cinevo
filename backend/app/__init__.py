"""Application factory của CINEVO."""
import re

from flask import Flask, current_app, jsonify, request
from flask_cors import CORS

from .config import Config
from .extensions import db
from .services.validation import ApiError


class CinevoRequest(Flask.request_class):
    @property
    def max_content_length(self):
        if self.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/(poster|title-logo)", self.path):
            return current_app.config["POSTER_MAX_CONTENT_LENGTH"]
        if self.method == "POST" and self.path == "/api/admin/movies/import":
            return current_app.config["MOVIE_IMPORT_MAX_CONTENT_LENGTH"]
        if self.method == "POST" and self.path == "/api/admin/cinemas/import":
            return current_app.config["CINEMA_IMPORT_MAX_CONTENT_LENGTH"]
        if self.method == "POST" and self.path == "/api/content/manage/media":
            return current_app.config["POSTER_MAX_CONTENT_LENGTH"]
        if self.method == "POST" and self.path == "/api/auth/me/avatar":
            return current_app.config["POSTER_MAX_CONTENT_LENGTH"]
        if self.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/film", self.path):
            return current_app.config["FILM_MAX_CONTENT_LENGTH"]
        if self.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/film-image", self.path):
            return current_app.config["POSTER_MAX_CONTENT_LENGTH"]
        if self.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/subtitles", self.path):
            return current_app.config["POSTER_MAX_CONTENT_LENGTH"]
        if self.method == "POST" and (
            re.fullmatch(r"/api/admin/movies/\d+/(trailer|audio)", self.path)
            or re.fullmatch(r"/api/admin/appearance/(site|banner|welcome)/media", self.path)
        ):
            return current_app.config["TRAILER_MAX_CONTENT_LENGTH"]
        return current_app.config["MAX_CONTENT_LENGTH"]


def create_app(config_class=Config):
    app = Flask(__name__)
    app.request_class = CinevoRequest
    app.config.from_object(config_class)

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from . import models  # noqa: F401  (đăng ký toàn bộ model với SQLAlchemy)
    from .routes import register_blueprints

    register_blueprints(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "app": "CINEVO"})

    @app.get("/api/config")
    def public_config():
        """Cho frontend biết tính năng nào đang bật (không chứa thông tin bí mật)."""
        return jsonify({"features": {"ai": bool(app.config["FEATURE_AI"])}})

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        if app.config["IS_PRODUCTION"]:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp

    @app.errorhandler(ApiError)
    def api_error(e):
        return jsonify({"message": e.message, "code": e.code}), e.status

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"message": "Không tìm thấy tài nguyên."}), 404

    @app.errorhandler(405)
    def not_allowed(_e):
        return jsonify({"message": "Phương thức không được hỗ trợ."}), 405

    @app.errorhandler(413)
    def too_large(_e):
        if request.method == "POST" and request.path == "/api/admin/movies/import":
            return jsonify({"message": "File nhập phim vượt quá giới hạn 5 MB."}), 413
        if request.method == "POST" and request.path == "/api/admin/cinemas/import":
            return jsonify({"message": "File nhập rạp vượt quá giới hạn 5 MB."}), 413
        if request.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/film", request.path):
            return jsonify({"message": "Tệp phim vượt quá giới hạn 10 GB."}), 413
        if request.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/film-image", request.path):
            return jsonify({"message": "Ảnh phim vượt quá giới hạn 5 MB."}), 413
        if request.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/subtitles", request.path):
            return jsonify({"message": "Tệp phụ đề vượt quá giới hạn 5 MB."}), 413
        if request.method == "POST" and request.path == "/api/content/manage/media":
            return jsonify({"message": "Ảnh nội dung vượt quá giới hạn 5 MB."}), 413
        if request.method == "POST" and request.path == "/api/auth/me/avatar":
            return jsonify({"message": "Ảnh đại diện vượt quá giới hạn 5 MB."}), 413
        if request.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/title-logo", request.path):
            return jsonify({"message": "Logo tên phim vượt quá giới hạn 5 MB."}), 413
        if request.method == "POST" and re.fullmatch(r"/api/admin/movies/\d+/(trailer|audio)", request.path):
            return jsonify({"message": "Tệp trailer vượt quá giới hạn tải lên 10 GB."}), 413
        if request.method == "POST" and re.fullmatch(r"/api/admin/appearance/(site|banner|welcome)/media", request.path):
            return jsonify({"message": "Tệp nền vượt quá giới hạn tải lên 10 GB."}), 413
        return jsonify({"message": "Dữ liệu gửi lên quá lớn."}), 413

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"message": "Lỗi hệ thống, vui lòng thử lại."}), 500

    return app
