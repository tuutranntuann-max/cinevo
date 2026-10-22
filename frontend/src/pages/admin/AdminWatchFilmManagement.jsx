import { useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import Poster from "../../components/Poster";
import { api } from "../../services/api";

export default function AdminWatchFilmManagement() {
  const [movies, setMovies] = useState(null);
  const [error, setError] = useState("");
  const [uploadingId, setUploadingId] = useState(null);
  const [savingDetailsId, setSavingDetailsId] = useState(null);
  const [updatingStatusId, setUpdatingStatusId] = useState(null);
  const [deletingMovieId, setDeletingMovieId] = useState(null);
  const [progress, setProgress] = useState({});
  const [subtitleFields, setSubtitleFields] = useState({});

  async function loadMovies() {
    setMovies(await api.get("/admin/movies"));
  }

  useEffect(() => {
    loadMovies().catch((e) => setError(e.message));
  }, []);

  async function uploadFilm(movieId, file) {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024 * 1024) {
      setError("Tệp phim không được vượt quá 10 GB.");
      return;
    }
    const formData = new FormData();
    formData.append("film", file);
    setError("");
    setUploadingId(movieId);
    setProgress((current) => ({ ...current, [movieId]: 0 }));
    try {
      await api.uploadWithProgress(`/admin/movies/${movieId}/film`, formData, (value) => {
        setProgress((current) => ({ ...current, [movieId]: value }));
      });
      await loadMovies();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploadingId(null);
      setProgress((current) => {
        const next = { ...current };
        delete next[movieId];
        return next;
      });
    }
  }

  async function uploadFilmImage(movieId, file) {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError("Ảnh phim không được vượt quá 5 MB.");
      return;
    }
    const formData = new FormData();
    formData.append("image", file);
    setError("");
    setUploadingId(movieId);
    try {
      await api.upload(`/admin/movies/${movieId}/film-image`, formData);
      await loadMovies();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploadingId(null);
    }
  }

  function updateSubtitleField(movieId, field, value) {
    setSubtitleFields((current) => ({
      ...current,
      [movieId]: { label: "", language: "vi", url: "", ...current[movieId], [field]: value },
    }));
  }

  async function uploadSubtitle(movieId, file) {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError("Tệp phụ đề không được vượt quá 5 MB.");
      return;
    }
    const fields = subtitleFields[movieId] || {};
    const formData = new FormData();
    formData.append("subtitle", file);
    formData.append("language", fields.language || "vi");
    formData.append("label", fields.label || fields.language || "vi");
    setError("");
    setUploadingId(movieId);
    try {
      await api.upload(`/admin/movies/${movieId}/subtitles`, formData);
      await loadMovies();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploadingId(null);
    }
  }

  async function addSubtitleUrl(movieId) {
    const fields = subtitleFields[movieId] || {};
    setError("");
    setUploadingId(movieId);
    try {
      await api.post(`/admin/movies/${movieId}/subtitles/url`, {
        url: fields.url,
        language: fields.language || "vi",
        label: fields.label || fields.language || "vi",
      });
      updateSubtitleField(movieId, "url", "");
      await loadMovies();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploadingId(null);
    }
  }

  async function removeSubtitle(movieId, subtitleId) {
    setError("");
    setUploadingId(movieId);
    try {
      await api.delete(`/admin/movies/${movieId}/subtitles/${subtitleId}`);
      await loadMovies();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploadingId(null);
    }
  }

  async function removeFilm(movie) {
    if (!window.confirm(`Gỡ bản xem trực tuyến của phim “${movie.title}”?`)) return;
    setError("");
    setUploadingId(movie.id);
    try {
      await api.delete(`/admin/movies/${movie.id}/film`);
      await loadMovies();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploadingId(null);
    }
  }

  async function toggleMovieCancellation(movie) {
    setError("");
    setUpdatingStatusId(movie.id);
    try {
      await api.patch(`/admin/movies/${movie.id}/cancellation`, { cancelled: !movie.cancelled });
      await loadMovies();
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingStatusId(null);
    }
  }

  async function deleteMovie(movie) {
    const cancelledBookingCount = movie.cancelled_booking_count || 0;
    const confirmation = cancelledBookingCount
      ? `Xóa phim “${movie.title}”, ${cancelledBookingCount} vé đã hủy, các suất chiếu và thanh toán liên quan? Dữ liệu đã xóa không thể khôi phục.`
      : `Xóa phim “${movie.title}” và các suất chiếu liên quan? Dữ liệu đã xóa không thể khôi phục.`;
    if (!window.confirm(confirmation)) return;

    setError("");
    setDeletingMovieId(movie.id);
    try {
      await api.delete(`/admin/movies/${movie.id}`);
      setMovies((current) => current.filter((item) => item.id !== movie.id));
    } catch (e) {
      setError(e.message);
    } finally {
      setDeletingMovieId(null);
    }
  }

  function updateMovieField(movieId, field, value) {
    setMovies((current) => current.map((movie) =>
      movie.id === movieId ? { ...movie, [field]: value } : movie));
  }

  async function saveWatchDetails(event, movie) {
    event.preventDefault();
    setError("");
    setSavingDetailsId(movie.id);
    try {
      await api.patch(`/admin/movies/${movie.id}/watch-details`, {
        description: movie.description || "",
        director: movie.director || "",
        release_date: movie.release_date || "",
        theatrical_end_date: movie.theatrical_end_date || "",
        duration_minutes: Number(movie.duration_minutes),
      });
      await loadMovies();
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingDetailsId(null);
    }
  }

  return (
    <section>
      <div className="toolbar">
        <div>
          <h1 className="page-title">Quản lý phim xem trực tuyến</h1>
          <p className="muted">Chỉ đăng tải phim do bạn sở hữu hoặc được cấp quyền phát trực tuyến.</p>
        </div>
      </div>
      <ErrorBox message={error} />
      {movies === null ? <Loading /> : (
        <div className="table-wrap">
          <table className="admin-watch-film-table">
            <thead><tr><th>Phim</th><th>Thông tin phim</th><th>Phát trực tuyến</th></tr></thead>
            <tbody>{movies.map((movie) => (
              <tr key={movie.id}>
                <td className="admin-watch-title-cell">
                  <strong>{movie.title}</strong>
                  <small className="muted">ID: {movie.id}</small>
                  <span className={`movie-status ${movie.cancelled ? "cancelled" : movie.expired ? "expired" : movie.status === "draft" ? "draft" : ""}`}>
                    {movie.display_status}
                  </span>
                </td>
                <td>
                  <div className="admin-watch-metadata-summary">
                    <span>{movie.duration_minutes || "—"} phút</span>
                    {movie.director && <span>{movie.director}</span>}
                  </div>
                  <details className="admin-watch-disclosure">
                    <summary>Sửa thông tin</summary>
                    <form className="admin-watch-metadata" onSubmit={(event) => saveWatchDetails(event, movie)}>
                      <label>Mô tả
                        <textarea value={movie.description || ""} maxLength="5000"
                          onChange={(event) => updateMovieField(movie.id, "description", event.target.value)} />
                      </label>
                      <label>Tác giả / Đạo diễn
                        <input value={movie.director || ""} maxLength="120"
                          onChange={(event) => updateMovieField(movie.id, "director", event.target.value)} />
                      </label>
                      <label>Ngày ra phim
                        <input type="date" value={movie.release_date || ""}
                          onChange={(event) => updateMovieField(movie.id, "release_date", event.target.value)} />
                      </label>
                      <label>Ngày kết thúc chiếu rạp
                        <input type="date" value={movie.theatrical_end_date || ""}
                          onChange={(event) => updateMovieField(movie.id, "theatrical_end_date", event.target.value)} />
                      </label>
                      <label>Thời lượng (phút)
                        <input type="number" min="1" max="600" required value={movie.duration_minutes || ""}
                          onChange={(event) => updateMovieField(movie.id, "duration_minutes", event.target.value)} />
                      </label>
                      <button className="btn btn-ghost btn-sm" type="submit" disabled={savingDetailsId !== null}>
                        {savingDetailsId === movie.id ? "Đang lưu..." : "Lưu thông tin"}
                      </button>
                    </form>
                  </details>
                </td>
                <td className="admin-watch-assets-cell">
                  <div className="admin-watch-status-line">
                    <span className={`movie-status ${movie.watch_ready ? "" : "expired"}`}>
                      {movie.watch_ready ? "Sẵn sàng" : movie.film_url ? "Chờ hết lịch chiếu" : "Chưa có phim"}
                    </span>
                    <div className="admin-watch-actions">
                      <label className="btn btn-ghost btn-sm admin-poster-upload">
                        {uploadingId === movie.id ? `Đang tải ${progress[movie.id] ?? 0}%` : movie.film_url ? "Thay phim" : "Tải phim lên"}
                        <input type="file" accept="video/mp4,video/webm,.mp4,.webm" disabled={uploadingId !== null}
                          onChange={(event) => {
                            uploadFilm(movie.id, event.target.files?.[0]);
                            event.target.value = "";
                          }} />
                      </label>
                      {movie.film_url && (
                        <button className="btn btn-ghost btn-sm" type="button" disabled={uploadingId !== null}
                          onClick={() => removeFilm(movie)}>Xóa bản phim trực tuyến</button>
                      )}
                    </div>
                  </div>
                  <div className="admin-film-artwork">
                    {movie.film_image_url && (
                      <Poster
                        movie={{ ...movie, poster_url: movie.film_image_url }}
                        className="admin-film-image-preview"
                      />
                    )}
                    {movie.film_url && <label className="btn btn-ghost btn-sm admin-poster-upload">
                      {uploadingId === movie.id ? "Đang cập nhật..." : movie.film_image_url ? "Đổi ảnh phim" : "Thêm ảnh phim"}
                      <input type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
                        disabled={uploadingId !== null}
                        onChange={(event) => {
                          uploadFilmImage(movie.id, event.target.files?.[0]);
                          event.target.value = "";
                        }} />
                    </label>}
                  </div>
                  <section className="admin-subtitles" aria-label={`Phụ đề phim ${movie.title}`}>
                    <strong>Phụ đề riêng cho phim</strong>
                    <div className="admin-subtitle-fields">
                      <label>Tên hiển thị
                        <input value={subtitleFields[movie.id]?.label || ""}
                          onChange={(event) => updateSubtitleField(movie.id, "label", event.target.value)}
                          maxLength="80" placeholder="Ví dụ: Tiếng Việt" />
                      </label>
                      <label>Mã ngôn ngữ
                        <input value={subtitleFields[movie.id]?.language || "vi"}
                          onChange={(event) => updateSubtitleField(movie.id, "language", event.target.value)}
                          maxLength="35" placeholder="vi" />
                      </label>
                    </div>
                    <label className="btn btn-ghost btn-sm admin-poster-upload">
                      Tải phụ đề VTT / SRT
                      <input type="file" accept=".vtt,.srt,text/vtt,application/x-subrip"
                        disabled={uploadingId !== null}
                        onChange={(event) => {
                          uploadSubtitle(movie.id, event.target.files?.[0]);
                          event.target.value = "";
                        }} />
                    </label>
                    <form className="admin-subtitle-url" onSubmit={(event) => {
                      event.preventDefault();
                      addSubtitleUrl(movie.id);
                    }}>
                      <label>Hoặc URL phụ đề VTT (HTTPS)
                        <input type="url" value={subtitleFields[movie.id]?.url || ""}
                          onChange={(event) => updateSubtitleField(movie.id, "url", event.target.value)}
                          placeholder="https://example.com/subtitle.vtt" required />
                      </label>
                      <button className="btn btn-ghost btn-sm" type="submit" disabled={uploadingId !== null}>
                        Thêm URL
                      </button>
                    </form>
                    {movie.subtitle_tracks?.length > 0 && (
                      <ul className="admin-subtitle-list">
                        {movie.subtitle_tracks.map((subtitle) => (
                          <li key={subtitle.id}>
                            <span>{subtitle.label} · {subtitle.language} · {subtitle.format === "url" ? "URL" : subtitle.format.toUpperCase()}</span>
                            <button className="btn btn-outline btn-sm" type="button"
                              disabled={uploadingId !== null}
                              onClick={() => removeSubtitle(movie.id, subtitle.id)}>Xóa</button>
                          </li>
                        ))}
                      </ul>
                    )}
                    <small className="muted">URL ngoài phải truy cập công khai, dùng HTTPS, trả về WebVTT và cho phép CORS từ website.</small>
                  </section>
                  {movie.film_url && <details className="admin-watch-disclosure admin-watch-preview-disclosure">
                    <summary>{movie.watch_ready ? "Xem trước phim" : "Điều kiện phát phim"}</summary>
                    {movie.watch_ready
                      ? <video className="admin-film-preview" src={movie.film_url}
                        controls preload="metadata" aria-label={`Xem trước ${movie.title}`} />
                      : <small className="muted">Phim sẽ phát trên trang khách sau khi hết lịch chiếu và đáp ứng điều kiện công bố.</small>}
                  </details>}
                  <div className="admin-watch-actions admin-watch-movie-actions">
                    <button className={`btn ${movie.cancelled ? "btn-ghost" : "btn-outline"} btn-sm`}
                      type="button"
                      disabled={updatingStatusId !== null || deletingMovieId !== null}
                      onClick={() => toggleMovieCancellation(movie)}>
                      {updatingStatusId === movie.id
                        ? "Đang cập nhật..."
                        : movie.cancelled ? "Khôi phục phim" : "Hủy phim"}
                    </button>
                    <button className="btn btn-outline btn-sm" type="button"
                      disabled={!movie.delete_allowed || deletingMovieId !== null || updatingStatusId !== null}
                      title={movie.delete_allowed
                        ? "Xóa phim cùng các vé đã hủy và suất chiếu liên quan"
                        : "Hãy hủy phim hoặc hủy toàn bộ vé liên quan trước; vé chưa hủy sẽ chặn xóa"}
                      onClick={() => deleteMovie(movie)}>
                      {deletingMovieId === movie.id ? "Đang xóa..." : "Xóa phim & vé đã hủy"}
                    </button>
                  </div>
                  {movie.booking_count > movie.cancelled_booking_count ? (
                    <small className="muted admin-poster-hint">
                      Còn {movie.booking_count - movie.cancelled_booking_count} vé chưa hủy
                    </small>
                  ) : !movie.cancelled && movie.cancelled_booking_count === 0 ? (
                    <small className="muted admin-poster-hint">Hủy phim trước khi xóa</small>
                  ) : null}
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <p className="hint">Video: MP4 hoặc WebM, tối đa 10 GB. Ảnh đại diện: JPG, PNG hoặc WEBP, tối đa 5 MB (tải bản phim lên trước khi thêm ảnh). Phim chỉ xuất hiện cho khách sau khi đã có suất chiếu đã qua, không còn suất chiếu tương lai và chưa bị hủy.</p>
    </section>
  );
}
