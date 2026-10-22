"""Public movie reviews, with authenticated review creation and updates."""
from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..models import Movie, MovieReview
from ..services.auth_service import auth_required
from ..services.validation import ApiError, clean_int, clean_str

bp = Blueprint("reviews", __name__, url_prefix="/api/movies")
PAGE_SIZE = 20


def _movie_or_404(movie_id):
    movie = db.session.get(Movie, movie_id)
    if not movie:
        raise ApiError("Không tìm thấy phim.", 404)
    return movie


@bp.get("/<int:movie_id>/reviews")
def list_movie_reviews(movie_id):
    _movie_or_404(movie_id)
    page = request.args.get("page", "1")
    try:
        page_number = int(page)
    except (TypeError, ValueError) as exc:
        raise ApiError("Số trang không hợp lệ.") from exc
    if page_number < 1:
        raise ApiError("Số trang không hợp lệ.")

    query = MovieReview.query.filter_by(movie_id=movie_id)
    total = query.count()
    average = db.session.query(func.avg(MovieReview.rating)).filter_by(movie_id=movie_id).scalar()
    reviews = (
        query.order_by(MovieReview.created_at.desc(), MovieReview.id.desc())
        .offset((page_number - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    return jsonify({
        "average_rating": round(float(average), 1) if average is not None else None,
        "review_count": total,
        "page": page_number,
        "page_size": PAGE_SIZE,
        "has_more": page_number * PAGE_SIZE < total,
        "reviews": [review.to_dict() for review in reviews],
    })


@bp.get("/<int:movie_id>/reviews/mine")
@auth_required
def get_my_movie_review(movie_id):
    _movie_or_404(movie_id)
    review = MovieReview.query.filter_by(movie_id=movie_id, user_id=g.current_user.id).first()
    return jsonify(review.to_dict() if review else None)


@bp.post("/<int:movie_id>/reviews")
@auth_required
def save_movie_review(movie_id):
    movie = _movie_or_404(movie_id)
    if movie.status not in {"coming_soon", "now_showing"}:
        raise ApiError("Phim này hiện không nhận đánh giá.", 400)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Nội dung đánh giá không hợp lệ.")
    rating = clean_int(data.get("rating"), "Số sao", lo=1, hi=5)
    comment = clean_str(data.get("comment"), "Bình luận", min_len=2, max_len=1000, required=True)

    review = MovieReview.query.filter_by(movie_id=movie_id, user_id=g.current_user.id).first()
    created = review is None
    if created:
        review = MovieReview(movie_id=movie_id, user_id=g.current_user.id)
        db.session.add(review)
    review.rating = rating
    review.comment = comment
    db.session.commit()
    return jsonify({
        "review": review.to_dict(),
        "created": created,
    }), 201 if created else 200


@bp.delete("/<int:movie_id>/reviews/mine")
@auth_required
def delete_my_movie_review(movie_id):
    _movie_or_404(movie_id)
    review = MovieReview.query.filter_by(movie_id=movie_id, user_id=g.current_user.id).first()
    if not review:
        raise ApiError("Bạn chưa đánh giá phim này.", 404)
    db.session.delete(review)
    db.session.commit()
    return jsonify({"deleted": True})
