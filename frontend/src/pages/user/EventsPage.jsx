import { useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";
import { useUserPreferences } from "../../context/UserPreferencesContext";

function formatDate(value, language) {
  if (!value) return "";
  return new Intl.DateTimeFormat(language === "en" ? "en-US" : "vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function EventsPage() {
  const { t, language } = useUserPreferences();
  const [events, setEvents] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api.get("/content/events")
      .then((result) => { if (active) setEvents(result); })
      .catch((loadError) => { if (active) setError(loadError.message); });
    return () => { active = false; };
  }, []);

  return (
    <section className="events-page">
      <header className="events-heading">
        <span className="eyebrow">CINEVO EXPERIENCES</span>
        <h1 className="page-title">{t("Sự kiện & chương trình")}</h1>
        <p className="muted">{t("Khám phá các chương trình và sự kiện đang diễn ra tại Cinevo.")}</p>
      </header>
      <ErrorBox message={error} />
      {!events ? <Loading /> : events.length ? (
        <div className="events-grid">
          {events.map((event) => (
            <article className="event-card" key={event.id}>
              {event.image_url ? (
                <img className="event-poster" src={event.image_url} alt={`Poster ${event.title}`} />
              ) : (
                <div className="event-poster event-poster-placeholder" aria-hidden="true">
                  <span>CINEVO EVENT</span>
                </div>
              )}
              <div className="event-card-copy">
                <span className="event-kicker">{t("SỰ KIỆN CINEVO")}</span>
                <h2>{event.title}</h2>
                <p className="muted">{event.summary}</p>
                {(event.starts_at || event.ends_at) && (
                  <p className="event-dates">
                    {event.starts_at && <time dateTime={event.starts_at}>{t("Từ")} {formatDate(event.starts_at, language)}</time>}
                    {event.ends_at && <time dateTime={event.ends_at}> · {t("Đến")} {formatDate(event.ends_at, language)}</time>}
                  </p>
                )}
                {event.body && (
                  <details className="event-details">
                    <summary>{t("Xem thông tin chương trình")}</summary>
                    <p>{event.body}</p>
                  </details>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="state-box">{t("Chưa có sự kiện đang diễn ra. Hãy quay lại sau để xem chương trình mới.")}</div>
      )}
    </section>
  );
}
