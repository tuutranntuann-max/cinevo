// Trang chủ: chọn khu vực → khám phá phim. Không cần đăng nhập.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import CitySelector from "../../components/CitySelector";
import MovieHeroCarousel from "../../components/MovieHeroCarousel";
import MovieCard from "../../components/MovieCard";
import Loading from "../../components/Loading";
import { useBooking } from "../../context/BookingContext";
import { useFeatures } from "../../context/FeaturesContext";
import { aiService } from "../../services/aiService";
import { movieService } from "../../services/movieService";
import { useUserPreferences } from "../../context/UserPreferencesContext";

const GENRES = ["Hành động", "Hài", "Kinh dị", "Khoa học viễn tưởng", "Tình cảm"];

export default function HomePage() {
  const { city } = useBooking();
  const { features } = useFeatures();
  const { t } = useUserPreferences();
  const [showing, setShowing] = useState(null);
  const [watchable, setWatchable] = useState([]);
  const [coming, setComing] = useState([]);
  const [genre, setGenre] = useState("");
  const [ai, setAi] = useState(null);

  useEffect(() => {
    setShowing(null);
    movieService.movies({ status: "now_showing", city }).then(setShowing).catch(() => setShowing([]));
  }, [city]);
  useEffect(() => {
    movieService.watchableMovies().then(setWatchable).catch(() => setWatchable([]));
  }, []);
  useEffect(() => { movieService.movies({ status: "coming_soon" }).then(setComing).catch(() => {}); }, []);
  useEffect(() => {
    if (!features.ai) return;     // AI đang tắt: không gọi API
    aiService.recommendMovies(genre).then(setAi).catch(() => setAi(null));
  }, [genre, features.ai]);

  return (
    <>
      <MovieHeroCarousel
        movies={[
          ...(showing || []),
          ...watchable
            .filter((movie) => !(showing || []).some((showingMovie) => showingMovie.id === movie.id))
            .map((movie) => ({ ...movie, watchable: true })),
        ]}
        city={city}
      />
      <div className="home-content">
        <div className="home-discovery">
          <div>
            <p className="small muted">{t("Bạn xem phim ở đâu?")}</p>
            <details className="home-city-picker">
              <summary>{city || t("Tất cả khu vực")}</summary>
              <CitySelector variant="chips" />
            </details>
          </div>
          <Link to="/user/movies" className="btn btn-ghost">{t("Xem tất cả phim")}</Link>
        </div>

        <section>
          <h2 className="section-title">{t("Phim đang chiếu")}{city && ` tại ${city}`}</h2>
          {!showing ? <Loading /> : showing.length ? (
            <div className="grid">{showing.map((m) => <MovieCard key={m.id} movie={m} />)}</div>
          ) : <div className="state-box">{t("Chưa có suất chiếu tại khu vực này. Hãy thử khu vực khác.")}</div>}
        </section>

        {features.ai && (
          <section>
            <h2 className="section-title">{t("Cinevo AI gợi ý cho bạn")}</h2>
            <div className="chips">
              <button className={`chip ${!genre ? "active" : ""}`} onClick={() => setGenre("")}>{t("Nổi bật")}</button>
              {GENRES.map((g) => <button key={g} className={`chip ${g === genre ? "active" : ""}`} onClick={() => setGenre(g)}>{t(g)}</button>)}
            </div>
            {ai && (
              <>
                <p className="muted">{ai.message}</p>
                <div className="grid">{ai.movies.slice(0, 4).map((m) => <MovieCard key={m.id} movie={m} />)}</div>
              </>
            )}
          </section>
        )}

        {coming.length > 0 && (
          <section>
            <h2 className="section-title">{t("Sắp chiếu")}</h2>
            <div className="grid">{coming.map((m) => <MovieCard key={m.id} movie={m} />)}</div>
          </section>
        )}
      </div>
    </>
  );
}
