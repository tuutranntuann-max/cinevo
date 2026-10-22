import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import Poster from "../../components/Poster";
import { api } from "../../services/api";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function MovieWatchPage() {
  const { t, language } = useUserPreferences();
  const { id } = useParams();
  const [movies, setMovies] = useState(null);
  const [movie, setMovie] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setMovies(null);
    setMovie(null);
    setError("");
    const path = id ? `/movies/watch/${id}` : "/movies/watch";
    api.get(path).then((result) => {
      if (id) setMovie(result);
      else setMovies(result);
    }).catch((e) => {
      setError(e.message);
      setMovies([]);
    });
  }, [id]);

  if (error && id) return <ErrorBox message={error} />;
  if (id && !movie) return <Loading />;
  return (
    <section className="watch-page">
      <h1 className="page-title">{movie ? movie.title : t("Xem phim")}</h1>
      {!movie && <p className="muted">{t("Xem phần giới thiệu miễn phí; đăng ký gói thành viên để mở khóa phim trực tuyến.")}</p>}
      {!movie && error && <ErrorBox message={error} />}
      {!movie && !movies ? <Loading /> : movie ? (
        <>
          {movie.can_watch ? (
            <video className="watch-film-player" src={movie.film_url}
              poster={movie.film_image_url || movie.poster_url || undefined} controls playsInline
              preload="metadata" aria-label={`${t("Xem phim")} ${movie.title}`}>
              {(movie.subtitles || []).map((subtitle, index) => (
                <track key={subtitle.id} kind="subtitles" src={subtitle.url}
                  srcLang={subtitle.language} label={subtitle.label} default={index === 0} />
              ))}
            </video>
          ) : (
            <section className="watch-preview">
              {movie.trailer_url && /\.(mp4|webm)(?:\?|$)/i.test(movie.trailer_url) ? (
                <video className="watch-film-player" src={movie.trailer_url}
                  poster={movie.poster_url || undefined} controls playsInline preload="metadata"
                  aria-label={`${t("Xem giới thiệu")} ${movie.title}`} />
              ) : movie.poster_url ? (
                <img className="watch-preview-poster" src={movie.poster_url} alt={`Poster ${movie.title}`} />
              ) : null}
              <div className="watch-preview-message">
                <h2>{t("Đăng ký thành viên để xem phim")}</h2>
                <p className="muted">{t("Bạn có thể xem phần giới thiệu miễn phí. Để xem toàn bộ phim, hãy mua gói thành viên và chờ nhân viên xác nhận thanh toán.")}</p>
                <Link className="btn btn-red" to="/user/membership">{t("Xem các gói thành viên")}</Link>
              </div>
            </section>
          )}
          <dl className="watch-film-details">
            {movie.director && <><dt>{t("Tác giả / Đạo diễn")}</dt><dd>{movie.director}</dd></>}
            {movie.release_date && <><dt>{t("Ngày ra phim")}</dt><dd>{new Date(movie.release_date).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")}</dd></>}
            {movie.theatrical_end_date && <><dt>{t("Ngày kết thúc chiếu rạp")}</dt><dd>{new Date(movie.theatrical_end_date).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")}</dd></>}
            <dt>{t("Thời lượng")}</dt><dd>{movie.duration_minutes} {t("phút")}</dd>
            {movie.genre && <><dt>{t("Thể loại")}</dt><dd>{movie.genre}</dd></>}
            {movie.age_rating && <><dt>{t("Phân loại tuổi")}</dt><dd>{movie.age_rating}</dd></>}
          </dl>
          {movie.description && <div className="watch-film-description">
            <h2>{t("Mô tả phim")}</h2>
            <p className="desc">{movie.description}</p>
          </div>}
          <Link className="btn btn-ghost watch-film-info-link" to={`/user/movies/${movie.id}`}>
            {t("Thông tin phim, vé & bình luận")}
          </Link>
          <Link className="btn btn-ghost" to="/user/watch">{t("Quay lại danh sách phim")}</Link>
        </>
      ) : movies?.length ? (
        <div className="watch-film-grid">
          {movies.map((item) => (
            <Link className="watch-film-card" key={item.id} to={`/user/watch/${item.id}`}
              aria-label={`${t("Xem phim")} ${item.title}`}>
              <span className="watch-film-thumb">
                <Poster movie={{ ...item, poster_url: item.film_image_url || item.poster_url }}
                  className="watch-film-poster" />
                <span className="watch-film-overlay">
                  <span className="watch-film-overlay-title">{item.title}</span>
                  <span className="watch-film-overlay-meta">
                    {                    [item.genre, item.duration_minutes ? `${item.duration_minutes} ${t("phút")}` : null, item.age_rating]
                      .filter(Boolean).join(" · ")}
                  </span>
                  {item.description && <span className="watch-film-overlay-description">{item.description}</span>}
                  <span className="watch-film-play">
                    <span aria-hidden="true">{item.can_watch ? "▶" : "▣"}</span>
                    {item.can_watch ? t("Xem phim") : t("Xem giới thiệu")}
                  </span>
                </span>
                <span className="watch-film-play-badge" aria-hidden="true">▶</span>
              </span>
              <span className="watch-film-card-title">{item.title}</span>
              <span className="watch-film-card-meta">
                {[item.genre, item.duration_minutes ? `${item.duration_minutes} ${t("phút")}` : null]
                  .filter(Boolean).join(" · ")}
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <div className="state-box">
          {t("Chưa có phim nào đủ điều kiện xem trực tuyến.")}
          <p className="muted small">{t("Phim chỉ xuất hiện sau khi đã kết thúc công chiếu và quản trị viên tải bản phim đầy đủ lên.")}</p>
        </div>
      )}
    </section>
  );
}
