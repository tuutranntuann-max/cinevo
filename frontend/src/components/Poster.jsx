import { useState } from "react";

// Poster phim: dùng ảnh nếu có, ngược lại vẽ bằng màu + tên phim (không cần file ảnh).
export default function Poster({ movie, className = "" }) {
  const posterUrl = movie.poster_url;
  const [failedPosterUrl, setFailedPosterUrl] = useState("");
  if (posterUrl && failedPosterUrl !== posterUrl) {
    return (
      <img
        className={`poster ${className}`}
        src={posterUrl}
        alt={movie.title}
        onError={() => setFailedPosterUrl(posterUrl)}
      />
    );
  }
  return (
    <div className={`poster poster-fallback ${className}`} style={{ "--poster": movie.poster_color }} aria-label={movie.title}>
      <span>{movie.title}</span>
    </div>
  );
}
