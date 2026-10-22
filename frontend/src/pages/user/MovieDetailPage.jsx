import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import MovieInfoIcon from "../../components/MovieInfoIcon";
import MovieTrailerPlayer from "../../components/MovieTrailerPlayer";
import MovieReviews from "../../components/MovieReviews";
import Poster from "../../components/Poster";
import { movieService } from "../../services/movieService";
import { useUserPreferences } from "../../context/UserPreferencesContext";

function MovieFact({ icon, label, children, highlight = false }) {
  const { t } = useUserPreferences();
  return (
    <div className={`movie-detail-fact${highlight ? " is-highlight" : ""}`}>
      <span className="movie-detail-fact-label"><MovieInfoIcon name={icon} />{label}</span>
      <strong>{children || t("Chưa cập nhật")}</strong>
    </div>
  );
}

export default function MovieDetailPage() {
  const { t, language } = useUserPreferences();
  const { id } = useParams();
  const [movie, setMovie] = useState(null);
  const [error, setError] = useState("");
  const [reviewSummary, setReviewSummary] = useState({ average_rating: null, review_count: 0 });
  const updateReviewSummary = useCallback((summary) => setReviewSummary(summary), []);
  useEffect(() => {
    setMovie(null);
    setError("");
    movieService.movie(id).then(setMovie).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <ErrorBox message={error} />;
  if (!movie) return <Loading />;

  const genreList = (movie.genre || "").split(",").map((genre) => genre.trim()).filter(Boolean);

  return (
    <section className="movie-detail-page">
      <div className="movie-detail-backdrop" style={movie.poster_url ? { backgroundImage: `url("${movie.poster_url}")` } : undefined} aria-hidden="true" />
      <div className="movie-detail-shell">
        <div className="movie-detail-hero">
          <div className="movie-detail-poster-frame">
            <Poster movie={movie} className="movie-detail-poster" />
          </div>

          <div className="movie-detail-copy">
            <span className="movie-detail-kicker">
              <MovieInfoIcon name="film" />
              {movie.status === "now_showing" ? t("ĐANG CHIẾU TẠI RẠP") : t("SẮP CÔNG CHIẾU")}
            </span>
            {movie.title_logo_enabled && movie.title_logo_url
              ? <img className="movie-detail-title-logo" src={movie.title_logo_url} alt={movie.title} />
              : <h1 className="movie-detail-title">{movie.title}</h1>}
            <div className="movie-detail-genres">
              {genreList.length ? genreList.map((genre) => <span key={genre}>{genre}</span>) : <span>{t("Phim điện ảnh")}</span>}
            </div>

            <div className="movie-detail-facts">
              <MovieFact icon="star" label={`${t("Đánh giá người xem")} · ${reviewSummary.review_count}`} highlight>
                {reviewSummary.review_count ? `${reviewSummary.average_rating} / 5 ${t("sao")}` : t("Chưa có đánh giá")}
              </MovieFact>
              <MovieFact icon="clock" label={t("Thời lượng")}>{movie.duration_minutes} {t("phút")}</MovieFact>
              <MovieFact icon="film" label={t("Độ tuổi")}>{movie.age_rating || "P"}</MovieFact>
              <MovieFact icon="users" label={t("Diễn viên")}>{movie.cast || t("Chưa cập nhật")}</MovieFact>
              {movie.release_date && <MovieFact icon="calendar" label={t("Khởi chiếu")}>{new Date(movie.release_date).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")}</MovieFact>}
              {movie.director && <MovieFact icon="director" label={t("Đạo diễn")}>{movie.director}</MovieFact>}
            </div>

            {movie.description && (
              <div className="movie-detail-description">
                <h2><MovieInfoIcon name="info" />{t("Nội dung phim")}</h2>
                <p>{movie.description}</p>
              </div>
            )}
            <div className="movie-detail-actions">
              {movie.status === "now_showing"
                ? <Link className="btn btn-red movie-detail-booking" to={`/user/showtimes/${movie.id}`}>
                    <MovieInfoIcon name="calendar" />{t("Chọn ngày, rạp và suất chiếu")}
                  </Link>
                : <span className="movie-detail-coming-soon">{t("Phim sắp chiếu")}</span>}
              {movie.film_url && (
                <Link className="btn btn-ghost" to={`/user/watch/${movie.id}`}>{t("Xem ngay")}</Link>
              )}
              <a className="btn btn-ghost" href="#movie-reviews">{t("Đánh giá & bình luận")}</a>
            </div>
          </div>

          <aside className="movie-detail-trailer">
            <div className="movie-detail-trailer-heading">
              <span><MovieInfoIcon name="film" />{t("XEM TRƯỚC")}</span>
              <h2>{t("Trailer phim")}</h2>
            </div>
            <MovieTrailerPlayer movie={movie} className="movie-detail-trailer-video" />
          </aside>
        </div>
        <MovieReviews movieId={movie.id} onSummaryChange={updateReviewSummary} />
      </div>
    </section>
  );
}
