// Chọn ngày → rạp → suất chiếu của một phim.
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import CitySelector from "../../components/CitySelector";
import MovieInfoIcon from "../../components/MovieInfoIcon";
import MovieTrailerPlayer from "../../components/MovieTrailerPlayer";
import Poster from "../../components/Poster";
import { useBooking } from "../../context/BookingContext";
import { movieService } from "../../services/movieService";
import { formatTime, nextDays, toISODate } from "../../utils/format";
import { useUserPreferences } from "../../context/UserPreferencesContext";

export default function ShowtimePage() {
  const { t, language } = useUserPreferences();
  const { movieId } = useParams();
  const { city } = useBooking();
  const days = useMemo(() => nextDays(14), []);
  const [date, setDate] = useState(toISODate(days[0]));
  const [movie, setMovie] = useState(null);
  const [showtimes, setShowtimes] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setMovie(null);
    setError("");
    movieService.movie(movieId).then(setMovie).catch((e) => setError(e.message));
  }, [movieId]);
  useEffect(() => {
    setShowtimes(null);
    setError("");
    movieService.showtimes({ movie_id: movieId, city }).then((items) => {
      setShowtimes(items);
      const firstAvailableDate = items[0]?.start_time.slice(0, 10);
      if (firstAvailableDate) setDate(firstAvailableDate);
    }).catch((e) => setError(e.message));
  }, [movieId, city]);

  const byCinema = (showtimes || []).filter((showtime) => showtime.start_time.slice(0, 10) === date)
    .reduce((acc, s) => ((acc[s.cinema.id] ||= { cinema: s.cinema, items: [] }).items.push(s), acc), {});
  return (
    <section className="showtime-page">
      {movie && (
        <article className="showtime-movie-summary">
          <Poster movie={movie} className="showtime-movie-poster" />
          <div className="showtime-movie-copy">
            <span className="showtime-movie-kicker"><MovieInfoIcon name="film" />{t("ĐẶT VÉ XEM PHIM")}</span>
            <h1>{movie.title}</h1>
            <p className="showtime-movie-genres">{movie.genre || t("Phim điện ảnh")}</p>
            <div className="showtime-movie-facts">
              <span><MovieInfoIcon name="star" />{Number(movie.rating || 0).toFixed(1)} / 10</span>
              <span><MovieInfoIcon name="clock" />{movie.duration_minutes} {t("phút")}</span>
              <span><MovieInfoIcon name="film" />{movie.age_rating || "P"}</span>
              <span><MovieInfoIcon name="users" />{movie.cast || t("Diễn viên chưa cập nhật")}</span>
            </div>
          </div>
          <div className="showtime-movie-trailer">
            <MovieTrailerPlayer movie={movie} />
            <span><MovieInfoIcon name="film" />{t("Trailer phim")}</span>
          </div>
        </article>
      )}
      <div className="showtime-heading-row">
        <div>
          <span className="showtime-movie-kicker"><MovieInfoIcon name="calendar" />{t("LỊCH CHIẾU")}</span>
          <h2 className="page-title">{t("Chọn ngày và suất chiếu")}</h2>
        </div>
        <label className="showtime-city-control"><span>{t("Khu vực")}</span><CitySelector /></label>
      </div>
      <div className="date-tabs showtime-date-tabs" role="tablist" aria-label={t("Chọn ngày chiếu")}>
        {days.map((d) => {
          const iso = toISODate(d);
          return (
            <button key={iso} role="tab" aria-selected={iso === date} className={`date-tab ${iso === date ? "active" : ""}`} onClick={() => setDate(iso)}>
              <small>{d.toLocaleDateString(language === "en" ? "en-US" : "vi-VN", { weekday: "short" })}</small><b>{d.getDate()}/{d.getMonth() + 1}</b>
            </button>
          );
        })}
      </div>
      <ErrorBox message={error} />
      {!showtimes && !error ? <Loading /> : Object.values(byCinema).length ? (
        Object.values(byCinema).map(({ cinema, items }) => (
          <article key={cinema.id} className="card">
            {cinema.chain && <p className="small muted">{cinema.chain}</p>}
            <h3>{cinema.name}</h3>
            <p className="muted small">{cinema.address}</p>
            <div className="time-grid">
              {items.map((s) => (
                <Link key={s.id} to={`/user/seats/${s.id}`} className="time-btn">
                  <b>{formatTime(s.start_time)}</b><small>{s.room.name} · {s.room.room_type}</small>
                </Link>
              ))}
            </div>
          </article>
        ))
      ) : showtimes && <div className="state-box">{t("Không có suất chiếu trong ngày này. Hãy chọn ngày hoặc khu vực khác.")}</div>}
    </section>
  );
}
