import { Fragment, useEffect, useRef, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";

const REGIONS = ["Miền Bắc", "Miền Trung", "Miền Nam"];
const EMPTY_CINEMA = {
  chain: "",
  name: "",
  city: "",
  address: "",
  phone: "",
  room_name: "Phòng 01",
  room_type: "2D",
  total_rows: "8",
  total_cols: "10",
};
const EMPTY_ROOM = {
  name: "",
  room_type: "2D",
  total_rows: "8",
  total_cols: "10",
};

export default function CinemaCatalogManagement() {
  const [cinemas, setCinemas] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [provinces, setProvinces] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState("");
  const [selectedProvince, setSelectedProvince] = useState("");
  const [form, setForm] = useState(EMPTY_CINEMA);
  const [importFile, setImportFile] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [expandedCinemaId, setExpandedCinemaId] = useState(null);
  const [editingCinemaId, setEditingCinemaId] = useState(null);
  const [cinemaDraft, setCinemaDraft] = useState(null);
  const [editingRoomId, setEditingRoomId] = useState(null);
  const [roomDraft, setRoomDraft] = useState(EMPTY_ROOM);
  const [newRoomDraft, setNewRoomDraft] = useState(EMPTY_ROOM);
  const [savingCinemaId, setSavingCinemaId] = useState(null);
  const [savingRoomId, setSavingRoomId] = useState(null);
  const [creatingRoom, setCreatingRoom] = useState(false);
  const importForm = useRef(null);

  async function loadData() {
    const [cinemaRows, provinceRows, roomRows] = await Promise.all([
      api.get("/admin/cinemas"),
      api.get("/provinces"),
      api.get("/admin/rooms"),
    ]);
    setCinemas(cinemaRows);
    setProvinces(provinceRows);
    setRooms(roomRows);
  }

  useEffect(() => {
    loadData().catch((e) => setError(e.message));
  }, []);

  const regionOptions = REGIONS.filter((region) =>
    provinces.some((province) => province.region === region));
  const provinceOptions = provinces.filter((province) =>
    !selectedRegion || province.region === selectedRegion);
  const visibleCinemas = (cinemas || []).filter((cinema) =>
    (!selectedRegion || cinema.region === selectedRegion)
    && (!selectedProvince || (cinema.province || cinema.city) === selectedProvince));

  function setField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function createCinema(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.post("/admin/cinemas", {
        ...form,
        total_rows: Number(form.total_rows),
        total_cols: Number(form.total_cols),
      });
      setForm(EMPTY_CINEMA);
      await loadData();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function importCinemas(event) {
    event.preventDefault();
    if (!importFile) {
      setError("Vui lòng chọn file Excel .xlsx hoặc CSV.");
      return;
    }
    const body = new FormData();
    body.append("file", importFile);
    setImporting(true);
    setError("");
    setImportResult(null);
    try {
      const result = await api.upload("/admin/cinemas/import", body);
      setImportResult(result);
      setImportFile(null);
      importForm.current?.reset();
      await loadData();
    } catch (e) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  }

  function beginCinemaEdit(cinema) {
    setEditingCinemaId(cinema.id);
    setCinemaDraft({
      chain: cinema.chain || "",
      name: cinema.name || "",
      city: cinema.province || cinema.city || "",
      address: cinema.address || "",
      phone: cinema.phone || "",
    });
  }

  async function saveCinema(event, cinemaId) {
    event.preventDefault();
    setSavingCinemaId(cinemaId);
    setError("");
    try {
      await api.put(`/admin/cinemas/${cinemaId}`, cinemaDraft);
      setEditingCinemaId(null);
      setCinemaDraft(null);
      await loadData();
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingCinemaId(null);
    }
  }

  function beginRoomEdit(room) {
    setEditingRoomId(room.id);
    setRoomDraft({
      name: room.name,
      room_type: room.room_type,
      total_rows: String(room.total_rows),
      total_cols: String(room.total_cols),
    });
  }

  async function saveRoom(event, roomId) {
    event.preventDefault();
    setSavingRoomId(roomId);
    setError("");
    try {
      await api.put(`/admin/rooms/${roomId}`, {
        ...roomDraft,
        total_rows: Number(roomDraft.total_rows),
        total_cols: Number(roomDraft.total_cols),
      });
      setEditingRoomId(null);
      await loadData();
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingRoomId(null);
    }
  }

  async function addRoom(event, cinemaId) {
    event.preventDefault();
    setCreatingRoom(true);
    setError("");
    try {
      await api.post(`/admin/cinemas/${cinemaId}/rooms`, {
        ...newRoomDraft,
        total_rows: Number(newRoomDraft.total_rows),
        total_cols: Number(newRoomDraft.total_cols),
      });
      setNewRoomDraft(EMPTY_ROOM);
      await loadData();
    } catch (e) {
      setError(e.message);
    } finally {
      setCreatingRoom(false);
    }
  }

  async function deleteRoom(room) {
    const confirmation = room.showtimes_count
      ? "Phòng này đã có suất chiếu nên không thể xóa để bảo toàn vé và lịch sử."
      : `Xóa ${room.name} và toàn bộ ghế của phòng này?`;
    if (room.showtimes_count || !window.confirm(confirmation)) return;
    setError("");
    try {
      await api.delete(`/admin/rooms/${room.id}`);
      await loadData();
    } catch (e) {
      setError(e.message);
    }
  }

  function downloadTemplate() {
    const content = "\uFEFFHệ thống rạp,Tên cụm rạp,Khu vực / Tỉnh thành,Địa chỉ / Chi tiết,SĐT,Tên phòng,Loại phòng,Số hàng,Số cột\n";
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "cinevo-cinema-import-template.csv";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <section>
      <div className="toolbar">
        <div>
          <h1 className="page-title">Quản lý rạp toàn quốc</h1>
          <p className="muted">Phân loại 34 tỉnh/thành theo miền Bắc, Trung, Nam. Danh sách địa điểm rạp thực tế lấy từ dữ liệu bạn nhập. Muốn khách chọn được rạp để mua vé, cần tạo suất chiếu cho phim tại phòng tương ứng.</p>
        </div>
      </div>
      <ErrorBox message={error} />

      <form ref={importForm} className="card admin-catalog-form admin-cinema-import-form" onSubmit={importCinemas}>
        <div className="admin-movie-import-heading">
          <div>
            <h2>Nhập rạp, phòng và ghế từ Excel</h2>
            <p className="muted">Hỗ trợ .xlsx và CSV UTF-8; tối đa 500 phòng mỗi lần. Hệ thống rạp và tên cụm rạp được lưu riêng.</p>
          </div>
          <button className="btn btn-ghost btn-sm" type="button" onClick={downloadTemplate}>Tải file mẫu CSV</button>
        </div>
        <label className="admin-movie-import-file">
          Chọn file dữ liệu
          <input type="file" accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
            disabled={importing}
            onChange={(event) => {
              setImportFile(event.target.files?.[0] || null);
              setImportResult(null);
            }} />
        </label>
        {importFile && <p className="hint">Đã chọn: {importFile.name}</p>}
        <div className="actions">
          <button className="btn btn-red" type="submit" disabled={importing || !importFile}>
            {importing ? "Đang nhập rạp..." : "Nhập rạp vào hệ thống"}
          </button>
        </div>
        <p className="hint">Hỗ trợ các cột “Hệ thống rạp”, “Tên cụm rạp”, “Tỉnh/thành” hoặc “Khu vực / Tỉnh thành”, “Miền” và “Địa chỉ”. Địa chỉ có thể để trống; nếu file không có thông tin phòng, hệ thống tạo Phòng 01 loại 2D với 8 × 10 ghế mặc định. Với mẫu chi tiết, mỗi dòng là một phòng và có thể khai báo Tên phòng, Loại phòng, Số hàng, Số cột để tạo nhiều phòng cho cùng rạp.</p>
        {importResult && <p className="appearance-success" role="status">{importResult.message}</p>}
      </form>

      <form className="card admin-catalog-form admin-cinema-manual-form" onSubmit={createCinema}>
        <h2>Thêm rạp thủ công</h2>
        <div className="admin-catalog-fields">
          <label>Hệ thống rạp<input name="chain" value={form.chain} onChange={setField} maxLength="100" placeholder="Ví dụ: Beta Cinemas" /></label>
          <label>Tên cụm rạp<input name="name" value={form.name} onChange={setField} maxLength="150" required /></label>
          <label>Miền và tỉnh/thành
            <select name="city" value={form.city} onChange={setField} required>
              <option value="">Chọn tỉnh/thành</option>
              {regionOptions.map((region) => (
                <optgroup key={region} label={region}>
                  {provinces.filter((province) => province.region === region).map((province) => (
                    <option key={province.name} value={province.name}>{province.name}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
          <label>Địa chỉ<input name="address" value={form.address} onChange={setField} maxLength="250" required /></label>
          <label>Số điện thoại<input name="phone" value={form.phone} onChange={setField} maxLength="20" /></label>
          <label>Tên phòng<input name="room_name" value={form.room_name} onChange={setField} maxLength="50" required /></label>
          <label>Loại phòng<select name="room_type" value={form.room_type} onChange={setField}>
            <option value="2D">2D</option><option value="3D">3D</option><option value="IMAX">IMAX</option>
          </select></label>
          <label>Số hàng ghế<input name="total_rows" type="number" min="1" max="26" value={form.total_rows} onChange={setField} required /></label>
          <label>Số ghế mỗi hàng<input name="total_cols" type="number" min="1" max="30" value={form.total_cols} onChange={setField} required /></label>
        </div>
        <div className="actions">
          <button className="btn btn-red" type="submit" disabled={saving || !provinces.length}>
            {saving ? "Đang thêm rạp..." : "Thêm rạp và phòng"}
          </button>
        </div>
        <p className="hint">Phòng và ghế được tạo cùng rạp để có thể lập suất chiếu ngay sau đó. Có thể bổ sung các phòng khác bằng cách nhập Excel.</p>
      </form>

      <h2 className="section-title">Danh sách rạp theo khu vực</h2>
      <div className="admin-cinema-filters" role="group" aria-label="Lọc khu vực rạp">
        <label>Miền<select value={selectedRegion} onChange={(event) => {
          setSelectedRegion(event.target.value);
          setSelectedProvince("");
        }}>
          <option value="">Toàn quốc</option>
          {regionOptions.map((region) => <option key={region} value={region}>{region}</option>)}
        </select></label>
        <label>Tỉnh/thành<select value={selectedProvince} onChange={(event) => setSelectedProvince(event.target.value)}>
          <option value="">Tất cả tỉnh/thành</option>
          {provinceOptions.map((province) => <option key={province.name} value={province.name}>{province.name}</option>)}
        </select></label>
      </div>
      {cinemas === null ? <Loading /> : visibleCinemas.length ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Miền</th><th>Tỉnh/thành</th><th>Hệ thống rạp</th><th>Tên cụm rạp</th><th>Địa chỉ</th><th>Điện thoại</th><th>Số phòng</th><th>Quản lý</th></tr></thead>
            <tbody>{visibleCinemas.map((cinema) => (
              <Fragment key={cinema.id}>
                <tr>
                  <td>{cinema.region}</td><td>{cinema.province || cinema.city}</td><td>{cinema.chain || "—"}</td><td>{cinema.name}</td>
                  <td>{cinema.address || "—"}</td><td>{cinema.phone || "—"}</td><td>{cinema.rooms_count ?? 0}</td>
                  <td className="actions">
                    <button className="btn btn-ghost btn-sm" type="button" onClick={() => beginCinemaEdit(cinema)}>Sửa rạp</button>
                    <button className="btn btn-ghost btn-sm" type="button"
                      onClick={() => setExpandedCinemaId(expandedCinemaId === cinema.id ? null : cinema.id)}>
                      {expandedCinemaId === cinema.id ? "Ẩn phòng" : "Phòng và ghế"}
                    </button>
                  </td>
                </tr>
                {editingCinemaId === cinema.id && cinemaDraft && (
                  <tr>
                    <td colSpan="8">
                      <form className="admin-catalog-fields" onSubmit={(event) => saveCinema(event, cinema.id)}>
                        <label>Hệ thống rạp<input value={cinemaDraft.chain} onChange={(event) => setCinemaDraft({ ...cinemaDraft, chain: event.target.value })} maxLength="100" /></label>
                        <label>Tên cụm rạp<input value={cinemaDraft.name} onChange={(event) => setCinemaDraft({ ...cinemaDraft, name: event.target.value })} maxLength="150" required /></label>
                        <label>Tỉnh/thành<select value={cinemaDraft.city} onChange={(event) => setCinemaDraft({ ...cinemaDraft, city: event.target.value })} required>
                          <option value="">Chọn tỉnh/thành</option>
                          {regionOptions.map((region) => <optgroup key={region} label={region}>
                            {provinces.filter((province) => province.region === region).map((province) => (
                              <option key={province.name} value={province.name}>{province.name}</option>
                            ))}
                          </optgroup>)}
                        </select></label>
                        <label>Địa chỉ<input value={cinemaDraft.address} onChange={(event) => setCinemaDraft({ ...cinemaDraft, address: event.target.value })} maxLength="250" /></label>
                        <label>Điện thoại<input value={cinemaDraft.phone} onChange={(event) => setCinemaDraft({ ...cinemaDraft, phone: event.target.value })} maxLength="20" /></label>
                        <div className="actions">
                          <button className="btn btn-red btn-sm" disabled={savingCinemaId === cinema.id}>
                            {savingCinemaId === cinema.id ? "Đang lưu..." : "Lưu thông tin rạp"}
                          </button>
                          <button className="btn btn-ghost btn-sm" type="button" onClick={() => setEditingCinemaId(null)}>Hủy</button>
                        </div>
                      </form>
                    </td>
                  </tr>
                )}
                {expandedCinemaId === cinema.id && (
                  <tr>
                    <td colSpan="8">
                      <div className="admin-cinema-room-management">
                        <h3>Phòng chiếu và số ghế — {cinema.name}</h3>
                        <p className="hint">Điều chỉnh số hàng/cột sẽ thêm ghế hoặc gỡ ghế chưa được đặt. Không thể xóa ghế đã có vé; phòng có suất chiếu không thể xóa.</p>
                        {rooms.filter((room) => room.cinema_id === cinema.id).map((room) => (
                          <div className="card" key={room.id}>
                            {editingRoomId === room.id ? (
                              <form className="admin-catalog-fields" onSubmit={(event) => saveRoom(event, room.id)}>
                                <label>Tên phòng<input value={roomDraft.name} onChange={(event) => setRoomDraft({ ...roomDraft, name: event.target.value })} maxLength="50" required /></label>
                                <label>Loại phòng<select value={roomDraft.room_type} onChange={(event) => setRoomDraft({ ...roomDraft, room_type: event.target.value })}>
                                  <option value="2D">2D</option><option value="3D">3D</option><option value="IMAX">IMAX</option>
                                </select></label>
                                <label>Số hàng<input type="number" min="1" max="26" value={roomDraft.total_rows} onChange={(event) => setRoomDraft({ ...roomDraft, total_rows: event.target.value })} required /></label>
                                <label>Số ghế mỗi hàng<input type="number" min="1" max="30" value={roomDraft.total_cols} onChange={(event) => setRoomDraft({ ...roomDraft, total_cols: event.target.value })} required /></label>
                                <div className="actions">
                                  <button className="btn btn-red btn-sm" disabled={savingRoomId === room.id}>
                                    {savingRoomId === room.id ? "Đang lưu..." : "Lưu phòng và ghế"}
                                  </button>
                                  <button className="btn btn-ghost btn-sm" type="button" onClick={() => setEditingRoomId(null)}>Hủy</button>
                                </div>
                              </form>
                            ) : (
                              <div className="toolbar">
                                <div><strong>{room.name}</strong> · {room.room_type} · {room.total_rows} hàng × {room.total_cols} ghế = {room.seats_count} ghế
                                  <p className="hint">Suất chiếu: {room.showtimes_count}</p>
                                </div>
                                <div className="actions">
                                  <button className="btn btn-ghost btn-sm" type="button" onClick={() => beginRoomEdit(room)}>Sửa phòng/ghế</button>
                                  <button className="btn btn-ghost btn-sm" type="button" disabled={Boolean(room.showtimes_count)} onClick={() => deleteRoom(room)}>Xóa phòng</button>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                        <form className="admin-catalog-fields" onSubmit={(event) => addRoom(event, cinema.id)}>
                          <label>Tên phòng mới<input value={newRoomDraft.name} onChange={(event) => setNewRoomDraft({ ...newRoomDraft, name: event.target.value })} maxLength="50" required placeholder="Phòng 02" /></label>
                          <label>Loại phòng<select value={newRoomDraft.room_type} onChange={(event) => setNewRoomDraft({ ...newRoomDraft, room_type: event.target.value })}>
                            <option value="2D">2D</option><option value="3D">3D</option><option value="IMAX">IMAX</option>
                          </select></label>
                          <label>Số hàng<input type="number" min="1" max="26" value={newRoomDraft.total_rows} onChange={(event) => setNewRoomDraft({ ...newRoomDraft, total_rows: event.target.value })} required /></label>
                          <label>Số ghế mỗi hàng<input type="number" min="1" max="30" value={newRoomDraft.total_cols} onChange={(event) => setNewRoomDraft({ ...newRoomDraft, total_cols: event.target.value })} required /></label>
                          <div className="actions"><button className="btn btn-red btn-sm" disabled={creatingRoom}>
                            {creatingRoom ? "Đang thêm..." : "Thêm phòng"}
                          </button></div>
                        </form>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}</tbody>
          </table>
        </div>
      ) : <div className="state-box">Chưa có rạp nào trong khu vực này. Hãy nhập danh sách rạp thật bằng Excel hoặc thêm thủ công.</div>}
    </section>
  );
}
