import { useRef, useState } from "react";
import MovieInfoIcon from "./MovieInfoIcon";
import Poster from "./Poster";

export default function MovieTrailerPlayer({ movie, className = "" }) {
  const videoRef = useRef(null);
  const [failed, setFailed] = useState(false);
  const [playing, setPlaying] = useState(false);
  const videoTrailer = movie.trailer_url && !movie.trailer_url.includes("format=mp3");

  async function playTrailer() {
    try {
      await videoRef.current?.play();
    } catch {
      setFailed(true);
    }
  }

  if (videoTrailer && !failed) {
    return (
      <div className={`movie-trailer-player ${className}`}>
        <video
          ref={videoRef}
          src={movie.trailer_url}
          poster={movie.poster_url || undefined}
          controls
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          aria-label={`Trailer phim ${movie.title}`}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onError={() => setFailed(true)}
        />
        {!playing && (
          <button className="movie-trailer-play" type="button" onClick={playTrailer}>
            <span aria-hidden="true">▶</span> Phát trailer
          </button>
        )}
      </div>
    );
  }

  if (movie.audio_url && !failed) {
    return (
      <div className={`movie-detail-audio ${className}`}>
        <p>Phim có trailer âm thanh</p>
        <audio src={movie.audio_url} controls preload="metadata" onError={() => setFailed(true)} />
      </div>
    );
  }

  return (
    <div className={`movie-trailer-fallback ${className}`}>
      <Poster movie={movie} className="movie-trailer-poster" />
      <span>{failed ? "Chưa phát được trailer. Hãy kiểm tra lại tệp phim." : "Trailer sẽ được cập nhật sớm."}</span>
      {failed && <MovieInfoIcon name="info" />}
    </div>
  );
}
