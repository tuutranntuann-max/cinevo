import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";
import { formatVND } from "../../utils/format";

function emptyShowtimeForm() {
  const nextSlot = new Date(Math.ceil((Date.now() + 60 * 60 * 1000) / (30 * 60 * 1000)) * 30 * 60 * 1000);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(nextSlot);
  const value = Object.fromEntries(parts.map(({ type, value: part }) => [type, part]));
  return {
    movie_id: "",
    cinema_id: "",
    room_id: "",
    start_time: `${value.year}-${value.month}-${value.day}T${value.hour}:${value.minute}`,
    base_price: "90000",
  };
}

function formatVietnamShowtime(value) {
  const [date, time] = value.split("T");
  return `${date} ${time.slice(0, 5)}`;
}

const NEW_MOVIE = {
  title: "", genre: "", duration_minutes: "120", age_rating: "T13",
  rating: "0", director: "", description: "", release_date: "", status: "coming_soon",
};

export default function AdminShowtimeManagement() {
  const [searchParams] = useSearchParams();
  const [movies, setMovies] = useState([]);
  const [cinemas, setCinemas] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [showtimes, setShowtimes] = useState(null);
  const [form, setForm] = useState(emptyShowtimeForm);
  const [selectedRoomIds, setSelectedRoomIds] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loadingForm, setLoadingForm] = useState(true);
  const [saving, setSaving] = useState(false);
  const [movieForm, setMovieForm] = useState(NEW_MOVIE);
  const [savingMovie, setSavingMovie] = useState(false);

  async function loadShowtimes() {
    setError("");
    try {
      setShowtimes(await api.get("/admin/showtimes"));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    Promise.all([api.get("/admin/movies"), api.get("/admin/cinemas"), api.get("/admin/rooms")])
      .then(([movieRows, cinemaRows, roomRows]) => {
        setMovies(movieRows);
        setCinemas(cinemaRows);
        setRooms(roomRows);
        const activeMovies = movieRows.filter((movie) => !movie.cancelled && movie.status !== "draft");
        const preferredMovie = searchParams.get("movie_id") || "";
        setForm((current) => ({
          ...current,
          movie_id: activeMovies.some((movie) => String(movie.id) === preferredMovie)
            ? preferredMovie
            : String(activeMovies[0]?.id || ""),
          cinema_id: String(cinemaRows[0]?.id || ""),
        }));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoadingForm(false));
    loadShowtimes();
  }, [searchParams]);

  const availableRooms = rooms.filter((room) => String(room.cinema_id) === form.cinema_id);

  function resetForm() {
    setEditingId(null);
    setSelectedRoomIds([]);
    setForm((current) => ({ ...emptyShowtimeForm(), movie_id: current.movie_id, cinema_id: current.cinema_id }));
  }

  function editShowtime(showtime) {
    setEditingId(showtime.id);
    setSelectedRoomIds([String(showtime.room_id)]);
    setForm({
      movie_id: String(showtime.movie_id),
      cinema_id: String(showtime.cinema_id),
      start_time: showtime.start_time.slice(0, 16),
      base_price: String(showtime.base_price),
    });
  }

  function setField(event) {
    const { name, value } = event.target;
    if (name === "cinema_id") {
      if (editingId !== null) {
        const firstRoom = rooms.find((room) => String(room.cinema_id) === value);
        setSelectedRoomIds(firstRoom ? [String(firstRoom.id)] : []);
      } else {
        setSelectedRoomIds([]);
      }
    }
    setForm((current) => ({ ...current, [name]: value }));
  }

  function toggleRoom(roomId) {
    setSelectedRoomIds((current) => current.includes(String(roomId))
      ? current.filter((id) => id !== String(roomId))
      : [...current, String(roomId)]);
  }

  async function addMovie(event) {
    event.preventDefault();
    setSavingMovie(true);
    setError("");
    const payload = {
      ...movieForm,
      duration_minutes: Number(movieForm.duration_minutes),
      rating: Number(movieForm.rating),
      release_date: movieForm.release_date || null,
    };
    try {
      const movie = await api.post("/admin/movies", payload);
      setMovies((current) => [...current, { ...movie, cancelled: false, expired: false }]);
      setForm((current) => ({ ...current, movie_id: String(movie.id) }));
      setMovieForm(NEW_MOVIE);
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingMovie(false);
    }
  }

  async function save(event) {
    event.preventDefault();
    if (form.movie_id === "__new_movie__") return;
    setSaving(true);
    setError("");
    setMessage("");
    const payload = {
      movie_id: Number(form.movie_id),
      cinema_id: Number(form.cinema_id),
      start_time: form.start_time,
      base_price: Number(form.base_price),
    };
    try {
      if (editingId === null) {
        const created = await api.post("/admin/showtimes/bulk", {
          ...payload,
          room_ids: selectedRoomIds.map(Number),
        });
        setMessage(`Đã tạo ${created.length} suất chiếu tại ${created.length} phòng.`);
      } else {
        await api.put(`/admin/showtimes/${editingId}`, {
          ...payload,
          room_id: Number(selectedRoomIds[0]),
        });
        setMessage("Đã cập nhật suất chiếu.");
      }
      resetForm();
      await loadShowtimes();
    } catch (e) {
      setError(e.message);
      setMessage("");
    } finally {
      setSaving(false);
    }
  }

  if (loadingForm) return <Loading />;

  return (
    <section>
      <div className="toolbar">
        <div>
          <h1 className="page-title">Quản lý suất chiếu & vé</h1>
          <p className="muted">Thêm hoặc cập nhật giờ chiếu và giá vé để khách hàng đặt vé.</p>
        </div>
        <Link className="btn btn-ghost" to="/admin/movies">Quay lại quản lý phim</Link>
      </div>
      <ErrorBox message={error} />
      {message && <p className="appearance-success" role="status">{message}</p>}

      <form className="card admin-catalog-form" onSubmit={save}>
        <h2>{editingId === null ? "Thêm suất chiếu mới" : "Cập nhật suất chiếu"}</h2>
        <div className="admin-catalog-fields">
          <label>Phim<select name="movie_id" value={form.movie_id} onChange={setField} required>
            <option value="">Chọn phim</option>
            {movies.filter((movie) => !movie.cancelled).map((movie) => <option key={movie.id} value={movie.id}>{movie.title}</option>)}
            <option value="__new_movie__">＋ Thêm phim mới bằng cách nhập thông tin...</option>
          </select></label>
          <label>Rạp<select name="cinema_id" value={form.cinema_id} onChange={setField} required>
            <option value="">Chọn rạp</option>
            {cinemas.map((cinema) => <option key={cinema.id} value={cinema.id}>{cinema.name} · {cinema.city}</option>)}
          </select></label>
          <label>Ngày và giờ (giờ Việt Nam, UTC+7)<input name="start_time" type="datetime-local" value={form.start_time} onChange={setField} required /></label>
          <label>Giá vé (VND)<input name="base_price" type="number" min="0" max="1000000000" value={form.base_price} onChange={setField} required /></label>
        </div>
        <p className="hint">Giờ mặc định được gợi ý theo giờ Việt Nam, sau thời điểm hiện tại ít nhất 1 giờ. Hãy kiểm tra giờ, rạp và phòng trước khi lưu.</p>
        <fieldset className="admin-showtime-room-picker" disabled={editingId !== null}>
          <legend>Chọn phòng chiếu — có thể tích nhiều phòng</legend>
          {availableRooms.length ? (
            <>
              <div className="admin-showtime-room-actions">
                <button className="btn btn-ghost btn-sm" type="button"
                  onClick={() => setSelectedRoomIds(availableRooms.map((room) => String(room.id)))}>
                  Chọn tất cả
                </button>
                <button className="btn btn-ghost btn-sm" type="button"
                  onClick={() => setSelectedRoomIds([])}>
                  Bỏ chọn
                </button>
              </div>
              <div className="admin-showtime-room-options">
                {availableRooms.map((room) => (
                  <label className="admin-showtime-room-option" key={room.id}>
                    <input
                      type="checkbox"
                      checked={selectedRoomIds.includes(String(room.id))}
                      onChange={() => toggleRoom(room.id)}
                    />
                    <span>{room.name} · {room.room_type}</span>
                  </label>
                ))}
              </div>
            </>
          ) : <p className="muted small">Rạp này chưa có phòng chiếu.</p>}
          {selectedRoomIds.length > 0 && (
            <p className="hint">Đã chọn {selectedRoomIds.length} phòng; mỗi phòng sẽ nhận cùng một lịch chiếu.</p>
          )}
        </fieldset>
        {form.movie_id === "__new_movie__" && <div className="admin-inline-movie">
          <div className="admin-inline-movie-heading">
            <h3>Nhập thông tin phim mới</h3>
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => {
              setForm((current) => ({ ...current, movie_id: String(movies[0]?.id || "") }));
            }}>Đóng</button>
          </div>
          <div className="admin-catalog-fields">
            <label>Tên phim<input required maxLength="200" value={movieForm.title} onChange={(e) => setMovieForm({ ...movieForm, title: e.target.value })} /></label>
            <label>Thể loại<input maxLength="120" value={movieForm.genre} onChange={(e) => setMovieForm({ ...movieForm, genre: e.target.value })} /></label>
            <label>Thời lượng (phút)<input type="number" min="1" max="600" required value={movieForm.duration_minutes} onChange={(e) => setMovieForm({ ...movieForm, duration_minutes: e.target.value })} /></label>
            <label>Phân loại tuổi<select value={movieForm.age_rating} onChange={(e) => setMovieForm({ ...movieForm, age_rating: e.target.value })}>
              {["P", "T13", "T16", "T18"].map((rating) => <option key={rating}>{rating}</option>)}
            </select></label>
            <label>Điểm đánh giá<input type="number" min="0" max="10" value={movieForm.rating} onChange={(e) => setMovieForm({ ...movieForm, rating: e.target.value })} /></label>
            <label>Đạo diễn<input maxLength="120" value={movieForm.director} onChange={(e) => setMovieForm({ ...movieForm, director: e.target.value })} /></label>
            <label>Ngày khởi chiếu<input type="date" value={movieForm.release_date} onChange={(e) => setMovieForm({ ...movieForm, release_date: e.target.value })} /></label>
            <label>Trạng thái<select value={movieForm.status} onChange={(e) => setMovieForm({ ...movieForm, status: e.target.value })}>
              <option value="coming_soon">Sắp chiếu</option>
              <option value="now_showing">Đang chiếu</option>
            </select></label>
            <label className="admin-catalog-wide">Mô tả<input maxLength="5000" value={movieForm.description} onChange={(e) => setMovieForm({ ...movieForm, description: e.target.value })} /></label>
          </div>
          <div className="actions">
            <button className="btn btn-red" type="button" onClick={addMovie} disabled={savingMovie}>
              {savingMovie ? "Đang thêm phim..." : "Lưu phim và chọn phim này"}
            </button>
          </div>
        </div>}
        <div className="actions">
          {editingId !== null && <button className="btn btn-ghost" type="button" onClick={resetForm}>Hủy sửa</button>}
          <button className="btn btn-red" disabled={saving || !movies.length || !availableRooms.length || !selectedRoomIds.length || form.movie_id === "__new_movie__"}>
            {saving ? "Đang lưu..." : editingId === null
              ? `Thêm suất chiếu tại ${selectedRoomIds.length} phòng`
              : "Lưu cập nhật"}
          </button>
        </div>
      </form>

      <h2 className="section-title">Danh sách suất chiếu</h2>
      {showtimes === null ? <Loading /> : showtimes.length === 0 ? <div className="state-box">Chưa có suất chiếu.</div> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Phim</th><th>Rạp</th><th>Phòng</th><th>Ngày giờ</th><th>Giá vé</th><th>Thao tác</th></tr></thead>
            <tbody>{showtimes.map((showtime) => <tr key={showtime.id}>
              <td>{showtime.movie}</td>
              <td>{showtime.cinema}</td>
              <td>{showtime.room}</td>
              <td>{formatVietnamShowtime(showtime.start_time)}</td>
              <td>{formatVND(showtime.base_price)}</td>
              <td><button className="btn btn-ghost btn-sm" disabled={new Date(showtime.start_time) <= new Date()}
                title={new Date(showtime.start_time) <= new Date() ? "Không thể sửa suất chiếu đã qua" : ""}
                onClick={() => editShowtime(showtime)}>Sửa</button></td>
            </tr>)}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
