import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAppearance } from "../context/AppearanceContext";

const FAVORITES_KEY = "cinevo_favorite_movies";

function loadFavorites() {
  try {
    const saved = JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function PosterPreview({ movie, className = "" }) {
  const [failedPosterUrl, setFailedPosterUrl] = useState("");
  if (movie.poster_url && failedPosterUrl !== movie.poster_url) {
    return <img className={className} src={movie.poster_url} alt="" onError={() => setFailedPosterUrl(movie.poster_url)} />;
  }
  return (
    <div className={`${className} movie-hero-fallback`} style={{ "--poster-color": movie.poster_color || "#52131b" }}>
      <span>{movie.title}</span>
    </div>
  );
}

export default function MovieHeroCarousel({ movies, city }) {
  const { appearance } = useAppearance();
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [favorites, setFavorites] = useState(loadFavorites);
  const [muted, setMuted] = useState(false);
  const [videoProgress, setVideoProgress] = useState(0);
  const [notice, setNotice] = useState("");
  const [failedTitleLogoUrl, setFailedTitleLogoUrl] = useState("");
  const videoRef = useRef(null);
  const audioRef = useRef(null);
  const activeMovie = movies[activeIndex];
  const thumbnailStartIndex = Math.min(Math.max(activeIndex - 2, 0), Math.max(movies.length - 5, 0));
  const visibleMovies = movies.slice(thumbnailStartIndex, thumbnailStartIndex + 5);
  const bannerVideoUrl = appearance.banner_media_type === "video" ? appearance.banner_media_url : null;
  const legacyAudioTrailer = activeMovie?.trailer_url?.includes("format=mp3") ? activeMovie.trailer_url : null;
  const movieAudioUrl = activeMovie?.audio_url || legacyAudioTrailer;
  const movieVideoUrl = legacyAudioTrailer ? bannerVideoUrl : activeMovie?.trailer_url || bannerVideoUrl;
  const hasMovieVideo = Boolean(movieVideoUrl);
  const hasMovieAudio = Boolean(movieAudioUrl);
  const hasMovieMedia = hasMovieVideo || hasMovieAudio;
  const hasSeparateAudio = Boolean(movieVideoUrl && movieAudioUrl);
  const bannerImageUrl = appearance.banner_media_type === "image" ? appearance.banner_media_url : null;
  const isFavorite = activeMovie ? favorites.includes(activeMovie.id) : false;

  useEffect(() => {
    if (activeIndex >= movies.length) setActiveIndex(0);
  }, [activeIndex, movies.length]);

  useEffect(() => {
    if (paused || hasMovieMedia || movies.length < 2) return undefined;
    const timer = window.setInterval(() => {
      setActiveIndex((index) => (index + 1) % movies.length);
    }, 6000);
    return () => window.clearInterval(timer);
  }, [movies.length, paused, hasMovieMedia]);

  useEffect(() => {
    setVideoProgress(0);
    setNotice("");
    setFailedTitleLogoUrl("");
  }, [activeMovie?.id]);

  useEffect(() => {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
  }, [favorites]);

  if (!activeMovie) {
    return (
      <section className="movie-hero movie-hero-empty" aria-label="Phim nổi bật">
        <div>
          <span className="movie-hero-eyebrow">CINEVO · RẠP CHIẾU PHIM</span>
          <h1>Chọn phim hay.<br />Chọn ghế đẹp.</h1>
          <p>Khám phá phim và suất chiếu tại khu vực của bạn.</p>
        </div>
      </section>
    );
  }

  const selectMovie = (index) => setActiveIndex(index);
  const move = (offset) => setActiveIndex((index) => (index + offset + movies.length) % movies.length);
  const handleVideoTimeUpdate = () => {
    const video = videoRef.current;
    const progressMedia = video || audioRef.current;
    if (!progressMedia || !Number.isFinite(progressMedia.duration) || progressMedia.duration <= 0) return;
    setVideoProgress(Math.min(1, progressMedia.currentTime / progressMedia.duration));
    const audio = audioRef.current;
    if (video && audio && Math.abs(video.currentTime - audio.currentTime) > 0.4) {
      audio.currentTime = video.currentTime;
    }
  };
  const handleVideoEnded = () => {
    setVideoProgress(1);
    if (movies.length > 1) move(1);
  };
  const handleVideoReady = async () => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = muted || hasSeparateAudio;
    const audio = audioRef.current;
    if (audio) audio.currentTime = video.currentTime || 0;
    try {
      await video.play();
      if (audio) {
        audio.muted = muted;
        await audio.play();
      }
    } catch {
      if (muted) {
        if (audio) setNotice("Âm thanh bị chặn tự động. Nhấn biểu tượng loa để bật tiếng.");
        return;
      }
      if (!hasSeparateAudio) {
        video.muted = true;
        setMuted(true);
        setNotice("Trình duyệt chặn tự phát có tiếng. Nhấn biểu tượng loa để bật âm thanh.");
      }
      try {
        await video.play();
        if (audio) {
          audio.muted = true;
          await audio.play();
          setMuted(true);
          setNotice("Trình duyệt chặn tự phát âm thanh. Nhấn biểu tượng loa để bật tiếng.");
        }
      } catch {
        setNotice("Không thể tự phát video. Hãy thử chọn lại phim.");
      }
    }
  };
  const handleAudioReady = async () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.muted = muted;
    if (videoRef.current) {
      audio.currentTime = videoRef.current.currentTime || 0;
      if (!videoRef.current.paused) {
        try {
          await audio.play();
        } catch {
          setNotice("Âm thanh bị chặn tự động. Nhấn biểu tượng loa để bật tiếng.");
        }
      }
      return;
    }
    try {
      await audio.play();
    } catch {
      if (!muted) {
        audio.muted = true;
        setMuted(true);
        setNotice("Trình duyệt chặn tự phát có tiếng. Nhấn biểu tượng loa để bật âm thanh.");
      }
    }
  };
  const toggleFavorite = () => {
    setFavorites((current) => current.includes(activeMovie.id)
      ? current.filter((id) => id !== activeMovie.id)
      : [...current, activeMovie.id]);
    setNotice(isFavorite ? "Đã xóa khỏi phim yêu thích" : "Đã thêm vào phim yêu thích");
  };
  const shareMovie = async () => {
    const shareData = {
      title: activeMovie.title,
      text: `Xem thông tin phim ${activeMovie.title} trên CINEVO`,
      url: `${window.location.origin}/user/movies/${activeMovie.id}`,
    };
    try {
      if (navigator.share) await navigator.share(shareData);
      else {
        await navigator.clipboard.writeText(shareData.url);
        setNotice("Đã sao chép liên kết phim");
      }
    } catch (error) {
      if (error.name !== "AbortError") setNotice("Không thể chia sẻ phim lúc này");
    }
  };
  const toggleMute = async () => {
    const nextMuted = !muted;
    setMuted(nextMuted);
    const mediaElements = [videoRef.current, audioRef.current].filter(Boolean);
    for (const media of mediaElements) {
      media.muted = nextMuted || (media === videoRef.current && hasSeparateAudio);
      if (!nextMuted) {
        try {
          await media.play();
        } catch {
          setNotice("Trình duyệt chưa cho phép phát tiếng. Hãy thử nhấn biểu tượng loa lần nữa.");
        }
      }
    }
  };

  return (
    <section
      className="movie-hero"
      aria-label="Phim nổi bật"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false);
      }}
    >
      <div
        key={activeMovie.id}
        className="movie-hero-backdrop"
        style={!hasMovieVideo && (bannerImageUrl || activeMovie.poster_url)
            ? { backgroundImage: `url("${bannerImageUrl || activeMovie.poster_url}")` }
            : {
              backgroundColor: activeMovie.poster_color,
              backgroundImage: activeMovie.poster_url ? `url("${activeMovie.poster_url}")` : undefined,
            }}
        >
          {hasMovieVideo && (
              <video
                ref={videoRef}
                key={movieVideoUrl}
                src={movieVideoUrl}
              autoPlay
              muted={muted || hasSeparateAudio}
              playsInline
              preload="metadata"
              aria-hidden="true"
              tabIndex={-1}
              onCanPlay={handleVideoReady}
              onTimeUpdate={handleVideoTimeUpdate}
              onEnded={handleVideoEnded}
              onError={() => {
                setNotice("Không phát được video này. Hãy kiểm tra tệp video đã tải lên.");
              }}
            />
          )}
          {hasMovieAudio && (
            <audio
              ref={audioRef}
              key={movieAudioUrl}
              src={movieAudioUrl}
              autoPlay
              muted={muted}
              preload="metadata"
              onCanPlay={handleAudioReady}
              onTimeUpdate={!hasMovieVideo ? handleVideoTimeUpdate : undefined}
              onEnded={!hasMovieVideo ? handleVideoEnded : undefined}
              onError={() => setNotice("Không phát được âm thanh MP3. Hãy kiểm tra tệp đã tải lên.")}
            />
          )}
      </div>
      <div className="movie-hero-shade" aria-hidden="true" />
      <div className="movie-hero-main" key={`content-${activeMovie.id}`}>
        <div className="movie-hero-copy">
          <span className="movie-hero-eyebrow">
            {activeMovie.watchable
              ? "ĐÃ KẾT THÚC CÔNG CHIẾU · XEM TRỰC TUYẾN"
              : city ? `ĐANG CHIẾU TẠI ${city}` : "ĐANG CHIẾU · PHIM NỔI BẬT"}
          </span>
          {activeMovie.title_logo_enabled && activeMovie.title_logo_url && failedTitleLogoUrl !== activeMovie.title_logo_url
            ? <img className="movie-hero-title-logo" src={activeMovie.title_logo_url} alt={activeMovie.title}
              onError={() => setFailedTitleLogoUrl(activeMovie.title_logo_url)} />
            : <h1>{activeMovie.title}</h1>}
          <div className="movie-hero-badges">
            <span className="movie-hero-badge movie-hero-rating"><span aria-hidden="true">★</span> {Number(activeMovie.rating || 0).toFixed(1)}</span>
            {activeMovie.genre && <span className="movie-hero-badge">{activeMovie.genre.split(",")[0].trim()}</span>}
            <span className="movie-hero-badge">{activeMovie.age_rating || "P"}</span>
            {hasMovieVideo && <span className="movie-hero-badge movie-hero-video-badge">VIDEO</span>}
            {hasMovieAudio && <span className="movie-hero-badge movie-hero-video-badge">CÓ ÂM THANH</span>}
          </div>
          <p className="movie-hero-meta">
            {activeMovie.release_date ? `${activeMovie.release_date.slice(0, 4)} · ` : ""}
            {activeMovie.age_rating || "P"} · {activeMovie.duration_minutes} phút
            {activeMovie.director ? ` · ${activeMovie.director}` : ""}
          </p>
          <div className="movie-hero-actions">
            <Link
              className="movie-hero-cta"
              to={activeMovie.watchable ? `/user/watch/${activeMovie.id}` : `/user/showtimes/${activeMovie.id}`}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" /></svg>
              <span>{activeMovie.watchable ? "Xem ngay" : "Đặt vé ngay"}</span>
            </Link>
            <button
              className={`movie-hero-round-action ${isFavorite ? "selected" : ""}`}
              type="button"
              onClick={toggleFavorite}
              aria-label={isFavorite ? "Bỏ yêu thích" : "Thêm vào yêu thích"}
              aria-pressed={isFavorite}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" /></svg>
            </button>
            <button className="movie-hero-round-action" type="button" onClick={shareMovie} aria-label="Chia sẻ phim">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="m8.7 10.7 6.6-4.4M8.7 13.3l6.6 4.4" /></svg>
            </button>
            <span className="movie-hero-action-divider" aria-hidden="true" />
            <button
              className="movie-hero-sound"
              type="button"
              onClick={toggleMute}
              disabled={!hasMovieMedia}
              aria-label={hasMovieMedia ? (muted ? "Bật tiếng" : "Tắt tiếng") : "Phim chưa có video"}
              title={hasMovieMedia ? (muted ? "Bật tiếng" : "Tắt tiếng") : "Phim chưa có video hoặc âm thanh trailer"}
            >
              {muted ? (
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4zM16 9l5 6m0-6-5 6" /></svg>
              ) : (
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4zM15.5 8.5a5 5 0 0 1 0 7m3-10a9 9 0 0 1 0 13" /></svg>
              )}
            </button>
          </div>
          <div className="movie-hero-description-corner">
            <span className="movie-hero-description-label">NỘI DUNG PHIM</span>
            <p className="movie-hero-description">
              {activeMovie.description || "Khám phá lịch chiếu và chọn chỗ ngồi yêu thích của bạn."}
            </p>
          </div>
          {notice && <span className="movie-hero-notice" role="status">{notice}</span>}
        </div>
      </div>
      {movies.length > 1 && (
        <div className="movie-hero-controls">
          <div className="movie-hero-count"><b>{String(activeIndex + 1).padStart(2, "0")}</b> / {String(movies.length).padStart(2, "0")}</div>
          <div className="movie-hero-thumbnails" aria-label="Chọn phim nổi bật">
            {visibleMovies.map((movie, thumbnailIndex) => {
              const index = thumbnailStartIndex + thumbnailIndex;
              return (
                <button
                  className={`movie-hero-thumb ${index === activeIndex ? "active" : ""}`}
                  key={movie.id}
                  type="button"
                  onClick={() => selectMovie(index)}
                  aria-label={`Hiện phim ${movie.title}`}
                  aria-pressed={index === activeIndex}
                >
                  <PosterPreview movie={movie} className="movie-hero-thumb-image" />
                  <span>{movie.title}</span>
                  {index === activeIndex && (
                    <i
                      className={`movie-hero-thumb-progress ${hasMovieMedia ? "video-progress" : ""}`}
                      style={hasMovieMedia ? { "--video-progress": videoProgress } : undefined}
                      aria-hidden="true"
                    />
                  )}
                </button>
              );
            })}
          </div>
          <div className="movie-hero-arrows">
            <button type="button" onClick={() => move(-1)} aria-label="Phim trước">‹</button>
            <button type="button" onClick={() => move(1)} aria-label="Phim tiếp theo">›</button>
          </div>
        </div>
      )}
    </section>
  );
}
