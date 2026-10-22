import { Link } from "react-router-dom";
import Poster from "./Poster";
import { useUserPreferences } from "../context/UserPreferencesContext";

export default function MovieCard({ movie }) {
  const { t } = useUserPreferences();
  return (
    <Link to={`/user/movies/${movie.id}`} className="movie-card" aria-label={`${t("Xem chi tiết phim")} ${movie.title}`}>
      <div className="movie-card-art">
        <Poster movie={movie} />
        <div className="movie-card-reveal">
          <span className="movie-card-rating">★ {movie.rating || 0}/10 · {movie.age_rating || "P"}</span>
          <h3>{movie.title}</h3>
          <p className="movie-card-meta">{movie.genre || t("Đang cập nhật")} · {movie.duration_minutes} {t("phút")}</p>
          <p className="movie-card-description">{movie.description || t("Khám phá thông tin và lịch chiếu của bộ phim.")}</p>
          <span className="movie-card-cta">{t("Khám phá phim")} <span aria-hidden="true">→</span></span>
        </div>
        <span className="movie-card-hint" aria-hidden="true">{t("Xem nội dung phim")} <span>↗</span></span>
      </div>
      <div className="movie-card-body">
        <h3>{movie.title}</h3>
        <p className="muted">{movie.genre}</p>
        <p className="muted small">{movie.duration_minutes} {t("phút")} · {movie.age_rating} · ★ {movie.rating}</p>
      </div>
    </Link>
  );
}
