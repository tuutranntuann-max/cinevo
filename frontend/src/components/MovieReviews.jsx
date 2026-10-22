import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { movieService } from "../services/movieService";
import MovieInfoIcon from "./MovieInfoIcon";

function ReviewStars({ value, onChange, disabled = false }) {
  return (
    <div className="movie-review-stars" role="group" aria-label="Chọn số sao">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          className={star <= value ? "active" : ""}
          key={star}
          type="button"
          disabled={disabled}
          aria-label={`${star} sao`}
          aria-pressed={star === value}
          onClick={() => onChange(star)}
        >
          ★
        </button>
      ))}
    </div>
  );
}

function formatReviewDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(value));
}

export default function MovieReviews({ movieId, onSummaryChange }) {
  const { user, loading: authLoading, requireLogin } = useAuth();
  const [data, setData] = useState(null);
  const [myReview, setMyReview] = useState(null);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState(1);

  const loadReviews = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await movieService.movieReviews(movieId, page);
      setData((current) => ({
        ...result,
        reviews: page === 1 ? result.reviews : [...(current?.reviews || []), ...result.reviews],
      }));
      onSummaryChange?.({ average_rating: result.average_rating, review_count: result.review_count });
      if (user) {
        const ownReview = await movieService.myMovieReview(movieId);
        setMyReview(ownReview);
        if (ownReview) {
          setRating(ownReview.rating);
          setComment(ownReview.comment);
        }
      } else {
        setMyReview(null);
      }
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [movieId, onSummaryChange, page, user]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  async function persistReview() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const result = await movieService.saveMovieReview(movieId, { rating, comment });
      setMyReview(result.review);
      setRating(result.review.rating);
      setComment(result.review.comment);
      setPage(1);
      const updated = await movieService.movieReviews(movieId);
      setData({ ...updated, reviews: updated.reviews });
      onSummaryChange?.({ average_rating: updated.average_rating, review_count: updated.review_count });
      setMessage(result.created ? "Đã gửi đánh giá của bạn." : "Đã cập nhật đánh giá của bạn.");
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  }

  function submitReview() {
    if (!user) {
      requireLogin(persistReview);
      return;
    }
    persistReview();
  }

  async function removeReview() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await movieService.deleteMyMovieReview(movieId);
      setMyReview(null);
      setRating(5);
      setComment("");
      setPage(1);
      const updated = await movieService.movieReviews(movieId);
      setData({ ...updated, reviews: updated.reviews });
      onSummaryChange?.({ average_rating: updated.average_rating, review_count: updated.review_count });
      setMessage("Đã xóa đánh giá của bạn.");
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="movie-reviews" id="movie-reviews" aria-labelledby="movie-reviews-title">
      <div className="movie-reviews-heading">
        <div>
          <span className="movie-detail-kicker"><MovieInfoIcon name="users" />CỘNG ĐỒNG CINEVO</span>
          <h2 id="movie-reviews-title">Đánh giá &amp; bình luận</h2>
          <p className="muted small">Chia sẻ cảm nhận thật của bạn về bộ phim.</p>
        </div>
        <div className="movie-review-score" aria-live="polite">
          <strong>{data?.review_count ? Number(data.average_rating).toFixed(1) : "—"}</strong>
          <span className="movie-review-score-stars" aria-label={data?.review_count ? `${data.average_rating} trên 5 sao trung bình` : "Chưa có đánh giá"}>
            {data?.review_count ? "★★★★★" : "☆☆☆☆☆"}
          </span>
          <small>{data?.review_count || 0} đánh giá</small>
        </div>
      </div>

      <div className="movie-review-compose">
        <h3>{myReview ? "Cập nhật đánh giá của bạn" : "Viết đánh giá"}</h3>
        {user ? (
          <p className="movie-review-author">Đang bình luận với tên <strong>{user.full_name}</strong></p>
        ) : (
          <p className="movie-review-author">Bạn cần đăng nhập để gửi đánh giá và bình luận.</p>
        )}
        <ReviewStars value={rating} onChange={setRating} disabled={saving} />
        <label className="movie-review-comment-label" htmlFor={`movie-review-${movieId}`}>Bình luận</label>
        <textarea
          id={`movie-review-${movieId}`}
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          maxLength={1000}
          minLength={2}
          placeholder="Bạn nghĩ gì về bộ phim? (2–1000 ký tự)"
          disabled={saving}
        />
        <div className="movie-review-compose-footer">
          <small>{comment.length}/1000 ký tự</small>
          <div>
            {myReview && (
              <button className="btn btn-ghost btn-sm" type="button" onClick={removeReview} disabled={saving}>
                Xóa đánh giá
              </button>
            )}
            {user
              ? <button className="btn btn-red btn-sm" type="button" onClick={submitReview}
                  disabled={saving || comment.trim().length < 2}>
                  {saving ? "Đang gửi..." : myReview ? "Cập nhật đánh giá" : "Gửi đánh giá"}
                </button>
              : <button className="btn btn-red btn-sm" type="button" onClick={submitReview}
                  disabled={saving || authLoading || comment.trim().length < 2}>
                  Đăng nhập để bình luận
                </button>}
          </div>
        </div>
      </div>

      {error && <p className="movie-review-error" role="alert">{error}</p>}
      {message && <p className="movie-review-success" role="status">{message}</p>}
      {loading && !data ? <p className="muted">Đang tải bình luận...</p> : error && !data ? null : data?.reviews.length ? (
        <div className="movie-review-list">
          {data.reviews.map((review) => (
            <article className="movie-review-item" key={review.id}>
              <div className="movie-review-item-heading">
                <div className="movie-review-avatar" aria-hidden="true">
                  {(review.user_name || "N").trim().charAt(0).toLocaleUpperCase("vi-VN")}
                </div>
                <div>
                  <strong>{review.user_name}</strong>
                  <small>{formatReviewDate(review.updated_at || review.created_at)}</small>
                </div>
                <span className="movie-review-item-stars" aria-label={`${review.rating} trên 5 sao`}>
                  {"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}
                </span>
              </div>
              <p>{review.comment}</p>
            </article>
          ))}
          {data.has_more && (
            <button className="btn btn-ghost movie-review-load-more" type="button"
              onClick={() => setPage((current) => current + 1)} disabled={loading}>
              {loading ? "Đang tải..." : "Xem thêm bình luận"}
            </button>
          )}
        </div>
      ) : (
        <div className="movie-review-empty">
          <MovieInfoIcon name="users" />
          <p>Chưa có bình luận nào. Hãy là người đầu tiên chia sẻ cảm nhận!</p>
        </div>
      )}
      {!user && !authLoading && (
        <p className="movie-review-signin">Bạn đã có tài khoản? <Link to="/user/login">Đăng nhập</Link> để bình luận.</p>
      )}
    </section>
  );
}
