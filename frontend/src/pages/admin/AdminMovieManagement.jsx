import { Fragment, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import Poster from "../../components/Poster";
import { api } from "../../services/api";

const EMPTY_MOVIE = {
  title: "",
  genre: "",
  description: "",
  duration_minutes: "120",
  age_rating: "T13",
  rating: "0",
  director: "",
  cast: "",
  release_date: "",
  status: "coming_soon",
};

export default function AdminMovieManagement() {
  const [movies, setMovies] = useState(null);
  const [form, setForm] = useState(EMPTY_MOVIE);
  const [creating, setCreating] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [error, setError] = useState("");
  const [premiereFilter, setPremiereFilter] = useState("all");
  const [editingMovieId, setEditingMovieId] = useState(null);
  const [movieDraft, setMovieDraft] = useState(null);
  const [savingMovieId, setSavingMovieId] = useState(null);
  const [uploadingId, setUploadingId] = useState(null);
  const [updatingTitleLogoId, setUpdatingTitleLogoId] = useState(null);
  const [searchingPosterId, setSearchingPosterId] = useState(null);
  const [applyingTmdbPosterId, setApplyingTmdbPosterId] = useState(null);
  const [posterCandidatesById, setPosterCandidatesById] = useState({});
  const [posterSearchMessageById, setPosterSearchMessageById] = useState({});
  const [updatingStatusId, setUpdatingStatusId] = useState(null);
  const [deletingMovieId, setDeletingMovieId] = useState(null);
  const [publishingId, setPublishingId] = useState(null);
  const [updatingTrailerId, setUpdatingTrailerId] = useState(null);
  const [updatingAudioId, setUpdatingAudioId] = useState(null);
  const [trailerProgressById, setTrailerProgressById] = useState({});
  const [trailerUploadById, setTrailerUploadById] = useState({});
  const [audioProgressById, setAudioProgressById] = useState({});
  const [audioUploadById, setAudioUploadById] = useState({});
  const [previewById, setPreviewById] = useState({});
  const importForm = useRef(null);
  const previewUrls = useRef({});

  useEffect(() => {
    api.get("/admin/movies").then(setMovies).catch((e) => setError(e.message));
  }, []);

  useEffect(() => () => {
    Object.values(previewUrls.current).forEach((url) => URL.revokeObjectURL(url));
  }, []);

  function setMovieField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function startEditingMovie(movie) {
    setEditingMovieId(movie.id);
    setMovieDraft({
      title: movie.title || "",
      genre: movie.genre || "",
      duration_minutes: String(movie.duration_minutes || 120),
      age_rating: movie.age_rating || "T13",
      rating: String(movie.rating ?? 0),
      director: movie.director || "",
      cast: movie.cast || "",
      release_date: movie.release_date || "",
      description: movie.description || "",
      status: movie.status || "coming_soon",
    });
  }

  async function saveMovieDetails(event, movieId) {
    event.preventDefault();
    setSavingMovieId(movieId);
    setError("");
    try {
      await api.patch(`/admin/movies/${movieId}/details`, {
        ...movieDraft,
        duration_minutes: Number(movieDraft.duration_minutes),
        rating: Number(movieDraft.rating),
      });
      setMovies(await api.get("/admin/movies"));
      setEditingMovieId(null);
      setMovieDraft(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingMovieId(null);
    }
  }

  async function createMovie(event) {
    event.preventDefault();
    setCreating(true);
    setError("");
    try {
      const created = await api.post("/admin/movies", {
        ...form,
        duration_minutes: Number(form.duration_minutes),
        rating: Number(form.rating),
      });
      setMovies(await api.get("/admin/movies"));
      setForm(EMPTY_MOVIE);
      window.setTimeout(() => {
        document.getElementById(`admin-movie-${created.id}`)?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }, 0);
    } catch (e) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  }

  async function importMovies(event) {
    event.preventDefault();
    if (!importFile) {
      setError("Vui lòng chọn file Excel .xlsx hoặc CSV.");
      return;
    }
    const formData = new FormData();
    formData.append("file", importFile);
    setImporting(true);
    setError("");
    setImportResult(null);
    try {
      const result = await api.upload("/admin/movies/import", formData);
      setImportResult(result);
      setMovies(await api.get("/admin/movies"));
      setImportFile(null);
      importForm.current?.reset();
    } catch (e) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  }

  function downloadMovieTemplate() {
    const csv = "\uFEFFTên phim,Thể loại,Thời lượng (phút),Phân loại tuổi,Đạo diễn,Mô tả,Ngày khởi chiếu\n";
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "cinevo-movie-import-template.csv";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function publishDraft(movie) {
    setPublishingId(movie.id);
    setError("");
    try {
      await api.patch(`/admin/movies/${movie.id}/status`, { status: "coming_soon" });
      setMovies(await api.get("/admin/movies"));
    } catch (e) {
      setError(e.message);
    } finally {
      setPublishingId(null);
    }
  }

  async function endMoviePremiere(movie) {
    if (!window.confirm(`Kết thúc công chiếu “${movie.title}” ngay bây giờ? Các suất chiếu sẽ không còn hiển thị cho khách và không thể đặt vé mới.`)) {
      return;
    }
    setUpdatingStatusId(movie.id);
    setError("");
    try {
      await api.patch(`/admin/movies/${movie.id}/status`, { status: "ended" });
      setMovies(await api.get("/admin/movies"));
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingStatusId(null);
    }
  }

  async function setCancelled(movie) {
    setUpdatingStatusId(movie.id);
    setError("");
    try {
      await api.patch(`/admin/movies/${movie.id}/cancellation`, { cancelled: !movie.cancelled });
      setMovies(await api.get("/admin/movies"));
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingStatusId(null);
    }
  }

  async function deleteMovie(movie) {
    const ticketCount = movie.cancelled_booking_count || 0;
    const confirmation = ticketCount
      ? `Xóa phim “${movie.title}”, ${ticketCount} vé đã hủy, các suất chiếu và thanh toán liên quan? Dữ liệu đã xóa không thể khôi phục.`
      : `Xóa phim “${movie.title}” và các suất chiếu liên quan? Dữ liệu đã xóa không thể khôi phục.`;
    if (!window.confirm(confirmation)) return;

    setDeletingMovieId(movie.id);
    setError("");
    try {
      await api.delete(`/admin/movies/${movie.id}`);
      setMovies((current) => current.filter((item) => item.id !== movie.id));
    } catch (e) {
      setError(e.message);
    } finally {
      setDeletingMovieId(null);
    }
  }

  async function uploadPoster(movieId, file) {
    if (!file) return;
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!["jpg", "jpeg", "jfif", "png", "webp"].includes(extension)) {
      setError("Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Ảnh poster không được vượt quá 5 MB.");
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    if (previewUrls.current[movieId]) URL.revokeObjectURL(previewUrls.current[movieId]);
    previewUrls.current[movieId] = previewUrl;
    setPreviewById((current) => {
      return { ...current, [movieId]: previewUrl };
    });
    setUploadingId(movieId);
    setError("");
    const formData = new FormData();
    formData.append("poster", file);
    try {
      const updatedMovie = await api.upload(`/admin/movies/${movieId}/poster`, formData);
      setMovies((current) => current.map((movie) => movie.id === movieId ? updatedMovie : movie));
      setPreviewById((current) => {
        URL.revokeObjectURL(previewUrls.current[movieId]);
        delete previewUrls.current[movieId];
        const next = { ...current };
        delete next[movieId];
        return next;
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setUploadingId(null);
    }
  }

  async function uploadTitleLogo(movieId, file) {
    if (!file) return;
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(extension)) {
      setError("Logo tên phim chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Ảnh logo tên phim không được vượt quá 5 MB.");
      return;
    }
    const formData = new FormData();
    formData.append("logo", file);
    setUpdatingTitleLogoId(movieId);
    setError("");
    try {
      const updatedMovie = await api.upload(`/admin/movies/${movieId}/title-logo`, formData);
      setMovies((current) => current.map((movie) => movie.id === movieId ? updatedMovie : movie));
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingTitleLogoId(null);
    }
  }

  async function toggleTitleLogo(movie) {
    setUpdatingTitleLogoId(movie.id);
    setError("");
    try {
      const updatedMovie = await api.patch(`/admin/movies/${movie.id}/title-logo`, {
        enabled: !movie.title_logo_enabled,
      });
      setMovies((current) => current.map((item) => item.id === movie.id ? updatedMovie : item));
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingTitleLogoId(null);
    }
  }

  async function removeTitleLogo(movie) {
    setUpdatingTitleLogoId(movie.id);
    setError("");
    try {
      const updatedMovie = await api.delete(`/admin/movies/${movie.id}/title-logo`);
      setMovies((current) => current.map((item) => item.id === movie.id ? updatedMovie : item));
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingTitleLogoId(null);
    }
  }

  async function searchTmdbPoster(movie) {
    setSearchingPosterId(movie.id);
    setError("");
    setPosterSearchMessageById((current) => ({ ...current, [movie.id]: "" }));
    setPosterCandidatesById((current) => ({ ...current, [movie.id]: [] }));
    try {
      const result = await api.post(`/admin/movies/${movie.id}/poster/search`, {});
      if (result.auto_applied) {
        setMovies((current) => current.map((item) => item.id === movie.id ? result.movie : item));
        setPosterSearchMessageById((current) => ({
          ...current,
          [movie.id]: `Đã tự tìm và tải poster khớp chính xác: ${result.matched_title}.`,
        }));
        return;
      }
      setPosterCandidatesById((current) => ({ ...current, [movie.id]: result.candidates || [] }));
      setPosterSearchMessageById((current) => ({ ...current, [movie.id]: result.message }));
    } catch (e) {
      setError(e.message);
    } finally {
      setSearchingPosterId(null);
    }
  }

  async function applyTmdbPoster(movie, candidate) {
    setApplyingTmdbPosterId(movie.id);
    setError("");
    try {
      const updatedMovie = await api.post(`/admin/movies/${movie.id}/poster/tmdb`, {
        poster_path: candidate.poster_path,
      });
      setMovies((current) => current.map((item) => item.id === movie.id ? updatedMovie : item));
      setPosterCandidatesById((current) => ({ ...current, [movie.id]: [] }));
      setPosterSearchMessageById((current) => ({
        ...current,
        [movie.id]: `Đã tải poster “${candidate.title}” từ TMDb.`,
      }));
    } catch (e) {
      setError(e.message);
    } finally {
      setApplyingTmdbPosterId(null);
    }
  }

  async function updateTrailer(movieId, file) {
    if (!file) return;
    const extension = file.name.split(".").pop()?.toLowerCase();
    const acceptedTypes = { mp4: ["video/mp4"], webm: ["video/webm"] };
    if (!acceptedTypes[extension] || (file.type && !acceptedTypes[extension].includes(file.type))) {
      const message = "Video chỉ hỗ trợ MP4 hoặc WebM. Tải MP3 ở phần Âm thanh.";
      setError(message);
      setTrailerUploadById((current) => ({
        ...current,
        [movieId]: { status: "error", progress: 0, fileName: file.name, message },
      }));
      return;
    }
    if (file.size > 10 * 1024 * 1024 * 1024) {
      const message = "Tệp không được vượt quá 10 GB.";
      setError(message);
      setTrailerUploadById((current) => ({
        ...current,
        [movieId]: { status: "error", progress: 0, fileName: file.name, message },
      }));
      return;
    }
    setUpdatingTrailerId(movieId);
    setError("");
    setTrailerUploadById((current) => ({
      ...current,
      [movieId]: { status: "uploading", progress: 0, fileName: file.name, message: "" },
    }));
    const formData = new FormData();
    formData.append("trailer", file);
    setTrailerProgressById((current) => ({ ...current, [movieId]: 0 }));
    try {
      const updatedMovie = await api.uploadWithProgress(
        `/admin/movies/${movieId}/trailer`,
        formData,
        (progress) => {
          setTrailerProgressById((current) => ({ ...current, [movieId]: progress }));
          setTrailerUploadById((current) => ({
            ...current,
            [movieId]: {
              ...current[movieId],
              status: progress >= 100 ? "processing" : "uploading",
              progress,
            },
          }));
        }
      );
      setMovies((current) => current.map((item) => item.id === movieId ? updatedMovie : item));
      setTrailerUploadById((current) => ({
        ...current,
        [movieId]: {
          ...current[movieId],
          status: "complete",
          progress: 100,
          message: "Video đã tải lên và lưu thành công. Âm thanh MP3 riêng vẫn được giữ lại.",
        },
      }));
    } catch (e) {
      setError(e.message);
      setTrailerUploadById((current) => ({
        ...current,
        [movieId]: {
          ...current[movieId],
          status: "error",
          message: e.message,
        },
      }));
    } finally {
      setUpdatingTrailerId(null);
    }
  }

  async function updateAudio(movieId, file) {
    if (!file) return;
    if (file.name.split(".").pop()?.toLowerCase() !== "mp3"
      || (file.type && !["audio/mpeg", "audio/mp3", "audio/x-mpeg"].includes(file.type))) {
      const message = "Âm thanh trailer chỉ hỗ trợ MP3.";
      setError(message);
      setAudioUploadById((current) => ({
        ...current,
        [movieId]: { status: "error", progress: 0, fileName: file.name, message },
      }));
      return;
    }
    if (file.size > 10 * 1024 * 1024 * 1024) {
      const message = "Tệp âm thanh không được vượt quá 10 GB.";
      setError(message);
      setAudioUploadById((current) => ({
        ...current,
        [movieId]: { status: "error", progress: 0, fileName: file.name, message },
      }));
      return;
    }
    setUpdatingAudioId(movieId);
    setError("");
    setAudioUploadById((current) => ({
      ...current,
      [movieId]: { status: "uploading", progress: 0, fileName: file.name, message: "" },
    }));
    const formData = new FormData();
    formData.append("audio", file);
    try {
      const updatedMovie = await api.uploadWithProgress(
        `/admin/movies/${movieId}/audio`,
        formData,
        (progress) => {
          setAudioProgressById((current) => ({ ...current, [movieId]: progress }));
          setAudioUploadById((current) => ({
            ...current,
            [movieId]: {
              ...current[movieId],
              status: progress >= 100 ? "processing" : "uploading",
              progress,
            },
          }));
        }
      );
      setMovies((current) => current.map((item) => item.id === movieId ? updatedMovie : item));
      setAudioUploadById((current) => ({
        ...current,
        [movieId]: {
          ...current[movieId],
          status: "complete",
          progress: 100,
          message: "Âm thanh MP3 đã tải lên thành công; video hiện có được giữ lại.",
        },
      }));
    } catch (e) {
      setError(e.message);
      setAudioUploadById((current) => ({
        ...current,
        [movieId]: { ...current[movieId], status: "error", message: e.message },
      }));
    } finally {
      setUpdatingAudioId(null);
    }
  }

  async function removeTrailer(movie) {
    setUpdatingTrailerId(movie.id);
    setError("");
    try {
      const updatedMovie = await api.delete(`/admin/movies/${movie.id}/trailer`);
      setMovies((current) => current.map((item) => item.id === movie.id ? updatedMovie : item));
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingTrailerId(null);
    }
  }

  async function removeAudio(movie) {
    setUpdatingAudioId(movie.id);
    setError("");
    try {
      const updatedMovie = await api.delete(`/admin/movies/${movie.id}/audio`);
      setMovies((current) => current.map((item) => item.id === movie.id ? updatedMovie : item));
      setAudioUploadById((current) => {
        const next = { ...current };
        delete next[movie.id];
        return next;
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setUpdatingAudioId(null);
    }
  }

  const visibleMovies = (movies || []).filter((movie) => {
    if (premiereFilter === "all") return true;
    if (premiereFilter === "coming_soon") return movie.status === "coming_soon";
    if (premiereFilter === "now_showing") return movie.status === "now_showing";
    return movie.status === "draft";
  });

  return (
    <section>
      <div className="toolbar">
        <h1 className="page-title">Quản lý vé phim</h1>
        <Link className="btn btn-red" to="/admin/showtimes">Quản lý suất chiếu & vé</Link>
      </div>
      <p className="muted">Thêm phim mới, cập nhật poster và video trailer riêng cho từng phim.</p>
      <p className="hint">Tìm poster TMDb theo tên phim: tên khớp chính xác sẽ tự tải về; kết quả gần giống cần admin chọn. Poster được lưu trên máy chủ.</p>
      <ErrorBox message={error} />
      <form ref={importForm} className="card admin-catalog-form admin-movie-import-form" onSubmit={importMovies}>
        <div className="admin-movie-import-heading">
          <div>
            <h2>Nhập danh sách phim từ Excel</h2>
            <p className="muted">Nhập tối đa 500 phim từ file .xlsx hoặc CSV UTF-8. Phim trùng tên sẽ được bỏ qua.</p>
          </div>
          <button className="btn btn-ghost btn-sm" type="button" onClick={downloadMovieTemplate}>
            Tải file mẫu CSV
          </button>
        </div>
        <label className="admin-movie-import-file">
          Chọn file dữ liệu
          <input
            type="file"
            accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
            disabled={importing}
            onChange={(event) => {
              setImportFile(event.target.files?.[0] || null);
              setImportResult(null);
            }}
          />
        </label>
        {importFile && <p className="hint">Đã chọn: {importFile.name}</p>}
        <div className="actions">
          <button className="btn btn-red" type="submit" disabled={importing || !importFile}>
            {importing ? "Đang nhập phim..." : "Nhập phim vào bản nháp"}
          </button>
        </div>
        <p className="hint">Cột bắt buộc: Tên phim. Các cột tùy chọn: Thể loại, Thời lượng (phút), Phân loại tuổi (P/T13/T16/T18), Đạo diễn, Mô tả, Ngày khởi chiếu (YYYY-MM-DD). Phim nhập mới được lưu dưới dạng bản nháp, chưa hiển thị cho khách; poster, trailer và suất chiếu bổ sung riêng. Bạn vẫn có thể thêm phim thủ công ở phần bên dưới.</p>
        {importResult && <p className="appearance-success" role="status">{importResult.message}</p>}
      </form>
      <form className="card admin-catalog-form admin-movie-create-form" onSubmit={createMovie}>
        <h2>Thêm phim và lịch công chiếu</h2>
        <div className="admin-catalog-fields">
          <label>Tên phim<input name="title" value={form.title} onChange={setMovieField} maxLength="200" required /></label>
          <label>Thể loại<input name="genre" value={form.genre} onChange={setMovieField} maxLength="120" placeholder="Hành động, Tâm lý..." /></label>
          <label>Thời lượng (phút)<input name="duration_minutes" type="number" min="1" max="600" value={form.duration_minutes} onChange={setMovieField} required /></label>
          <label>Phân loại tuổi
            <select name="age_rating" value={form.age_rating} onChange={setMovieField}>
              <option value="P">P</option>
              <option value="T13">T13</option>
              <option value="T16">T16</option>
              <option value="T18">T18</option>
            </select>
          </label>
          <label>Điểm đánh giá (0–10)<input name="rating" type="number" min="0" max="10" value={form.rating} onChange={setMovieField} /></label>
          <label>Đạo diễn / tác giả<input name="director" value={form.director} onChange={setMovieField} maxLength="120" /></label>
          <label>Diễn viên<input name="cast" value={form.cast} onChange={setMovieField} maxLength="500" placeholder="Tên diễn viên, phân cách bằng dấu phẩy" /></label>
          <label>Ngày công chiếu<input name="release_date" type="date" value={form.release_date} onChange={setMovieField} /></label>
          <label>Trạng thái công chiếu
            <select name="status" value={form.status} onChange={setMovieField}>
              <option value="coming_soon">Sắp công chiếu</option>
              <option value="now_showing">Đang công chiếu</option>
            </select>
          </label>
          <label className="admin-catalog-wide">Mô tả
            <textarea name="description" value={form.description} onChange={setMovieField} maxLength="5000" rows="3" />
          </label>
        </div>
        <div className="actions">
          <button className="btn btn-red" type="submit" disabled={creating}>
            {creating ? "Đang thêm phim..." : "Thêm phim vào hệ thống"}
          </button>
        </div>
        <p className="hint">Phim mới sẽ được liên kết với danh sách phim. Sau khi thêm, hãy chọn poster và video ở dòng phim vừa tạo. Phim đang chiếu cần có suất chiếu để khách nhìn thấy.</p>
      </form>
      <div className="admin-premiere-section">
        <h2 className="section-title">Lịch công chiếu và danh sách phim</h2>
        <div className="admin-premiere-filters" role="group" aria-label="Lọc phim theo trạng thái công chiếu">
          {[
            ["all", "Tất cả phim"],
            ["coming_soon", "Sắp công chiếu"],
            ["now_showing", "Đang công chiếu"],
            ["draft", "Bản nháp"],
          ].map(([value, label]) => (
            <button key={value} className={`chip ${premiereFilter === value ? "active" : ""}`}
              type="button" aria-pressed={premiereFilter === value}
              onClick={() => setPremiereFilter(value)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      {movies === null ? <Loading /> : visibleMovies.length === 0 ? <div className="state-box">Không có phim trong nhóm công chiếu này.</div> : (
        <div className="table-wrap">
          <table className="admin-movies-table">
            <thead><tr><th>Ảnh</th><th>ID</th><th>Tên phim</th><th>Thể loại</th><th>Điểm</th><th>Ngày công chiếu</th><th>Trạng thái</th><th>Poster &amp; logo tên phim</th><th>Video / âm thanh banner</th><th>Thao tác</th></tr></thead>
            <tbody>{visibleMovies.map((movie) => (
              <Fragment key={movie.id}>
              <tr id={`admin-movie-${movie.id}`}>
              <td>
                <Poster
                  movie={{ ...movie, poster_url: previewById[movie.id] || movie.poster_url }}
                  className="admin-movie-poster"
                />
              </td>
              <td>{movie.id}</td><td>{movie.title}</td><td>{movie.genre}</td><td>{movie.rating}</td><td>{movie.release_date || "—"}</td>
              <td>
                <span className={`movie-status ${movie.cancelled ? "cancelled" : movie.status === "ended" ? "ended" : movie.expired ? "expired" : movie.status === "draft" ? "draft" : ""}`}>
                  {movie.display_status}
                </span>
                {movie.status === "now_showing" && !movie.cancelled && !movie.has_future_showtime && (
                  <Link className="btn btn-ghost btn-sm admin-poster-search" to={`/admin/showtimes?movie_id=${movie.id}`}>
                    Tạo lịch chiếu
                  </Link>
                )}
              </td>
              <td>
                <label className="btn btn-ghost btn-sm admin-poster-upload">
                  {uploadingId === movie.id ? "Đang cập nhật..." : "Chọn ảnh"}
                  <input type="file" accept=".jpg,.jpeg,.jfif,.png,.webp,image/jpeg,image/png,image/webp" disabled={uploadingId !== null}
                    onChange={(event) => {
                      uploadPoster(movie.id, event.target.files?.[0]);
                      event.target.value = "";
                    }} />
                </label>
                <small className="muted admin-poster-hint">JPG, JFIF, PNG, WEBP · tối đa 5 MB</small>
                <div className="admin-title-logo-controls">
                  <strong>Logo tiêu đề</strong>
                  {movie.title_logo_url && (
                    <img className="admin-title-logo-preview" src={movie.title_logo_url} alt={`Logo tiêu đề ${movie.title}`} />
                  )}
                  <label className="btn btn-ghost btn-sm admin-poster-upload">
                    {updatingTitleLogoId === movie.id ? "Đang cập nhật..." : movie.title_logo_url ? "Đổi logo phim" : "Thêm logo phim"}
                    <input type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" disabled={updatingTitleLogoId !== null}
                      onChange={(event) => {
                        uploadTitleLogo(movie.id, event.target.files?.[0]);
                        event.target.value = "";
                      }} />
                  </label>
                  <small className="muted admin-poster-hint">
                    {movie.title_logo_enabled ? "Đang hiển thị logo thay tên chữ." : "Đang hiển thị tên chữ."}
                  </small>
                  {movie.title_logo_url && (
                    <>
                      <button className="btn btn-ghost btn-sm" type="button" disabled={updatingTitleLogoId !== null}
                        onClick={() => toggleTitleLogo(movie)}>
                        {movie.title_logo_enabled ? "Dùng tên chữ" : "Dùng logo"}
                      </button>
                      <button className="btn btn-ghost btn-sm" type="button" disabled={updatingTitleLogoId !== null}
                        onClick={() => removeTitleLogo(movie)}>
                        Xóa logo
                      </button>
                    </>
                  )}
                </div>
                <button className="btn btn-ghost btn-sm admin-poster-search" type="button"
                  disabled={searchingPosterId !== null || applyingTmdbPosterId !== null}
                  onClick={() => searchTmdbPoster(movie)}>
                  {searchingPosterId === movie.id ? "Đang tìm..." : "Tìm poster TMDb"}
                </button>
                {posterSearchMessageById[movie.id] && (
                  <small className="admin-poster-search-message" role="status">
                    {posterSearchMessageById[movie.id]}
                  </small>
                )}
                {posterCandidatesById[movie.id]?.length > 0 && (
                  <div className="admin-poster-candidates" aria-label={`Chọn poster TMDb cho ${movie.title}`}>
                    {posterCandidatesById[movie.id].map((candidate) => (
                      <button className="admin-poster-candidate" key={candidate.id}
                        type="button" disabled={applyingTmdbPosterId === movie.id}
                        onClick={() => applyTmdbPoster(movie, candidate)}
                        title={`Dùng poster: ${candidate.title}${candidate.release_date ? ` (${candidate.release_date.slice(0, 4)})` : ""}`}>
                        <img src={candidate.preview_url} alt={`Poster ${candidate.title}`} loading="lazy" />
                        <span>{candidate.title}{candidate.release_date ? ` · ${candidate.release_date.slice(0, 4)}` : ""}</span>
                        {applyingTmdbPosterId === movie.id && <span>Đang tải poster...</span>}
                      </button>
                    ))}
                  </div>
                )}
              </td>
              <td className="admin-trailer-cell">
                <div className="admin-trailer-upload-group">
                  <strong>Video</strong>
                  {movie.trailer_url && !movie.trailer_url.includes("format=mp3") && (
                    <video className="admin-trailer-preview" src={movie.trailer_url} controls preload="metadata" aria-label={`Video trailer ${movie.title}`} />
                  )}
                  <label className="btn btn-ghost btn-sm admin-poster-upload">
                    {updatingTrailerId === movie.id ? "Đang tải video..." : movie.trailer_url && !movie.trailer_url.includes("format=mp3") ? "Đổi video MP4/WebM" : "Chọn video MP4/WebM"}
                    <input type="file" accept="video/mp4,video/webm,.mp4,.webm" disabled={updatingTrailerId !== null || updatingAudioId !== null}
                      onChange={(event) => {
                        updateTrailer(movie.id, event.target.files?.[0]);
                        event.target.value = "";
                      }} />
                  </label>
                  {movie.trailer_url && !movie.trailer_url.includes("format=mp3") && (
                    <button className="btn btn-ghost btn-sm" type="button" disabled={updatingTrailerId !== null || updatingAudioId !== null}
                      onClick={() => removeTrailer(movie)}>Xóa video</button>
                  )}
                  {trailerUploadById[movie.id] && (
                    <div className={`admin-upload-progress ${trailerUploadById[movie.id].status}`} role="status" aria-live="polite">
                      <div className="admin-upload-progress-label">
                        <span>
                          {trailerUploadById[movie.id].status === "uploading" && "Đang tải video"}
                          {trailerUploadById[movie.id].status === "processing" && "Máy chủ đang lưu video"}
                          {trailerUploadById[movie.id].status === "complete" && "Video tải lên hoàn tất"}
                          {trailerUploadById[movie.id].status === "error" && "Tải video thất bại"}
                        </span>
                        {trailerUploadById[movie.id].status !== "error" && <span>{trailerProgressById[movie.id] ?? 0}%</span>}
                      </div>
                      <span className="admin-upload-progress-filename">{trailerUploadById[movie.id].fileName}</span>
                      {trailerUploadById[movie.id].status !== "error" && <progress className="admin-upload-progress-bar" max="100" value={trailerProgressById[movie.id] ?? 0} />}
                      {trailerUploadById[movie.id].message && <span className="admin-upload-progress-message">{trailerUploadById[movie.id].message}</span>}
                    </div>
                  )}
                  <small className="muted admin-poster-hint">MP4 / WebM · tối đa 10 GB · hỗ trợ 4K</small>
                </div>
                <div className="admin-trailer-upload-group">
                  <strong>Âm thanh bổ sung</strong>
                  {movie.audio_url && (
                    <audio className="admin-trailer-audio-preview" src={movie.audio_url} controls preload="metadata" aria-label={`Âm thanh trailer ${movie.title}`} />
                  )}
                  <label className="btn btn-ghost btn-sm admin-poster-upload">
                    {updatingAudioId === movie.id ? "Đang tải MP3..." : movie.audio_url ? "Đổi âm thanh MP3" : "Chọn âm thanh MP3"}
                    <input type="file" accept="audio/mpeg,audio/mp3,.mp3" disabled={updatingTrailerId !== null || updatingAudioId !== null}
                    onChange={(event) => {
                      updateAudio(movie.id, event.target.files?.[0]);
                      event.target.value = "";
                    }} />
                  </label>
                  {movie.audio_url && <button className="btn btn-ghost btn-sm" type="button" disabled={updatingTrailerId !== null || updatingAudioId !== null} onClick={() => removeAudio(movie)}>Xóa MP3</button>}
                  {audioUploadById[movie.id] && (
                    <div className={`admin-upload-progress ${audioUploadById[movie.id].status}`} role="status" aria-live="polite">
                      <div className="admin-upload-progress-label">
                        <span>
                          {audioUploadById[movie.id].status === "uploading" && "Đang tải MP3"}
                          {audioUploadById[movie.id].status === "processing" && "Máy chủ đang lưu MP3"}
                          {audioUploadById[movie.id].status === "complete" && "MP3 tải lên hoàn tất"}
                          {audioUploadById[movie.id].status === "error" && "Tải MP3 thất bại"}
                        </span>
                        {audioUploadById[movie.id].status !== "error" && <span>{audioProgressById[movie.id] ?? 0}%</span>}
                      </div>
                      <span className="admin-upload-progress-filename">{audioUploadById[movie.id].fileName}</span>
                      {audioUploadById[movie.id].status !== "error" && <progress className="admin-upload-progress-bar" max="100" value={audioProgressById[movie.id] ?? 0} />}
                      {audioUploadById[movie.id].message && <span className="admin-upload-progress-message">{audioUploadById[movie.id].message}</span>}
                    </div>
                  )}
                  <small className="muted admin-poster-hint">MP3 · tối đa 10 GB · được giữ riêng cùng video</small>
                </div>
              </td>
              <td>
                <button className="btn btn-ghost btn-sm" type="button"
                  disabled={savingMovieId !== null}
                  onClick={() => editingMovieId === movie.id
                    ? setEditingMovieId(null)
                    : startEditingMovie(movie)}>
                  {editingMovieId === movie.id ? "Đóng sửa" : "Sửa thông tin"}
                </button>
                {movie.status === "now_showing" && !movie.cancelled && (
                  <button className="btn btn-outline btn-sm" type="button"
                    disabled={updatingStatusId !== null || publishingId !== null || deletingMovieId !== null}
                    onClick={() => endMoviePremiere(movie)}>
                    {updatingStatusId === movie.id ? "Đang kết thúc..." : "Kết thúc công chiếu"}
                  </button>
                )}
                {movie.status === "draft" && !movie.cancelled ? (
                  <button className="btn btn-red btn-sm" type="button"
                    disabled={publishingId !== null || updatingStatusId !== null || deletingMovieId !== null}
                    onClick={() => publishDraft(movie)}>
                    {publishingId === movie.id ? "Đang công bố..." : "Công bố sắp chiếu"}
                  </button>
                ) : (
                  <button className={`btn ${movie.cancelled ? "btn-ghost" : "btn-outline"} btn-sm`} type="button"
                    disabled={updatingStatusId !== null || publishingId !== null || deletingMovieId !== null || (movie.expired && !movie.cancelled)}
                    title={movie.expired ? "Phim đã hết hạn, tự ẩn khỏi khách hàng" : ""}
                    onClick={() => setCancelled(movie)}>
                    {updatingStatusId === movie.id ? "Đang cập nhật..." : movie.cancelled ? "Khôi phục" : "Hủy phim"}
                  </button>
                )}
                <button className="btn btn-outline btn-sm" type="button"
                  disabled={!movie.delete_allowed || deletingMovieId !== null || updatingStatusId !== null || publishingId !== null}
                  title={movie.delete_allowed
                    ? "Xóa phim cùng các vé đã hủy và suất chiếu liên quan"
                    : "Hãy hủy phim hoặc hủy toàn bộ vé liên quan trước; vé chưa hủy sẽ chặn xóa"}
                  onClick={() => deleteMovie(movie)}>
                  {deletingMovieId === movie.id ? "Đang xóa..." : "Xóa phim & vé đã hủy"}
                </button>
                {movie.booking_count > movie.cancelled_booking_count ? (
                  <small className="muted admin-poster-hint">
                    Hủy {movie.booking_count - movie.cancelled_booking_count} vé còn lại trước khi xóa
                  </small>
                ) : !movie.cancelled && movie.cancelled_booking_count === 0 ? (
                  <small className="muted admin-poster-hint">Hủy phim trước khi xóa</small>
                ) : null}
              </td>
              </tr>
              {editingMovieId === movie.id && movieDraft && (
                <tr>
                  <td colSpan="10">
                    <form className="admin-catalog-fields admin-movie-edit-form"
                      onSubmit={(event) => saveMovieDetails(event, movie.id)}>
                      <h3 className="admin-catalog-wide">Sửa thông tin và công chiếu — {movie.title}</h3>
                      <label>Tên phim<input value={movieDraft.title} onChange={(event) => setMovieDraft({ ...movieDraft, title: event.target.value })} maxLength="200" required /></label>
                      <label>Thể loại<input value={movieDraft.genre} onChange={(event) => setMovieDraft({ ...movieDraft, genre: event.target.value })} maxLength="120" /></label>
                      <label>Thời lượng (phút)<input type="number" min="1" max="600" value={movieDraft.duration_minutes} onChange={(event) => setMovieDraft({ ...movieDraft, duration_minutes: event.target.value })} required /></label>
                      <label>Độ tuổi
                        <select value={movieDraft.age_rating} onChange={(event) => setMovieDraft({ ...movieDraft, age_rating: event.target.value })}>
                          <option value="P">P</option><option value="T13">T13</option><option value="T16">T16</option><option value="T18">T18</option>
                        </select>
                      </label>
                      <label>Điểm đánh giá<input type="number" min="0" max="10" step="0.1" value={movieDraft.rating} onChange={(event) => setMovieDraft({ ...movieDraft, rating: event.target.value })} /></label>
                      <label>Đạo diễn / tác giả<input value={movieDraft.director} onChange={(event) => setMovieDraft({ ...movieDraft, director: event.target.value })} maxLength="120" /></label>
                      <label>Diễn viên<input value={movieDraft.cast} onChange={(event) => setMovieDraft({ ...movieDraft, cast: event.target.value })} maxLength="500" placeholder="Tên diễn viên, phân cách bằng dấu phẩy" /></label>
                      <label>Ngày công chiếu<input type="date" value={movieDraft.release_date} onChange={(event) => setMovieDraft({ ...movieDraft, release_date: event.target.value })} /></label>
                      <label>Trạng thái công chiếu
                        <select value={movieDraft.status} onChange={(event) => setMovieDraft({ ...movieDraft, status: event.target.value })}>
                          <option value="draft">Bản nháp</option>
                          <option value="coming_soon">Sắp công chiếu</option>
                          <option value="now_showing">Đang công chiếu</option>
                          <option value="ended" disabled>Đã kết thúc công chiếu</option>
                        </select>
                      </label>
                      <label className="admin-catalog-wide">Mô tả phim
                        <textarea value={movieDraft.description} onChange={(event) => setMovieDraft({ ...movieDraft, description: event.target.value })} maxLength="5000" rows="4" />
                      </label>
                      <div className="actions admin-catalog-wide">
                        <button className="btn btn-red btn-sm" disabled={savingMovieId === movie.id}>
                          {savingMovieId === movie.id ? "Đang lưu..." : "Lưu thông tin phim"}
                        </button>
                        <button className="btn btn-ghost btn-sm" type="button" onClick={() => setEditingMovieId(null)}>Hủy</button>
                      </div>
                    </form>
                  </td>
                </tr>
              )}
              </Fragment>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
