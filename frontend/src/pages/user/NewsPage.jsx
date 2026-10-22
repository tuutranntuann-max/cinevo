import { useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";
import { useUserPreferences } from "../../context/UserPreferencesContext";

function formatPublishedAt(value, language) {
  if (!value) return "";
  return new Intl.DateTimeFormat(language === "en" ? "en-US" : "vi-VN", { dateStyle: "long" }).format(new Date(value));
}

export default function NewsPage() {
  const { t, language } = useUserPreferences();
  const [movies, setMovies] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const loadNews = async () => {
      try {
        const result = await api.get("/content/news");
        if (active) {
          setMovies(result);
          setError("");
        }
      } catch (loadError) {
        if (active) setError(loadError.message);
      }
    };
    loadNews();
    const timer = window.setInterval(loadNews, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <section className="news-page">
      <header className="news-heading">
        <span className="eyebrow">CINEVO UPDATE</span>
        <h1 className="page-title">{t("Tin tức phim")}</h1>
        <p className="muted">{t("Tin báo chí về phim, diễn viên và các hoạt động điện ảnh do Cinevo cập nhật.")}</p>
      </header>
      <ErrorBox message={error} />
      {!movies ? <Loading /> : movies.length ? (
        <div className="news-grid">
          {movies.map((article) => (
            <article className="news-card" key={article.id}>
              {article.image_url ? (
                <div className="news-poster">
                  <img
                    src={article.image_url}
                    alt={article.title}
                    onError={(event) => {
                      event.currentTarget.hidden = true;
                      event.currentTarget.parentElement.classList.add("news-poster-image-error");
                    }}
                  />
                  <span className="news-status">{article.category}</span>
                  <span className="news-poster-fallback" aria-hidden="true">{article.category}</span>
                </div>
              ) : (
                <div className="news-poster news-poster-placeholder" aria-hidden="true">
                  <span>{article.category}</span>
                </div>
              )}
              <div className="news-card-copy">
                <time dateTime={article.published_at}>{formatPublishedAt(article.published_at, language)}</time>
                <h2>{article.title}</h2>
                <p>{article.summary}</p>
                <details className="news-article-details">
                  <summary>{t("Đọc bài viết")} <span aria-hidden="true">→</span></summary>
                  <p>{article.body}</p>
                </details>
                {article.source && <small className="muted">{t("Nguồn:")} {article.source}</small>}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="state-box">{t("Chưa có tin tức. Các tin về phim và diễn viên sẽ được cập nhật tại đây.")}</div>
      )}
    </section>
  );
}
